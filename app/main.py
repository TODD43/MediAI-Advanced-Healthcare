from __future__ import annotations

import asyncio
import json
import os
from threading import Lock
from typing import Any, Dict, List, Optional, Set

import websockets
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.ai_engine import analyze_case
from app.schemas import AnalyzeRequest, PatientState
from app.state import PatientStateStore, WebSocketHub
from app.voice_agent import SYSTEM_PROMPT, build_voice_intro

app = FastAPI(title="MEDI Clinical Voice Assistant", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PATIENT_STATE = PatientStateStore()
WS_HUB = WebSocketHub()


@app.get("/api/health")
async def health() -> Dict[str, Any]:
    return {"status": "online", "service": "MEDI Voice Clinical Assistant"}


@app.get("/api/patient/state")
async def get_patient_state() -> Dict[str, Any]:
    return {"status": "ok", "data": PATIENT_STATE.snapshot()}


@app.post("/api/analyze")
async def analyze(request: AnalyzeRequest) -> Dict[str, Any]:
    payload = request.model_dump(exclude_none=True)
    result = analyze_case(payload)
    return result


@app.get("/api/voice-session")
async def voice_session() -> Dict[str, Any]:
    return {
        "voice_name": "MEDI",
        "greeting": build_voice_intro(),
        "system_prompt": SYSTEM_PROMPT,
    }


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket) -> None:
    await WS_HUB.connect(websocket)
    await websocket.send_json({"type": "state", "data": {"status": "starting", "patient": PATIENT_STATE.snapshot()}})

    try:
        while True:
            message = await websocket.receive_json()
            message_type = message.get("type")

            if message_type == "get_state":
                await websocket.send_json({"type": "state", "data": {"status": "online", "patient": PATIENT_STATE.snapshot()}})
                continue

            if message_type == "update_patient":
                payload = message.get("data", {})
                PATIENT_STATE.apply_tool_update(payload)
                await WS_HUB.broadcast({"type": "patient_update", "data": PATIENT_STATE.snapshot()})
                continue

            if message_type == "transcript":
                await WS_HUB.broadcast({"type": "transcript", "role": message.get("role", "user"), "text": message.get("text", "")})
                continue

            if message_type == "audio":
                await WS_HUB.broadcast({"type": "audio", "audio": message.get("audio", "")})
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


async def _browser_to_assembly(browser_ws: WebSocket, assembly_ws) -> None:
    while True:
        try:
            message = await browser_ws.receive_json()
        except Exception:
            break

        msg_type = message.get("type")
        if msg_type == "audio":
            audio = message.get("audio")
            if audio:
                await assembly_ws.send(json.dumps({"type": "input.audio", "audio": audio}))
        elif msg_type == "text":
            await browser_ws.send_json({"type": "text", "message": "MEDI cloud server is ON!"})
        elif msg_type == "stop":
            await browser_ws.send_json({"type": "status", "status": "ready"})
        elif msg_type == "interrupt":
            await browser_ws.send_json({"type": "status", "status": "listening"})


async def _assembly_to_browser(browser_ws: WebSocket, assembly_ws) -> None:
    pending_tools: List[Dict[str, Any]] = []
    async for raw in assembly_ws:
        try:
            event = json.loads(raw)
        except Exception:
            continue
        event_type = event.get("type")

        if event_type == "session.ready":
            await browser_ws.send_json({"type": "status", "status": "ready"})
        elif event_type == "transcript.user":
            text = str(event.get("text", "")).strip()
            if text:
                await browser_ws.send_json({"type": "transcript", "role": "user", "text": text})
        elif event_type == "transcript.agent":
            text = str(event.get("text", "")).strip()
            if text:
                await browser_ws.send_json({"type": "transcript", "role": "assistant", "text": text})
        elif event_type == "reply.audio":
            data = event.get("data")
            if data:
                await browser_ws.send_json({"type": "audio", "audio": data})
        elif event_type == "tool.call":
            call_id = event.get("call_id")
            name = event.get("name")
            arguments = event.get("arguments") or {}
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except Exception:
                    arguments = {}

            if name == "update_patient_memory":
                updated_state = PATIENT_STATE.apply_tool_update(arguments)
                await browser_ws.send_json({"type": "patient_update", "data": updated_state})
                result = {"success": True, "message": "Patient summary updated."}
            else:
                result = {"success": False, "message": f"Unknown tool: {name}"}
            pending_tools.append({"call_id": call_id, "result": result})
        elif event_type == "reply.done":
            for item in pending_tools:
                await assembly_ws.send(
                    json.dumps({"type": "tool.result", "call_id": item["call_id"], "result": json.dumps(item["result"])})
                )
            pending_tools.clear()
        elif event_type == "session.error":
            await browser_ws.send_json({"type": "error", "message": "MEDI encountered a voice connection error."})


async def run_assembly_session(browser_ws: WebSocket) -> None:
    api_key = os.getenv("ASSEMBLYAI_API_KEY")
    if not api_key:
        await browser_ws.send_json({"type": "error", "message": "ASSEMBLYAI_API_KEY is not configured."})
        return

    try:
        async with websockets.connect(
            "wss://agents.assemblyai.com/v1/ws",
            additional_headers={"Authorization": f"Bearer {api_key}"},
            ping_interval=20,
            ping_timeout=20,
            open_timeout=30,
        ) as assembly_ws:
            await assembly_ws.send(
                json.dumps(
                    {
                        "type": "session.update",
                        "session": {
                            "system_prompt": SYSTEM_PROMPT,
                            "greeting": build_voice_intro(),
                            "tools": [
                                {
                                    "type": "function",
                                    "name": "update_patient_memory",
                                    "description": "Update the structured patient memory using facts explicitly provided by the user.",
                                    "parameters": {
                                        "type": "object",
                                        "properties": {
                                            "main_concern": {"type": "string"},
                                            "symptoms": {"type": "array", "items": {"type": "string"}},
                                            "duration": {"type": "string"},
                                            "severity": {"type": "string"},
                                            "location": {"type": "string"},
                                            "associated_symptoms": {"type": "array", "items": {"type": "string"}},
                                            "medications": {"type": "array", "items": {"type": "string"}},
                                            "allergies": {"type": "array", "items": {"type": "string"}},
                                            "medical_history": {"type": "array", "items": {"type": "string"}},
                                            "notes": {"type": "array", "items": {"type": "string"}},
                                        },
                                    },
                                }
                            ],
                            "input": {"turn_detection": {"interrupt_response": True}},
                            "output": {"voice": "anna"},
                        },
                    }
                )
            )
            await asyncio.gather(_browser_to_assembly(browser_ws, assembly_ws), _assembly_to_browser(browser_ws, assembly_ws))
    except Exception as exc:
        await browser_ws.send_json({"type": "error", "message": f"MEDI cloud connection failed: {exc}"})


@app.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        await run_assembly_session(websocket)
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        await websocket.send_json({"type": "error", "message": str(exc)})


@app.get("/")
async def root() -> JSONResponse:
    return JSONResponse({"message": "MEDI is running. Open the UI or use the websocket endpoints."})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
