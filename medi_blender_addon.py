from __future__ import annotations

import asyncio
import json
import queue
import threading
from typing import Any, Dict, List, Optional

try:
    import bpy
except Exception:  # pragma: no cover
    bpy = None


BODY_TARGETS = {
    "head": ["head", "face", "skull", "cranial"],
    "neck": ["neck"],
    "chest": ["chest", "thorax", "torso", "rib", "lungs"],
    "abdomen": ["abdomen", "stomach", "belly", "gut"],
    "back": ["back", "spine", "spinal"],
    "left arm": ["left arm", "left_arm", "upper arm", "forearm", "arm"],
    "right arm": ["right arm", "right_arm"],
    "left leg": ["left leg", "left_leg", "thigh", "leg"],
    "right leg": ["right leg", "right_leg"],
    "knee": ["knee", "kneecap"],
    "ankle": ["ankle"],
    "shoulder": ["shoulder"],
    "hip": ["hip", "pelvis"],
}


class BlenderNetworkBridge(threading.Thread):
    def __init__(self, ws_url: str = "ws://localhost:8000/ws") -> None:
        super().__init__(daemon=True)
        self.ws_url = ws_url
        self.queue: "queue.Queue[Dict[str, Any]]" = queue.Queue()
        self.websocket = None
        self.loop = None
        self.stop_event = threading.Event()

    def enqueue(self, payload: Dict[str, Any]) -> None:
        if payload:
            self.queue.put(payload)

    async def _connect(self) -> None:
        import websockets

        async for websocket in websockets.connect(self.ws_url):
            self.websocket = websocket
            self._listen_loop(websocket)
            break

    async def _listen_loop(self, websocket) -> None:
        async for msg in websocket:
            try:
                payload = json.loads(msg)
            except Exception:
                continue
            if payload.get("type") == "patient_update":
                self.enqueue(payload)
            elif payload.get("type") == "transcript":
                self.enqueue(payload)
            elif payload.get("type") == "status":
                self.enqueue(payload)

    def run(self) -> None:
        try:
            asyncio.run(self._run())
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            self.loop.run_until_complete(self._run())

    async def _run(self) -> None:
        import websockets

        while not self.stop_event.is_set():
            try:
                async with websockets.connect(self.ws_url) as websocket:
                    self.websocket = websocket
                    async for msg in websocket:
                        try:
                            payload = json.loads(msg)
                        except Exception:
                            continue
                        if payload.get("type") in {"patient_update", "transcript", "status", "state"}:
                            self.enqueue(payload)
            except Exception:
                await asyncio.sleep(1.5)

    def stop(self) -> None:
        self.stop_event.set()


bridge = BlenderNetworkBridge()


def _get_scene_objects():
    if bpy is None:
        return []
    return list(bpy.data.objects)


def _match_target(location: str):
    text = (location or "").lower()
    for target, aliases in BODY_TARGETS.items():
        if any(alias in text for alias in aliases):
            return target
    for token in ["left", "right", "head", "neck", "chest", "abdomen", "back", "knee", "ankle", "hip", "shoulder", "arm", "leg"]:
        if token in text:
            return token
    return "chest"


def _ensure_material(obj, name: str, color: tuple):
    if bpy is None or obj is None:
        return
    material = obj.data.materials.get(name)
    if material is None:
        material = bpy.data.materials.new(name=name)
        obj.data.materials.clear()
        obj.data.materials.append(material)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf is None:
        bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Emission"].default_value = (*color, 1.0)
    bsdf.inputs["Emission Strength"].default_value = 0.6


def _update_highlight(location: str, severity: str = "moderate") -> None:
    if bpy is None:
        return
    target_name = _match_target(location)
    for obj in _get_scene_objects():
        name_lower = obj.name.lower()
        if target_name in name_lower or target_name.replace(" ", "_") in name_lower:
            color = (1.0, 0.2, 0.2)
            if severity and "low" in severity.lower():
                color = (1.0, 0.85, 0.2)
            elif severity and "high" in severity.lower():
                color = (1.0, 0.1, 0.1)
            _ensure_material(obj, "MEDI_Alert_Material", color)
            return


def _ensure_hud_text() -> Any:
    if bpy is None:
        return None
    scene = bpy.context.scene
    hud = bpy.data.objects.get("MEDI_HUD")
    if hud is None:
        bpy.ops.object.text_add(location=(0, 0, 2.5))
        hud = bpy.context.active_object
        hud.name = "MEDI_HUD"
        hud.data.body = "MEDI\nWaiting for patient data..."
        hud.data.align_x = "CENTER"
        hud.data.align_y = "CENTER"
    return hud


def _update_hud_text(transcript: str, patient: Dict[str, Any]) -> None:
    if bpy is None:
        return
    hud = _ensure_hud_text()
    if hud is None:
        return
    patient_lines = []
    if patient.get("main_concern"):
        patient_lines.append(f"Concern: {patient['main_concern']}")
    if patient.get("location"):
        patient_lines.append(f"Location: {patient['location']}")
    if patient.get("severity"):
        patient_lines.append(f"Severity: {patient['severity']}")
    patient_block = "\n".join(patient_lines) if patient_lines else "No patient data yet"
    hud.data.body = f"MEDI\n{transcript}\n\n{patient_block}"


def _process_blender_queue() -> bool:
    if bpy is None:
        return False
    while not bridge.queue.empty():
        payload = bridge.queue.get()
        msg_type = payload.get("type")
        if msg_type == "patient_update":
            patient = payload.get("data") or {}
            location = patient.get("location") or "chest"
            severity = patient.get("severity") or "moderate"
            _update_highlight(location, severity)
            _update_hud_text("Patient state updated", patient)
        elif msg_type == "transcript":
            text = payload.get("text") or ""
            patient = payload.get("patient") or {}
            _update_hud_text(text, patient)
        elif msg_type == "state":
            patient = payload.get("data", {}).get("patient") or {}
            _update_hud_text("System ready", patient)
    return True


def _ensure_bridge_started() -> None:
    if bridge.is_alive():
        return
    bridge.start()


def medi_register() -> None:
    if bpy is None:
        return
    _ensure_bridge_started()
    if not hasattr(bpy.app, "timers"):
        return
    bpy.app.timers.register(_process_blender_queue)


def medi_unregister() -> None:
    if bpy is None:
        return
    bridge.stop()
    try:
        bpy.app.timers.unregister(_process_blender_queue)
    except Exception:
        pass


bl_info = {
    "name": "MEDI Clinical 3D Visualization",
    "blender": (3, 0, 0),
    "category": "Medical",
    "version": (1, 0, 0),
    "author": "MEDI Systems",
    "description": "Real-time medical voice and patient state visualization in Blender.",
}


if bpy is not None:
    def register():
        medi_register()

    def unregister():
        medi_unregister()

    __all__ = ["register", "unregister"]
