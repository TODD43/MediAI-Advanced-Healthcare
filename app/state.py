from __future__ import annotations

import threading
from copy import deepcopy
from typing import Any, Dict, List, Optional, Set

from fastapi import WebSocket

from app.schemas import PatientState


class PatientStateStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._state = PatientState()

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return deepcopy(self._state.to_dict())

    def apply_tool_update(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            self._state.merge_update(payload)
            return deepcopy(self._state.to_dict())

    def reset(self) -> Dict[str, Any]:
        with self._lock:
            self._state = PatientState()
            return deepcopy(self._state.to_dict())


class WebSocketHub:
    def __init__(self) -> None:
        self._clients: Set[WebSocket] = set()
        self._lock = threading.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        with self._lock:
            self._clients.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        with self._lock:
            self._clients.discard(websocket)

    async def broadcast(self, payload: Dict[str, Any]) -> None:
        dead: List[WebSocket] = []
        with self._lock:
            clients = list(self._clients)
        for ws in clients:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


class ChatTranscript:
    def __init__(self) -> None:
        self.messages: List[Dict[str, str]] = []

    def add(self, role: str, text: str) -> None:
        if text:
            self.messages.append({"role": role, "text": text})

    def snapshot(self) -> List[Dict[str, str]]:
        return list(self.messages)
