from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
import os
import uuid
from pathlib import Path

from app.ai_engine import analyze_case
from app.schemas import AnalyzeRequest, PatientState
from app.state import PatientStateStore, WebSocketHub
from app.voice_agent import SYSTEM_PROMPT, build_voice_intro
from app.doctor_dashboard import DoctorDashboardRouter, db as dashboard_db

app = FastAPI(title="MEDI Clinical Voice Assistant", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

PATIENT_STATE = PatientStateStore()
WS_HUB = WebSocketHub()

# Initialize doctor dashboard routes
doctor_dashboard = DoctorDashboardRouter(dashboard_db)
app.include_router(doctor_dashboard.router)


@app.get("/")
async def root():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "MEDI Clinical Assistant is running."}


@app.get("/dashboard")
async def dashboard():
    dashboard_file = STATIC_DIR / "dashboard.html"
    if dashboard_file.exists():
        return FileResponse(dashboard_file)
    return {"message": "Dashboard not available."}


@app.get("/api/health")
async def health():
    return {"status": "online", "service": "MEDI Voice Clinical Assistant"}


@app.get("/api/patient/state")
async def get_patient_state():
    return {"status": "ok", "data": PATIENT_STATE.snapshot()}


@app.post("/api/analyze")
async def analyze(request: AnalyzeRequest):
    payload = request.model_dump(exclude_none=True)
    result = analyze_case(payload)
    return result


@app.get("/api/voice-session")
async def voice_session():
    return {
        "voice_name": "MEDI",
        "greeting": build_voice_intro(),
        "system_prompt": SYSTEM_PROMPT,
    }


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await WS_HUB.connect(websocket)
    await websocket.send_json({
        "type": "state",
        "data": {"status": "starting", "patient": PATIENT_STATE.snapshot()}
    })

    try:
        while True:
            message = await websocket.receive_json()
            message_type = message.get("type")

            if message_type == "get_state":
                await websocket.send_json({
                    "type": "state",
                    "data": {"status": "online", "patient": PATIENT_STATE.snapshot()}
                })
                continue

            if message_type == "update_patient":
                payload = message.get("data", {})
                PATIENT_STATE.apply_tool_update(payload)
                await WS_HUB.broadcast({
                    "type": "patient_update",
                    "data": PATIENT_STATE.snapshot()
                })
                continue

            if message_type == "transcript":
                await WS_HUB.broadcast({
                    "type": "transcript",
                    "role": message.get("role", "user"),
                    "text": message.get("text", "")
                })
                continue

            if message_type == "audio":
                await WS_HUB.broadcast({
                    "type": "audio",
                    "audio": message.get("audio", "")
                })
                continue

            if message_type == "start":
                await WS_HUB.broadcast({"type": "status", "status": "listening"})
                continue

            if message_type == "interrupt":
                await WS_HUB.broadcast({"type": "status", "status": "interrupt"})
                continue

            if message_type == "stop":
                await WS_HUB.broadcast({"type": "status", "status": "ready"})
                continue

            await WS_HUB.broadcast({"type": "echo", "message": message})
    except WebSocketDisconnect:
        WS_HUB.disconnect(websocket)
    except Exception:
        WS_HUB.disconnect(websocket)


@app.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket):
    await websocket.accept()
    session_id = str(uuid.uuid4())
    patient_name = "Patient"

    try:
        await websocket.send_json({
            "type": "session.ready",
            "session_id": session_id,
            "greeting": build_voice_intro(),
        })

        while True:
            message = await websocket.receive_json()
            msg_type = message.get("type")

            if msg_type == "start_session":
                patient_name = message.get("patient_name", "Patient")
                dashboard_db.create_session(session_id, patient_name)
                await websocket.send_json({"type": "session.started", "session_id": session_id})

            elif msg_type == "transcript.user":
                text = message.get("text", "")
                dashboard_db.add_transcript(session_id, "user", text)
                await websocket.send_json({"type": "ack", "status": "received"})

            elif msg_type == "update_patient":
                payload = message.get("data", {})
                updated_state = PATIENT_STATE.apply_tool_update(payload)
                dashboard_db.update_session_state(session_id, updated_state)
                await WS_HUB.broadcast({
                    "type": "patient_update",
                    "data": updated_state
                })

            elif msg_type == "stop_session":
                dashboard_db.close_session(session_id)
                await websocket.send_json({"type": "session.closed", "session_id": session_id})
                break

    except WebSocketDisconnect:
        dashboard_db.close_session(session_id)
    except Exception as exc:
        await websocket.send_json({"type": "error", "message": str(exc)})
        dashboard_db.close_session(session_id)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
