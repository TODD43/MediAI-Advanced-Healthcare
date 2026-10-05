from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class PatientState(BaseModel):
    main_concern: Optional[str] = None
    symptoms: List[str] = Field(default_factory=list)
    duration: Optional[str] = None
    severity: Optional[str] = None
    location: Optional[str] = None
    associated_symptoms: List[str] = Field(default_factory=list)
    medications: List[str] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)
    medical_history: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)

    @field_validator("symptoms", "associated_symptoms", "medications", "allergies", "medical_history", "notes")
    @classmethod
    def normalize_list(cls, value: List[str]) -> List[str]:
        if value is None:
            return []
        return [str(item).strip() for item in value if str(item).strip()]

    def merge_update(self, payload: Dict[str, Any]) -> None:
        for key, value in payload.items():
            if key not in self.model_fields:
                continue
            if isinstance(value, list):
                current = getattr(self, key)
                for item in value:
                    text = str(item).strip()
                    if text and text not in current:
                        current.append(text)
                setattr(self, key, current)
            elif value is not None:
                setattr(self, key, value)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class AnalyzeRequest(BaseModel):
    patient_name: Optional[str] = None
    age: Optional[int] = None
    symptoms: List[str] = Field(default_factory=list)
    duration: Optional[str] = None
    severity: Optional[str] = None
    location: Optional[str] = None
    associated_symptoms: List[str] = Field(default_factory=list)
    medications: List[str] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)
    medical_history: List[str] = Field(default_factory=list)
    scan_summary: Optional[str] = None
    context: Optional[str] = None
