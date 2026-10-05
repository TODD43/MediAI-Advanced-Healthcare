from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from typing import Dict, Any, List
import json
import os
import asyncio
from datetime import datetime
from app.state import PatientStateStore, WebSocketHub
from app.mock_agent import MockAssemblyAIAgent

router = APIRouter(prefix="/api/ws", tags=["websocket"])

# Mock database for doctor dashboard
class MockPatientDatabase:
    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.patients: Dict[str, Dict[str, Any]] = {}

    def create_session(self, session_id: str, patient_name: str) -> Dict[str, Any]:
        session = {
            "session_id": session_id,
            "patient_name": patient_name,
            "created_at": datetime.utcnow().isoformat(),
            "state": {},
            "transcript": [],
            "status": "active",
        }
        self.sessions[session_id] = session
        return session

    def update_session_state(self, session_id: str, state: Dict[str, Any]) -> None:
        if session_id in self.sessions:
            self.sessions[session_id]["state"] = state
            self.sessions[session_id]["updated_at"] = datetime.utcnow().isoformat()

    def add_transcript(self, session_id: str, role: str, text: str) -> None:
        if session_id in self.sessions:
            self.sessions[session_id]["transcript"].append({
                "role": role,
                "text": text,
                "timestamp": datetime.utcnow().isoformat(),
            })

    def close_session(self, session_id: str) -> None:
        if session_id in self.sessions:
            self.sessions[session_id]["status"] = "closed"
            self.sessions[session_id]["closed_at"] = datetime.utcnow().isoformat()

    def get_session(self, session_id: str) -> Dict[str, Any]:
        return self.sessions.get(session_id, {})

    def list_sessions(self) -> List[Dict[str, Any]]:
        return list(self.sessions.values())

    def get_patient(self, patient_id: str) -> Dict[str, Any]:
        return self.patients.get(patient_id, {})

    def save_patient(self, patient_id: str, data: Dict[str, Any]) -> None:
        data["updated_at"] = datetime.utcnow().isoformat()
        self.patients[patient_id] = data


db = MockPatientDatabase()


async def voice_agent_handler(websocket: WebSocket, session_id: str, patient_name: str) -> None:
    """
    Handle voice assistant connection with real or mock AssemblyAI agent.
    """
    db.create_session(session_id, patient_name)
    state_store = PatientStateStore()
    agent = MockAssemblyAIAgent()

    try:
        while True:
            message = await websocket.receive_json()
            msg_type = message.get("type")

            if msg_type == "transcript.user":
                text = message.get("text", "")
                db.add_transcript(session_id, "user", text)
                await websocket.send_json({"type": "ack", "status": "received"})

            elif msg_type == "tool.result":
                call_id = message.get("call_id")
                result = message.get("result", {})
                await websocket.send_json({"type": "ack", "call_id": call_id})

            elif msg_type == "update_patient":
                payload = message.get("data", {})
                updated_state = state_store.apply_tool_update(payload)
                db.update_session_state(session_id, updated_state)
                db.add_transcript(session_id, "system", f"Patient state updated: {payload}")

            elif msg_type == "stop":
                db.close_session(session_id)
                await websocket.send_json({"type": "session.closed", "session_id": session_id})
                break
    except WebSocketDisconnect:
        db.close_session(session_id)
    except Exception as exc:
        await websocket.send_json({"type": "error", "message": str(exc)})
        db.close_session(session_id)


# Doctor Dashboard Endpoints
class DoctorDashboardRouter:
    def __init__(self, db: MockPatientDatabase):
        self.db = db
        self.router = APIRouter(prefix="/api/doctor", tags=["doctor-dashboard"])
        self._setup_routes()

    def _setup_routes(self):
        @self.router.get("/sessions")
        async def list_patient_sessions():
            """List all patient intake sessions."""
            return {
                "status": "ok",
                "sessions": self.db.list_sessions(),
                "total": len(self.db.list_sessions()),
            }

        @self.router.get("/sessions/{session_id}")
        async def get_session_details(session_id: str):
            """Get detailed session transcript and patient state."""
            session = self.db.get_session(session_id)
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
            return {
                "status": "ok",
                "session": session,
            }

        @self.router.get("/patients")
        async def list_patients():
            """List all patients in the system."""
            return {
                "status": "ok",
                "patients": list(self.db.patients.values()),
                "total": len(self.db.patients),
            }

        @self.router.get("/patients/{patient_id}")
        async def get_patient_record(patient_id: str):
            """Get full patient medical record."""
            patient = self.db.get_patient(patient_id)
            if not patient:
                raise HTTPException(status_code=404, detail="Patient not found")
            return {
                "status": "ok",
                "patient": patient,
            }

        @self.router.post("/patients/{patient_id}/notes")
        async def add_doctor_notes(patient_id: str, body: Dict[str, Any]):
            """Add clinical notes to a patient record."""
            patient = self.db.get_patient(patient_id)
            if not patient:
                patient = {"patient_id": patient_id, "notes": []}
            if "notes" not in patient:
                patient["notes"] = []
            patient["notes"].append({
                "timestamp": datetime.utcnow().isoformat(),
                "note": body.get("note", ""),
                "doctor": body.get("doctor", "Unknown"),
            })
            self.db.save_patient(patient_id, patient)
            return {"status": "ok", "patient_id": patient_id, "patient": patient}

        @self.router.post("/patients/{patient_id}/diagnosis")
        async def record_diagnosis(patient_id: str, body: Dict[str, Any]):
            """Record a diagnosis for a patient."""
            patient = self.db.get_patient(patient_id)
            if not patient:
                patient = {"patient_id": patient_id}
            if "diagnoses" not in patient:
                patient["diagnoses"] = []
            patient["diagnoses"].append({
                "timestamp": datetime.utcnow().isoformat(),
                "diagnosis": body.get("diagnosis", ""),
                "icd_code": body.get("icd_code", ""),
                "confidence": body.get("confidence", "unknown"),
            })
            self.db.save_patient(patient_id, patient)
            return {"status": "ok", "patient_id": patient_id, "patient": patient}

        @self.router.get("/analytics/summary")
        async def get_analytics_summary():
            """Get high-level analytics for the clinic."""
            sessions = self.db.list_sessions()
            active_sessions = [s for s in sessions if s["status"] == "active"]
            closed_sessions = [s for s in sessions if s["status"] == "closed"]
            return {
                "status": "ok",
                "total_sessions": len(sessions),
                "active_sessions": len(active_sessions),
                "closed_sessions": len(closed_sessions),
                "total_patients": len(self.db.patients),
            }
