from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

EMERGENCY_KEYWORDS = {
    "severe chest pain",
    "difficulty breathing",
    "shortness of breath",
    "loss of consciousness",
    "severe bleeding",
    "stroke",
    "severe allergic reaction",
    "fainting",
    "suicidal",
    "severe injury",
}


def _normalize_text(value: Optional[str]) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _contains_emergency_signals(symptoms: List[str], context: str) -> bool:
    combined = " ".join(symptoms).lower() + " " + _normalize_text(context)
    return any(keyword in combined for keyword in EMERGENCY_KEYWORDS)


def analyze_case(payload: Dict[str, Any]) -> Dict[str, Any]:
    patient_name = payload.get("patient_name") or "Patient"
    symptoms = payload.get("symptoms") or []
    context = payload.get("context") or ""
    scan_summary = payload.get("scan_summary") or "No scan data provided"

    symptom_text = ", ".join(symptoms) if symptoms else "No stated symptoms"
    emergency = _contains_emergency_signals(symptoms, context)

    if emergency:
        urgency = "Emergency"
        guidance = (
            "This situation may require urgent medical assessment. Seek emergency care immediately "
            "or call local emergency services. Do not delay while waiting for diagnosis."
        )
    elif any(term in symptom_text.lower() for term in ["pain", "bleeding", "numbness", "weakness"]):
        urgency = "Urgent review"
        guidance = (
            "Please arrange a prompt medical assessment. Describe the pain, its location, and whether it is worsening."
        )
    elif any(term in symptom_text.lower() for term in ["fatigue", "nausea", "dizziness", "fever"]):
        urgency = "Monitor closely"
        guidance = "A clinician should review this soon if symptoms persist or worsen."
    else:
        urgency = "Routine follow-up"
        guidance = "This may still warrant a clinical review; gather more details and consider a scheduled appointment."

    structured_summary = {
        "patient_name": patient_name,
        "main_concern": symptom_text if symptoms else "Unspecified concern",
        "symptoms": symptoms,
        "duration": payload.get("duration") or "Not specified",
        "severity": payload.get("severity") or "Not specified",
        "location": payload.get("location") or "Not specified",
        "associated_symptoms": payload.get("associated_symptoms") or [],
        "medications": payload.get("medications") or [],
        "allergies": payload.get("allergies") or [],
        "medical_history": payload.get("medical_history") or [],
        "scan_summary": scan_summary,
        "context": context,
    }

    doctor_note = (
        f"Patient: {patient_name}. Main concern: {structured_summary['main_concern']}. "
        f"Severity: {structured_summary['severity']}. Duration: {structured_summary['duration']}. "
        f"Focus area: {structured_summary['location']}. Related context: {context or 'No extra context provided.'}"
    )

    return {
        "status": "analysis_complete",
        "urgency": urgency,
        "guidance": guidance,
        "confidence": "high" if emergency else "medium",
        "summary": {
            "headline": "AI-assisted clinical intake summary",
            "doctor_note": doctor_note,
            "structured_summary": structured_summary,
        },
        "next_questions": [
            "When did the symptom begin?",
            "Is it worsening, constant, or intermittent?",
            "Are there any related symptoms such as fever, breathlessness, dizziness, or rash?",
            "Has the patient had prior diagnoses, allergies, or medications that affect this concern?",
        ],
        "safety_notice": "This system supports triage and organization only; it is not a final medical diagnosis.",
    }


def extract_location_keywords(text: str) -> List[str]:
    if not text:
        return []
    keywords = re.findall(r"\b(?:chest|head|neck|back|knee|ankle|shoulder|arm|leg|hip|abdomen|waist|pelvis|left|right|upper|lower)\w*\b", text.lower())
    return sorted(set(keywords))
