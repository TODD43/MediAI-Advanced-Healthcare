# MediAI-Advanced-Healthcare

A next-generation healthcare AI platform designed for intelligent symptom analysis, AI-assisted patient triage, voice-first consultations, and 3D medical visualization workflows.

This project is a practical starter for a healthcare system that can:
- accept patient symptoms or scan summaries
- analyze and structure clinical concerns
- guide patients with safe, conversational AI
- prepare a concise clinical summary for doctors
- support future 3D visualization pipelines for imaging and anatomy modeling

Core features:
- AI-powered patient analysis
- voice agent for natural clinical conversations
- structured patient summary for clinicians
- medical triage logic with safety prompts
- healthcare dashboard UI
- future-ready integration with Blender, Cinema 4D, SolidWorks, and DICOM/3D imaging workflows

## Why this project

The original MediAI project is a strong voice-first medical assistant. This repository upgrades the concept into a broader healthcare intelligence platform focused on:
- doctor-ready patient intake
- scan-assisted clinical reasoning
- safe AI triage guidance
- immersive 3D visualization for anatomical review

## Architecture

- FastAPI backend for AI analysis and API endpoints
- Voice-first assistant logic optimized for patient conversations
- Frontend dashboard for summaries and scan review
- AI triage engine that flags emergencies and organizes information

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Then open:
- http://localhost:8000/

## API examples

### Health check

```bash
curl http://localhost:8000/api/health
```

### Analyze patient case

```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "patient_name": "Jane Doe",
    "symptoms": ["Chest pain", "Shortness of breath"],
    "duration": "2 hours",
    "severity": "High",
    "scan_summary": "Chest CT indicates possible pulmonary concern",
    "context": "Patient reports pain while walking"
  }'
```

## Safety policy

This project is for research and workflow prototyping only. It does not replace a physician and must never be used as a final medical diagnosis engine without clinician oversight.

## Future roadmap

- DICOM import pipeline
- AI imaging tagging for scans and x-rays
- anatomical 3D scene generation with Blender/Cinema 4D/SolidWorks compatible output
- doctor dashboard and EMR-ready structured summaries
- secure multimodal AI for patient and clinician workflows

## Voice-agent copy direction

The voice assistant was optimized from the MediAI concept to be:
- clinically cautious
- calm and conversational
- structured around symptom gathering
- prompt about emergency escalation without sounding robotic

Example voice prompt:

> "I’m here to help you describe what you’re feeling clearly. Tell me the main symptom, how long it has been happening, and whether it is getting worse. If this feels like an emergency, please seek urgent medical help now."

## Repository

This project was created as a healthcare intelligence starter based on the original MediAI direction and extended with a more advanced AI and visualization vision.
