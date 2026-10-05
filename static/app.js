async function analyzeCase() {
  const payload = {
    patient_name: document.getElementById('patientName').value || 'Patient',
    symptoms: (document.getElementById('symptoms').value || '').split(',').map((item) => item.trim()).filter(Boolean),
    duration: document.getElementById('duration').value,
    severity: document.getElementById('severity').value,
    location: document.getElementById('location').value,
    scan_summary: document.getElementById('scanSummary').value,
    context: document.getElementById('context').value,
  };

  try {
    const response = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await response.json();

    const summaryBox = document.getElementById('summaryBox');
    summaryBox.innerHTML = `
      <div><strong>Urgency:</strong> ${data.urgency}</div>
      <div><strong>Guidance:</strong> ${data.guidance}</div>
      <div><strong>Doctor note:</strong> ${data.summary.doctor_note}</div>
      <div><strong>Safety:</strong> ${data.safety_notice}</div>
    `;

    const steps = document.getElementById('nextSteps');
    steps.innerHTML = data.next_questions.map((item) => `<li>${item}</li>`).join('');
  } catch (error) {
    document.getElementById('summaryBox').innerHTML = '<p>Error connecting to the MEDI analysis service.</p>';
  }
}

async function loadVoiceIntro() {
  try {
    const response = await fetch('/api/voice-session');
    const data = await response.json();
    document.getElementById('voiceGreeting').textContent = data.greeting;
  } catch (error) {
    document.getElementById('voiceGreeting').textContent = 'Hi, I’m MEDI. Tell me the main symptom and how long it has been happening.';
  }
}

document.getElementById('runAnalysis').addEventListener('click', analyzeCase);
window.addEventListener('DOMContentLoaded', loadVoiceIntro);
