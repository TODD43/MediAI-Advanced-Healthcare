"""
Clinical Dashboard for MediAI - doctor-facing management system.
Handles patient records, triage, orders, notes, and follow-up coordination.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict, field
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class TriageUrgency(str, Enum):
    """ESI (Emergency Severity Index) triage levels."""
    EMERGENT = "emergent"  # Immediate life threat
    URGENT = "urgent"       # Needs rapid evaluation
    SEMI_URGENT = "semi_urgent"  # Can wait some time
    NON_URGENT = "non_urgent"     # Stable, routine
    UNKNOWN = "unknown"


@dataclass
class ClinicalNote:
    """Clinical note in patient record."""
    id: str
    timestamp: datetime
    author: str
    content: str
    note_type: str  # "intake", "assessment", "plan", "progress", "general"
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "author": self.author,
            "content": self.content,
            "type": self.note_type,
        }


@dataclass
class CareOrder:
    """Order for lab, imaging, referral, or procedure."""
    id: str
    timestamp: datetime
    order_type: str  # "lab", "imaging", "referral", "procedure"
    description: str
    urgency: str  # "routine", "urgent", "stat"
    status: str = "pending"  # "pending", "in_progress", "completed", "cancelled"
    assigned_to: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "type": self.order_type,
            "description": self.description,
            "urgency": self.urgency,
            "status": self.status,
            "assigned_to": self.assigned_to,
        }


@dataclass
class FollowUp:
    """Scheduled follow-up appointment or care plan."""
    id: str
    visit_type: str  # "appointment", "phone", "telehealth", "referral"
    scheduled_date: datetime
    description: str
    status: str = "scheduled"  # "scheduled", "completed", "cancelled"
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "visit_type": self.visit_type,
            "scheduled_date": self.scheduled_date.isoformat(),
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class VitalSigns:
    """Patient vital signs."""
    timestamp: datetime
    temperature: Optional[float] = None  # Celsius
    heart_rate: Optional[int] = None  # BPM
    respiratory_rate: Optional[int] = None  # breaths/min
    blood_pressure_systolic: Optional[int] = None  # mmHg
    blood_pressure_diastolic: Optional[int] = None  # mmHg
    oxygen_saturation: Optional[float] = None  # %
    weight: Optional[float] = None  # kg
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "temperature": self.temperature,
            "heart_rate": self.heart_rate,
            "respiratory_rate": self.respiratory_rate,
            "bp": {
                "systolic": self.blood_pressure_systolic,
                "diastolic": self.blood_pressure_diastolic,
            },
            "oxygen_saturation": self.oxygen_saturation,
            "weight": self.weight,
        }


@dataclass
class Medication:
    """Patient medication."""
    id: str
    name: str
    dosage: str
    frequency: str  # "once daily", "twice daily", "as needed", etc.
    route: str  # "oral", "IV", "IM", "topical", etc.
    start_date: datetime
    end_date: Optional[datetime] = None
    indication: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "dosage": self.dosage,
            "frequency": self.frequency,
            "route": self.route,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "indication": self.indication,
        }


@dataclass
class PatientRecord:
    """Complete patient medical record."""
    patient_id: str
    mrn: str  # Medical Record Number
    name: str
    date_of_birth: datetime
    gender: str
    contact: str
    
    # Current visit
    visit_id: str
    visit_date: datetime
    chief_complaint: str = ""
    
    # Clinical data
    vital_signs: List[VitalSigns] = field(default_factory=list)
    medications: List[Medication] = field(default_factory=list)
    allergies: List[str] = field(default_factory=list)
    past_medical_history: List[str] = field(default_factory=list)
    surgical_history: List[str] = field(default_factory=list)
    
    # Assessment and management
    assessment: str = ""
    working_diagnoses: List[str] = field(default_factory=list)
    differential_diagnoses: List[str] = field(default_factory=list)
    
    # Records
    clinical_notes: List[ClinicalNote] = field(default_factory=list)
    care_orders: List[CareOrder] = field(default_factory=list)
    followups: List[FollowUp] = field(default_factory=list)
    
    # Triage
    triage_urgency: TriageUrgency = TriageUrgency.UNKNOWN
    triage_category: str = "general"
    
    def to_dict(self) -> Dict:
        return {
            "patient_id": self.patient_id,
            "mrn": self.mrn,
            "name": self.name,
            "date_of_birth": self.date_of_birth.isoformat(),
            "gender": self.gender,
            "contact": self.contact,
            "visit": {
                "id": self.visit_id,
                "date": self.visit_date.isoformat(),
                "chief_complaint": self.chief_complaint,
            },
            "vital_signs": [v.to_dict() for v in self.vital_signs],
            "medications": [m.to_dict() for m in self.medications],
            "allergies": self.allergies,
            "past_medical_history": self.past_medical_history,
            "surgical_history": self.surgical_history,
            "assessment": self.assessment,
            "working_diagnoses": self.working_diagnoses,
            "differential_diagnoses": self.differential_diagnoses,
            "clinical_notes": [n.to_dict() for n in self.clinical_notes],
            "care_orders": [o.to_dict() for o in self.care_orders],
            "followups": [f.to_dict() for f in self.followups],
            "triage": {
                "urgency": self.triage_urgency.value,
                "category": self.triage_category,
            },
        }


class ClinicalDashboard:
    """Clinical dashboard for doctor/nurse management."""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.patient: Optional[PatientRecord] = None
        self.triage_status: Dict[str, Any] = {
            "urgency": "unknown",
            "category": "general",
            "rationale": "",
            "timestamp": datetime.now().isoformat(),
        }
        self._initialize_patient()
    
    def _initialize_patient(self) -> None:
        """Initialize a new patient record."""
        patient_id = str(uuid.uuid4())
        mrn = f"MRN{patient_id[:8].upper()}"
        
        self.patient = PatientRecord(
            patient_id=patient_id,
            mrn=mrn,
            name="Patient (To Be Identified)",
            date_of_birth=datetime.now() - timedelta(days=365*40),  # Default 40 years
            gender="Unknown",
            contact="",
            visit_id=str(uuid.uuid4()),
            visit_date=datetime.now(),
            chief_complaint="",
        )
    
    def get_current_patient(self) -> Dict:
        """Get current patient record."""
        if not self.patient:
            return {}
        return self.patient.to_dict()
    
    def update_patient_demographics(self, demographics: Dict) -> Dict:
        """Update patient demographic information."""
        if not self.patient:
            return {}
        
        self.patient.name = demographics.get("name", self.patient.name)
        self.patient.gender = demographics.get("gender", self.patient.gender)
        self.patient.contact = demographics.get("contact", self.patient.contact)
        
        if "date_of_birth" in demographics:
            try:
                dob = datetime.fromisoformat(demographics["date_of_birth"])
                self.patient.date_of_birth = dob
            except:
                pass
        
        logger.info(f"Updated patient demographics: {self.patient.mrn}")
        return self.patient.to_dict()
    
    def set_chief_complaint(self, complaint: str) -> str:
        """Set chief complaint from patient intake."""
        if self.patient:
            self.patient.chief_complaint = complaint
            logger.info(f"Chief complaint: {complaint}")
        return complaint
    
    def add_vital_signs(self, vitals: Dict) -> Dict:
        """Add vital signs measurement."""
        if not self.patient:
            return {}
        
        vital = VitalSigns(
            timestamp=datetime.now(),
            temperature=vitals.get("temperature"),
            heart_rate=vitals.get("heart_rate"),
            respiratory_rate=vitals.get("respiratory_rate"),
            blood_pressure_systolic=vitals.get("bp_systolic"),
            blood_pressure_diastolic=vitals.get("bp_diastolic"),
            oxygen_saturation=vitals.get("o2_sat"),
            weight=vitals.get("weight"),
        )
        
        self.patient.vital_signs.append(vital)
        logger.info(f"Vital signs recorded: HR={vital.heart_rate}, BP={vital.blood_pressure_systolic}/{vital.blood_pressure_diastolic}")
        
        return vital.to_dict()
    
    def add_medication(self, med_data: Dict) -> Dict:
        """Add medication to patient record."""
        if not self.patient:
            return {}
        
        medication = Medication(
            id=str(uuid.uuid4()),
            name=med_data.get("name", ""),
            dosage=med_data.get("dosage", ""),
            frequency=med_data.get("frequency", ""),
            route=med_data.get("route", "oral"),
            start_date=datetime.now(),
            indication=med_data.get("indication", ""),
        )
        
        self.patient.medications.append(medication)
        logger.info(f"Medication added: {medication.name}")
        
        return medication.to_dict()
    
    def add_allergy(self, allergy: str) -> List[str]:
        """Add documented allergy."""
        if self.patient and allergy not in self.patient.allergies:
            self.patient.allergies.append(allergy)
            logger.warning(f"Allergy documented: {allergy}")
        return self.patient.allergies if self.patient else []
    
    def add_clinical_note(self, author: str, content: str, note_type: str = "general") -> Dict:
        """Add clinical note to patient record."""
        if not self.patient:
            return {}
        
        note = ClinicalNote(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            author=author,
            content=content,
            note_type=note_type,
        )
        
        self.patient.clinical_notes.append(note)
        logger.info(f"Clinical note added ({note_type}): {author}")
        
        return note.to_dict()
    
    def add_care_order(self, order_type: str, description: str, urgency: str = "routine") -> Dict:
        """Create order for lab, imaging, referral, or procedure."""
        if not self.patient:
            return {}
        
        order = CareOrder(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            order_type=order_type,  # "lab", "imaging", "referral", "procedure"
            description=description,
            urgency=urgency,
        )
        
        self.patient.care_orders.append(order)
        logger.info(f"Care order created: {order_type} ({urgency})")
        
        return order.to_dict()
    
    def add_diagnosis(self, diagnosis: str, is_working: bool = True) -> List[str]:
        """Add working or differential diagnosis."""
        if not self.patient:
            return []
        
        if is_working:
            if diagnosis not in self.patient.working_diagnoses:
                self.patient.working_diagnoses.append(diagnosis)
            return self.patient.working_diagnoses
        else:
            if diagnosis not in self.patient.differential_diagnoses:
                self.patient.differential_diagnoses.append(diagnosis)
            return self.patient.differential_diagnoses
    
    def set_triage_status(self, urgency: str, category: str = "general", rationale: str = "") -> Dict:
        """Update triage assessment."""
        self.triage_status = {
            "urgency": urgency,
            "category": category,
            "rationale": rationale,
            "timestamp": datetime.now().isoformat(),
        }
        
        if self.patient:
            self.patient.triage_urgency = TriageUrgency(urgency)
            self.patient.triage_category = category
        
        logger.info(f"Triage updated: {urgency} ({category})")
        
        return self.triage_status
    
    def schedule_followup(self, visit_type: str, scheduled_date: str, description: str = "") -> Dict:
        """Schedule follow-up appointment or care plan."""
        if not self.patient:
            return {}
        
        try:
            followup_date = datetime.fromisoformat(scheduled_date)
        except:
            followup_date = datetime.now() + timedelta(days=7)  # Default: 7 days
        
        followup = FollowUp(
            id=str(uuid.uuid4()),
            visit_type=visit_type,
            scheduled_date=followup_date,
            description=description,
        )
        
        self.patient.followups.append(followup)
        logger.info(f"Follow-up scheduled: {visit_type} on {followup_date.date()}")
        
        return followup.to_dict()
    
    def get_findings_by_region(self, region: str) -> List[Dict]:
        """Get clinical findings related to anatomical region."""
        if not self.patient:
            return []
        
        findings = []
        
        # Search notes for region mentions
        for note in self.patient.clinical_notes:
            if region.lower() in note.content.lower():
                findings.append({
                    "type": "note",
                    "source": note.author,
                    "content": note.content,
                    "timestamp": note.timestamp.isoformat(),
                })
        
        # Search orders for region mentions
        for order in self.patient.care_orders:
            if region.lower() in order.description.lower():
                findings.append({
                    "type": "order",
                    "order_type": order.order_type,
                    "content": order.description,
                    "urgency": order.urgency,
                    "timestamp": order.timestamp.isoformat(),
                })
        
        logger.info(f"Found {len(findings)} findings for region: {region}")
        return findings
    
    def generate_summary(self) -> Dict:
        """Generate clinical summary for handoff or referral."""
        if not self.patient:
            return {}
        
        latest_vitals = self.patient.vital_signs[-1] if self.patient.vital_signs else None
        
        summary = {
            "patient": f"{self.patient.name} ({self.patient.mrn})",
            "age": int((datetime.now() - self.patient.date_of_birth).days / 365),
            "chief_complaint": self.patient.chief_complaint,
            "current_vital_signs": latest_vitals.to_dict() if latest_vitals else None,
            "active_medications": len(self.patient.medications),
            "allergies": self.patient.allergies,
            "working_diagnoses": self.patient.working_diagnoses,
            "pending_orders": len([o for o in self.patient.care_orders if o.status == "pending"]),
            "triage_level": self.patient.triage_urgency.value,
            "next_followup": (
                self.patient.followups[-1].scheduled_date.isoformat()
                if self.patient.followups else None
            ),
        }
        
        return summary
