async function analyzeCase() {
  const payload = {
    patient_name: document.getElementById('patientName').value || 'Patient',
    age: Number(document.getElementById('age').value || 0),
    severity: document.getElementById('severity').value,
    duration: document.getElementById('duration').value,
    symptoms: (document.getElementById('symptoms').value || '').split(',').map(item => item.trim()).filter(Boolean),
    location: document.getElementById('location').value,
    scan_summary: document.getElementById('scanSummary').value,
    context: document.getElementById('context').value,
  };

  try {
    const response = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await response.json();
    const summary = data.summary;
    document.getElementById('summaryBox').innerHTML = `
      <div><strong>Urgency:</strong> ${data.urgency}</div>
      <div><strong>Guidance:</strong> ${data.guidance}</div>
      <div><strong>Doctor note:</strong> ${summary.doctor_note}</div>
      <div><strong>Safety:</strong> ${data.safety_notice}</div>
    `;

    const steps = document.getElementById('nextSteps');
    steps.innerHTML = data.next_questions.map(q => `<li>${q}</li>`).join('');
  } catch (err) {
    document.getElementById('summaryBox').innerHTML = '<p>Error connecting to the analysis service.</p>';
  }
}

async function loadVoiceIntro() {
  try {
    const response = await fetch('/api/voice-session');
    const data = await response.json();
    document.getElementById('voiceGreeting').textContent = data.greeting;
  } catch {
    document.getElementById('voiceGreeting').textContent = 'Hi, I’m MediAI. Tell me the main concern and how long it has been happening.';
  }
}

document.getElementById('runAnalysis').addEventListener('click', analyzeCase);
window.addEventListener('DOMContentLoaded', loadVoiceIntro);
