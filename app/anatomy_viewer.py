"""
3D Anatomy Viewer for MediAI - interactive full-body anatomy model.
Supports multiple layers, region highlighting, and clinical overlay.
"""

import logging
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime
import json
import uuid

logger = logging.getLogger(__name__)


@dataclass
class AnatomyHighlight:
    """Highlight on anatomical region."""
    id: str
    region: str  # e.g., "chest", "abdomen", "heart", "lungs"
    condition: str  # e.g., "inflammation", "injury", "pain", "edema"
    severity: str  # "mild", "moderate", "severe"
    color: str = "#FF6B6B"  # Display color
    timestamp: datetime = field(default_factory=datetime.now)
    notes: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "region": self.region,
            "condition": self.condition,
            "severity": self.severity,
            "color": self.color,
            "timestamp": self.timestamp.isoformat(),
            "notes": self.notes,
        }


class AnatomyViewer:
    """3D full-body anatomy model viewer."""
    
    # Anatomical regions
    BODY_REGIONS = {
        "head": {
            "systems": ["nervous", "sensory"],
            "organs": ["brain", "eyes", "ears", "nose"],
        },
        "neck": {
            "systems": ["vascular", "nervous"],
            "organs": ["thyroid", "carotid"],
        },
        "chest": {
            "systems": ["cardiovascular", "respiratory"],
            "organs": ["heart", "lungs", "esophagus"],
        },
        "abdomen": {
            "systems": ["digestive", "urinary", "reproductive"],
            "organs": ["stomach", "liver", "kidneys", "pancreas", "intestines"],
        },
        "pelvis": {
            "systems": ["urinary", "reproductive"],
            "organs": ["bladder", "uterus", "prostate"],
        },
        "upper_extremity_right": {
            "systems": ["nervous", "skeletal", "muscular"],
            "organs": ["shoulder", "elbow", "wrist", "hand"],
        },
        "upper_extremity_left": {
            "systems": ["nervous", "skeletal", "muscular"],
            "organs": ["shoulder", "elbow", "wrist", "hand"],
        },
        "lower_extremity_right": {
            "systems": ["nervous", "skeletal", "muscular"],
            "organs": ["hip", "knee", "ankle", "foot"],
        },
        "lower_extremity_left": {
            "systems": ["nervous", "skeletal", "muscular"],
            "organs": ["hip", "knee", "ankle", "foot"],
        },
        "back": {
            "systems": ["nervous", "skeletal", "muscular"],
            "organs": ["spine", "spinal_cord"],
        },
    }
    
    # Available display layers
    ANATOMY_LAYERS = [
        "skin",
        "fascia",
        "muscle",
        "bone",
        "organ",
        "vascular",
        "nervous",
    ]
    
    # Condition-to-color mapping
    CONDITION_COLORS = {
        "normal": "#4CAF50",          # Green
        "pain": "#FF6B6B",            # Red
        "inflammation": "#FF9800",    # Orange
        "injury": "#F44336",          # Dark Red
        "swelling": "#E91E63",        # Pink
        "edema": "#9C27B0",           # Purple
        "infection": "#D32F2F",       # Dark Red
        "necrosis": "#000000",        # Black
        "ischemia": "#795548",        # Brown
    }
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.model_id = str(uuid.uuid4())
        self.visible_layers: Set[str] = set(self.ANATOMY_LAYERS)
        self.highlights: Dict[str, AnatomyHighlight] = {}
        self.selected_region: Optional[str] = None
        self.camera_position = {"x": 0, "y": 0, "z": 150}
        self.camera_rotation = {"x": 0, "y": 0, "z": 0}
        
        logger.info(f"Anatomy viewer initialized: {session_id}")
    
    def get_model_data(self) -> Dict[str, Any]:
        """Get 3D model data for rendering (glTF format structure)."""
        return {
            "id": self.model_id,
            "name": "Full Body Anatomy Model",
            "type": "gltf",
            "metadata": {
                "created": datetime.now().isoformat(),
                "regions": list(self.BODY_REGIONS.keys()),
                "available_layers": self.ANATOMY_LAYERS,
                "visible_layers": list(self.visible_layers),
            },
            "regions": self._get_region_data(),
            "camera": {
                "position": self.camera_position,
                "rotation": self.camera_rotation,
            },
            "highlights": [h.to_dict() for h in self.highlights.values()],
        }
    
    def _get_region_data(self) -> List[Dict]:
        """Get data for all anatomical regions."""
        regions = []
        
        for region_name, region_info in self.BODY_REGIONS.items():
            highlight = self.highlights.get(region_name)
            
            regions.append({
                "id": region_name,
                "name": region_name.replace("_", " ").title(),
                "systems": region_info.get("systems", []),
                "organs": region_info.get("organs", []),
                "highlight": highlight.to_dict() if highlight else None,
                "mesh_url": f"/models/{region_name}.gltf",  # Reference to actual model files
            })
        
        return regions
    
    def set_visible_layers(self, layers: List[str]) -> Set[str]:
        """Set which anatomy layers are visible."""
        valid_layers = set(layer for layer in layers if layer in self.ANATOMY_LAYERS)
        self.visible_layers = valid_layers
        
        logger.info(f"Visible layers updated: {list(self.visible_layers)}")
        return self.visible_layers
    
    def toggle_layer(self, layer: str) -> Set[str]:
        """Toggle visibility of a single layer."""
        if layer in self.ANATOMY_LAYERS:
            if layer in self.visible_layers:
                self.visible_layers.discard(layer)
            else:
                self.visible_layers.add(layer)
            logger.info(f"Layer toggled: {layer} -> {layer in self.visible_layers}")
        
        return self.visible_layers
    
    def add_highlight(self, region: str, condition: str, severity: str = "mild") -> Dict:
        """Add or update highlight on anatomical region."""
        if region not in self.BODY_REGIONS:
            logger.warning(f"Unknown region: {region}")
            return {}
        
        color = self.CONDITION_COLORS.get(condition.lower(), "#FF6B6B")
        
        highlight = AnatomyHighlight(
            id=str(uuid.uuid4()),
            region=region,
            condition=condition,
            severity=severity,
            color=color,
        )
        
        self.highlights[region] = highlight
        logger.info(f"Highlight added: {region} ({condition}, {severity})")
        
        return highlight.to_dict()
    
    def update_highlight(self, region: str, condition: str, severity: str = "mild", notes: str = "") -> Dict:
        """Update existing highlight."""
        if region not in self.highlights:
            return self.add_highlight(region, condition, severity)
        
        highlight = self.highlights[region]
        highlight.condition = condition
        highlight.severity = severity
        highlight.notes = notes
        highlight.color = self.CONDITION_COLORS.get(condition.lower(), "#FF6B6B")
        highlight.timestamp = datetime.now()
        
        logger.info(f"Highlight updated: {region} ({condition})")
        
        return highlight.to_dict()
    
    def remove_highlight(self, region: str) -> bool:
        """Remove highlight from region."""
        if region in self.highlights:
            del self.highlights[region]
            logger.info(f"Highlight removed: {region}")
            return True
        return False
    
    def clear_all_highlights(self) -> None:
        """Clear all highlights."""
        self.highlights.clear()
        logger.info("All highlights cleared")
    
    def get_current_highlights(self) -> List[Dict]:
        """Get all current highlights."""
        return [h.to_dict() for h in self.highlights.values()]
    
    def set_selected_region(self, region: str) -> Optional[Dict]:
        """Select anatomical region for inspection."""
        if region not in self.BODY_REGIONS:
            logger.warning(f"Unknown region: {region}")
            return None
        
        self.selected_region = region
        region_data = self.BODY_REGIONS[region]
        
        detail = {
            "region": region,
            "systems": region_data.get("systems", []),
            "organs": region_data.get("organs", []),
            "highlight": (
                self.highlights.get(region).to_dict() 
                if region in self.highlights else None
            ),
        }
        
        logger.info(f"Region selected: {region}")
        return detail
    
    def set_camera_position(self, x: float, y: float, z: float) -> Dict:
        """Update camera position (for 3D view control)."""
        self.camera_position = {"x": x, "y": y, "z": z}
        logger.debug(f"Camera position: {self.camera_position}")
        return self.camera_position
    
    def set_camera_rotation(self, x: float, y: float, z: float) -> Dict:
        """Update camera rotation (for 3D view control)."""
        self.camera_rotation = {"x": x, "y": y, "z": z}
        logger.debug(f"Camera rotation: {self.camera_rotation}")
        return self.camera_rotation
    
    def rotate_model(self, axis: str, angle: float) -> Dict:
        """Rotate 3D model by angle on axis."""
        if axis == "x":
            self.camera_rotation["x"] += angle
        elif axis == "y":
            self.camera_rotation["y"] += angle
        elif axis == "z":
            self.camera_rotation["z"] += angle
        
        # Normalize angles
        for key in self.camera_rotation:
            self.camera_rotation[key] = self.camera_rotation[key] % 360
        
        return self.camera_rotation
    
    def zoom(self, factor: float) -> Dict:
        """Zoom camera in/out."""
        if factor > 0:  # Zoom in
            self.camera_position["z"] *= (1 - factor)
        else:  # Zoom out
            self.camera_position["z"] *= (1 - factor)
        
        # Clamp z distance
        self.camera_position["z"] = max(50, min(300, self.camera_position["z"]))
        
        return self.camera_position
    
    def get_organ_details(self, organ: str) -> Dict:
        """Get clinical details about specific organ."""
        organ_details = {
            "heart": {
                "system": "cardiovascular",
                "function": "Pumps blood throughout the body",
                "location": "chest",
                "normal_range": {"heart_rate": "60-100 bpm", "blood_pressure": "< 120/80 mmHg"},
                "common_conditions": ["hypertension", "arrhythmia", "heart failure", "myocarditis"],
            },
            "lungs": {
                "system": "respiratory",
                "function": "Gas exchange (oxygen/CO2)",
                "location": "chest",
                "normal_range": {"respiratory_rate": "12-20 breaths/min", "o2_sat": "> 95%"},
                "common_conditions": ["pneumonia", "asthma", "COPD", "pulmonary embolism"],
            },
            "liver": {
                "system": "digestive",
                "function": "Metabolic processing, detoxification",
                "location": "abdomen",
                "normal_range": {"ast": "10-34 U/L", "alt": "7-35 U/L"},
                "common_conditions": ["hepatitis", "cirrhosis", "fatty liver", "hepatic failure"],
            },
            "kidneys": {
                "system": "urinary",
                "function": "Filtration, fluid/electrolyte balance",
                "location": "abdomen",
                "normal_range": {"creatinine": "0.7-1.3 mg/dL", "bun": "7-20 mg/dL"},
                "common_conditions": ["kidney disease", "acute kidney injury", "kidney stones", "hypertension"],
            },
            "pancreas": {
                "system": "digestive/endocrine",
                "function": "Hormone regulation, enzyme production",
                "location": "abdomen",
                "normal_range": {"glucose": "70-100 mg/dL", "amylase": "30-110 U/L"},
                "common_conditions": ["diabetes", "pancreatitis", "pancreatic cancer"],
            },
            "brain": {
                "system": "nervous",
                "function": "Central command and control",
                "location": "head",
                "normal_range": {"neuro_status": "alert and oriented"},
                "common_conditions": ["stroke", "seizure", "traumatic brain injury", "dementia"],
            },
        }
        
        return organ_details.get(organ.lower(), {})
    
    def create_scan_overlay(self, scan_type: str, scan_data: Dict) -> Dict:
        """Overlay medical imaging data on anatomy model."""
        overlay = {
            "id": str(uuid.uuid4()),
            "type": scan_type,  # "CT", "MRI", "X-ray", "Ultrasound"
            "timestamp": datetime.now().isoformat(),
            "region": scan_data.get("region", ""),
            "findings": scan_data.get("findings", []),
            "measurements": scan_data.get("measurements", {}),
            "url": scan_data.get("url", ""),
        }
        
        logger.info(f"Scan overlay created: {scan_type} of {scan_data.get('region')}")
        
        return overlay
    
    def get_full_body_summary(self) -> Dict:
        """Get summary of all current highlights across body."""
        summary = {
            "total_regions_highlighted": len(self.highlights),
            "by_severity": {
                "mild": len([h for h in self.highlights.values() if h.severity == "mild"]),
                "moderate": len([h for h in self.highlights.values() if h.severity == "moderate"]),
                "severe": len([h for h in self.highlights.values() if h.severity == "severe"]),
            },
            "by_condition": {},
            "regions": list(self.highlights.keys()),
        }
        
        # Group by condition
        for highlight in self.highlights.values():
            condition = highlight.condition
            if condition not in summary["by_condition"]:
                summary["by_condition"][condition] = 0
            summary["by_condition"][condition] += 1
        
        return summary
