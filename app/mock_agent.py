import json
import asyncio
import websockets
from typing import Optional


class MockAssemblyAIAgent:
    """
    Mock AssemblyAI agent for testing without a real API key.
    Simulates streaming transcript and tool calls.
    """

    def __init__(self):
        self.call_id_counter = 0

    async def simulate_conversation(self, websocket):
        """
        Simulate a patient intake conversation with mock transcript and tool updates.
        """
        # Welcome message
        await websocket.send(
            json.dumps({
                "type": "session.ready",
                "session_id": "mock_session_123",
            })
        )

        # Simulate greeting from agent
        await asyncio.sleep(0.5)
        await websocket.send(
            json.dumps({
                "type": "transcript.agent",
                "text": "Hi, I'm MEDI. I can help you describe your symptoms clearly. Tell me the main concern and how long it has been happening.",
            })
        )

        # Listen for user input
        try:
            while True:
                message = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                data = json.loads(message)
                msg_type = data.get("type")

                if msg_type == "transcript.user":
                    user_text = data.get("text", "")
                    await websocket.send(
                        json.dumps({
                            "type": "transcript.user",
                            "text": user_text,
                        })
                    )

                    # Mock symptom extraction and tool call
                    if any(word in user_text.lower() for word in ["chest", "pain", "breathing"]):
                        self.call_id_counter += 1
                        await websocket.send(
                            json.dumps({
                                "type": "tool.call",
                                "call_id": f"call_{self.call_id_counter}",
                                "name": "update_patient_memory",
                                "arguments": json.dumps({
                                    "main_concern": "Chest pain with shortness of breath",
                                    "symptoms": ["chest pain", "shortness of breath"],
                                    "duration": "2 hours",
                                    "location": "chest",
                                    "severity": "moderate",
                                }),
                            })
                        )
                        await asyncio.sleep(0.5)
                        await websocket.send(
                            json.dumps({
                                "type": "reply.done",
                            })
                        )

                    # Mock follow-up from agent
                    await asyncio.sleep(0.8)
                    await websocket.send(
                        json.dumps({
                            "type": "transcript.agent",
                            "text": "Thank you for sharing that. When did this pain start, and has it been constant or intermittent?",
                        })
                    )

                elif msg_type == "stop":
                    await websocket.send(
                        json.dumps({
                            "type": "session.complete",
                            "summary": "Session ended by user.",
                        })
                    )
                    break
        except asyncio.TimeoutError:
            await websocket.send(
                json.dumps({
                    "type": "session.error",
                    "message": "Session timeout.",
                })
            )
