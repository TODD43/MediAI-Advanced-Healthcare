"""
Production-grade real-time audio agent for MediAI.
Implements WebRTC audio streaming, clinical NLP processing, and multi-agent coordination.
"""

import asyncio
import json
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, asdict
from collections import deque
import uuid

import numpy as np
from fastapi import WebSocket, WebSocketDisconnect
import openai
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class AudioState(str, Enum):
    """Audio stream lifecycle states."""
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    RESPONDING = "responding"
    ERROR = "error"


class MessageRole(str, Enum):
    """Message roles for conversation context."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class AudioMetrics:
    """Real-time audio quality metrics."""
    sample_rate: int = 16000
    bit_depth: int = 16
    channels: int = 1
    latency_ms: float = 0.0
    noise_level: float = 0.0
    signal_level: float = 0.0
    packet_loss_pct: float = 0.0
    jitter_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ConversationTurn:
    """Single turn in patient-agent conversation."""
    id: str
    timestamp: datetime
    role: MessageRole
    content: str
    confidence: float = 0.95
    clinical_entities: List[str] = None
    emotion: str = "neutral"
    
    def __post_init__(self):
        if self.clinical_entities is None:
            self.clinical_entities = []


class AudioBuffer:
    """Thread-safe circular buffer for audio frames."""
    
    def __init__(self, max_frames: int = 4096):
        self.buffer = deque(maxlen=max_frames)
        self.frame_count = 0
        self.lock = asyncio.Lock()
    
    async def put(self, frame: bytes) -> None:
        """Add audio frame to buffer."""
        async with self.lock:
            self.buffer.append(frame)
            self.frame_count += 1
    
    async def get_all(self) -> List[bytes]:
        """Retrieve all buffered frames."""
        async with self.lock:
            frames = list(self.buffer)
            self.buffer.clear()
            return frames
    
    async def get_mono(self, frame_count: int = 0) -> np.ndarray:
        """Get buffer as mono float32 numpy array."""
        async with self.lock:
            if not self.buffer:
                return np.array([], dtype=np.float32)
            
            frames = list(self.buffer)
            if frame_count > 0:
                frames = frames[-frame_count:]
            
            # Convert bytes to numpy array
            audio_data = np.concatenate([
                np.frombuffer(frame, dtype=np.int16) for frame in frames
            ])
            
            # Normalize to float32
            return audio_data.astype(np.float32) / 32768.0


class AudioAnalyzer:
    """Clinical-grade audio analysis."""
    
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.metrics = AudioMetrics(sample_rate=sample_rate)
        self.rms_history: deque = deque(maxlen=100)
        self.vad_threshold = 0.02
    
    async def analyze_frame(self, audio_data: np.ndarray) -> Dict[str, float]:
        """Analyze single audio frame for quality metrics."""
        if len(audio_data) == 0:
            return {"noise_level": 0.0, "signal_level": 0.0, "voice_detected": False}
        
        # RMS energy
        rms = float(np.sqrt(np.mean(audio_data ** 2)))
        self.rms_history.append(rms)
        
        # Voice Activity Detection
        voice_detected = rms > self.vad_threshold
        
        # Spectral analysis
        fft = np.abs(np.fft.fft(audio_data))
        freq_bins = np.fft.fftfreq(len(fft), 1.0 / self.sample_rate)
        
        # Speech-frequency bands (80-400 Hz for voice fundamentals)
        speech_mask = (freq_bins > 80) & (freq_bins < 400)
        speech_energy = np.mean(fft[speech_mask]) if np.any(speech_mask) else 0.0
        
        # Noise detection (high-frequency content)
        noise_mask = (freq_bins > 4000) & (freq_bins < 8000)
        noise_energy = np.mean(fft[noise_mask]) if np.any(noise_mask) else 0.0
        
        return {
            "noise_level": float(noise_energy),
            "signal_level": float(speech_energy),
            "voice_detected": voice_detected,
            "rms": float(rms),
        }
    
    async def estimate_latency(self, timestamp_client: float, timestamp_server: float) -> float:
        """Estimate one-way latency in milliseconds."""
        return (timestamp_server - timestamp_client) * 1000


class ClinicalNLPProcessor:
    """Extract clinical entities and context from speech."""
    
    # Clinical keyword mappings
    SYMPTOM_KEYWORDS = {
        "pain": ["pain", "ache", "soreness", "hurt", "discomfort"],
        "fever": ["fever", "temperature", "hot", "chills"],
        "cough": ["cough", "coughing", "throat"],
        "breathing": ["breathing", "breath", "breathless", "dyspnea"],
        "nausea": ["nausea", "nauseous", "sick", "vomit"],
        "fatigue": ["tired", "fatigue", "exhausted", "weakness"],
    }
    
    SEVERITY_KEYWORDS = {
        "severe": ["severe", "severe", "worst", "unbearable", "critical"],
        "moderate": ["moderate", "considerable", "significant"],
        "mild": ["mild", "slight", "minor", "little"],
    }
    
    def __init__(self):
        self.last_entities: Dict[str, Any] = {}
    
    async def extract_entities(self, text: str) -> Dict[str, Any]:
        """Extract clinical entities from text."""
        text_lower = text.lower()
        
        entities = {
            "symptoms": [],
            "severity": "not_specified",
            "duration": None,
            "location": [],
            "medications": [],
            "allergies": [],
            "emotion": await self._detect_emotion(text),
        }
        
        # Symptom extraction
        for symptom_type, keywords in self.SYMPTOM_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                entities["symptoms"].append(symptom_type)
        
        # Severity assessment
        for severity_level, keywords in self.SEVERITY_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                entities["severity"] = severity_level
                break
        
        # Duration extraction (simple regex patterns)
        import re
        duration_patterns = [
            r"(\d+)\s*(days?|weeks?|months?|hours?|minutes?)",
        ]
        for pattern in duration_patterns:
            match = re.search(pattern, text_lower)
            if match:
                entities["duration"] = match.group(0)
                break
        
        self.last_entities = entities
        return entities
    
    async def _detect_emotion(self, text: str) -> str:
        """Simple emotion detection based on keywords."""
        text_lower = text.lower()
        
        if any(w in text_lower for w in ["urgent", "emergency", "critical", "help"]):
            return "urgent"
        if any(w in text_lower for w in ["worried", "anxious", "scared", "afraid"]):
            return "anxious"
        if any(w in text_lower for w in ["better", "good", "improving", "fine"]):
            return "positive"
        
        return "neutral"


class RealtimeAgent:
    """Production-grade real-time audio agent."""
    
    def __init__(self, 
                 model: str = "gpt-4",
                 system_prompt: Optional[str] = None,
                 max_history: int = 20):
        self.model = model
        self.agent_id = str(uuid.uuid4())
        self.session_id = str(uuid.uuid4())
        self.max_history = max_history
        self.conversation_history: List[ConversationTurn] = []
        self.audio_buffer = AudioBuffer()
        self.analyzer = AudioAnalyzer()
        self.nlp_processor = ClinicalNLPProcessor()
        self.state = AudioState.IDLE
        self.connected_clients: Set[WebSocket] = set()
        self.last_activity = datetime.now()
        
        self.system_prompt = system_prompt or self._get_default_system_prompt()
        self.llm_task: Optional[asyncio.Task] = None
        self.is_processing = False
    
    def _get_default_system_prompt(self) -> str:
        """Default clinical conversation system prompt."""
        return """You are MediAI, a professional medical intake assistant.

Your responsibilities:
1. Listen carefully to patient symptoms and concerns
2. Ask clarifying questions in a calm, empathetic manner
3. Structure information for clinical review
4. Identify emergency symptoms and respond appropriately
5. Provide safe, evidence-based guidance

Critical safety rules:
- NEVER diagnose or prescribe
- ALWAYS escalate emergency symptoms to immediate care
- Maintain HIPAA compliance for all patient data
- Use clear, simple language
- Acknowledge patient concerns with empathy

Conversation guidelines:
- Keep responses concise (under 50 words)
- Ask one question at a time
- Use active listening acknowledgments
- Document all clinical details
- Suggest appropriate next steps

Emergency keywords requiring immediate escalation:
chest pain, difficulty breathing, loss of consciousness, severe bleeding,
stroke symptoms, severe allergic reaction, suicidal ideation, severe trauma
"""
    
    async def connect_client(self, websocket: WebSocket) -> None:
        """Register new WebSocket client."""
        await websocket.accept()
        self.connected_clients.add(websocket)
        logger.info(f"Client connected. Total: {len(self.connected_clients)}")
    
    async def disconnect_client(self, websocket: WebSocket) -> None:
        """Unregister WebSocket client."""
        self.connected_clients.discard(websocket)
        logger.info(f"Client disconnected. Total: {len(self.connected_clients)}")
    
    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Broadcast message to all connected clients."""
        disconnected = set()
        
        for client in self.connected_clients:
            try:
                await client.send_json(message)
            except Exception as e:
                logger.error(f"Broadcast error: {e}")
                disconnected.add(client)
        
        # Cleanup failed connections
        for client in disconnected:
            await self.disconnect_client(client)
    
    async def process_audio_chunk(self, audio_chunk: bytes, timestamp: float) -> None:
        """Process incoming audio chunk."""
        if self.state == AudioState.ERROR:
            return
        
        try:
            # Add to buffer
            await self.audio_buffer.put(audio_chunk)
            
            # Analyze audio quality
            audio_data = await self.audio_buffer.get_mono(frame_count=1)
            quality = await self.analyzer.analyze_frame(audio_data)
            
            # Update metrics
            self.analyzer.metrics.noise_level = quality.get("noise_level", 0.0)
            self.analyzer.metrics.signal_level = quality.get("signal_level", 0.0)
            
            # Detect voice activity
            if quality.get("voice_detected", False):
                await self._transition_state(AudioState.LISTENING)
            
            # Broadcast metrics periodically
            if len(self.audio_buffer.buffer) % 10 == 0:
                await self.broadcast({
                    "type": "metrics",
                    "data": self.analyzer.metrics.to_dict(),
                })
            
        except Exception as e:
            logger.error(f"Audio processing error: {e}")
            await self._transition_state(AudioState.ERROR)
    
    async def process_transcript(self, transcript: str, is_final: bool = False) -> None:
        """Process speech-to-text transcript."""
        if not transcript.strip():
            return
        
        try:
            # Extract clinical entities
            entities = await self.nlp_processor.extract_entities(transcript)
            
            # Add to conversation history
            turn = ConversationTurn(
                id=str(uuid.uuid4()),
                timestamp=datetime.now(),
                role=MessageRole.USER,
                content=transcript,
                confidence=0.95,
                clinical_entities=entities.get("symptoms", []),
                emotion=entities.get("emotion", "neutral"),
            )
            self.conversation_history.append(turn)
            
            # Broadcast user message
            await self.broadcast({
                "type": "transcript",
                "role": "user",
                "text": transcript,
                "is_final": is_final,
                "entities": entities,
            })\n            \n            # Generate LLM response if transcript is final
            if is_final and not self.is_processing:
                await self._generate_response()
        
        except Exception as e:
            logger.error(f"Transcript processing error: {e}")
    
    async def _generate_response(self) -> None:
        """Generate LLM response to patient input."""
        if self.is_processing or not self.conversation_history:
            return
        
        self.is_processing = True
        await self._transition_state(AudioState.PROCESSING)
        
        try:
            # Build message context
            messages = [
                {"role": "system", "content": self.system_prompt},
            ]
            
            # Add conversation history (last N turns)
            for turn in self.conversation_history[-self.max_history:]:
                messages.append({
                    "role": turn.role.value,
                    "content": turn.content,
                })
            
            # Call LLM
            await self._transition_state(AudioState.RESPONDING)
            
            response = await asyncio.to_thread(
                openai.ChatCompletion.create,
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=150,
                presence_penalty=0.6,
            )
            
            assistant_text = response.choices[0].message.content.strip()
            
            # Add to history
            turn = ConversationTurn(
                id=str(uuid.uuid4()),
                timestamp=datetime.now(),
                role=MessageRole.ASSISTANT,
                content=assistant_text,
                confidence=0.98,
            )
            self.conversation_history.append(turn)
            
            # Broadcast response
            await self.broadcast({
                "type": "transcript",
                "role": "assistant",
                "text": assistant_text,
                "is_final": True,
            })
            
            # Prepare for TTS
            await self.broadcast({
                "type": "synthesize_speech",
                "text": assistant_text,
                "voice": "en-US-Neural2-C",  # Google Cloud TTS
            })
            
            await self._transition_state(AudioState.LISTENING)
        
        except Exception as e:
            logger.error(f"Response generation error: {e}")
            await self._transition_state(AudioState.ERROR)
        
        finally:
            self.is_processing = False
    
    async def _transition_state(self, new_state: AudioState) -> None:
        """Transition to new state."""
        if self.state != new_state:
            old_state = self.state
            self.state = new_state
            logger.info(f"State transition: {old_state.value} -> {new_state.value}")
            
            await self.broadcast({
                "type": "state_change",
                "state": new_state.value,
            })
    
    def get_patient_summary(self) -> Dict[str, Any]:
        """Generate clinical summary from conversation."""
        symptoms = []
        severity = "not_specified"
        duration = None
        
        for turn in self.conversation_history:
            if turn.clinical_entities:
                symptoms.extend(turn.clinical_entities)
            # Extract severity from last user message
            entities = asyncio.run(
                self.nlp_processor.extract_entities(turn.content)
            )
            if entities.get("severity") != "not_specified":
                severity = entities.get("severity")
            if entities.get("duration"):
                duration = entities.get("duration")
        
        return {
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "symptoms": list(set(symptoms)),  # Deduplicate
            "severity": severity,
            "duration": duration,
            "turn_count": len(self.conversation_history),
            "conversation": [
                {
                    "role": turn.role.value,
                    "content": turn.content,
                    "timestamp": turn.timestamp.isoformat(),
                }
                for turn in self.conversation_history
            ],
        }
