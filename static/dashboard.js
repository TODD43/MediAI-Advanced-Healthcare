const API_BASE = "http://localhost:8000";

let currentSection = "overview";

function showSection(sectionName) {
  document.querySelectorAll(".dash-section").forEach((el) => {
    el.classList.remove("active");
  });
  document.getElementById(sectionName).classList.add("active");
  currentSection = sectionName;

  if (sectionName === "overview") {
    loadAnalytics();
  } else if (sectionName === "sessions") {
    loadSessions();
  } else if (sectionName === "patients") {
    loadPatients();
  } else if (sectionName === "analytics") {
    loadDetailedAnalytics();
  }
}

async function loadAnalytics() {
  try {
    const response = await fetch(`${API_BASE}/api/doctor/analytics/summary`);
    const data = await response.json();

    document.getElementById("totalSessions").textContent = data.total_sessions || 0;
    document.getElementById("activeSessions").textContent = data.active_sessions || 0;
    document.getElementById("totalPatients").textContent = data.total_patients || 0;
    document.getElementById("closedSessions").textContent = data.closed_sessions || 0;
  } catch (error) {
    console.error("Error loading analytics:", error);
  }
}

async function loadSessions() {
  try {
    const response = await fetch(`${API_BASE}/api/doctor/sessions`);
    const data = await response.json();
    const sessions = data.sessions || [];

    const html = sessions
      .map((session) => {
        const state = session.state || {};
        const transcriptCount = (session.transcript || []).length;
        return `
          <div class="session-card" onclick="viewSessionDetail('${session.session_id}')">
            <div class="session-header">
              <h3>${session.patient_name}</h3>
              <span class="status-badge ${session.status}">${session.status}</span>
            </div>
            <div class="session-detail">
              <p><strong>Main concern:</strong> ${state.main_concern || "N/A"}</p>
              <p><strong>Symptoms:</strong> ${(state.symptoms || []).join(", ") || "N/A"}</p>
              <p><strong>Severity:</strong> ${state.severity || "N/A"}</p>
              <p><strong>Transcript entries:</strong> ${transcriptCount}</p>
              <p class="session-time">Created: ${new Date(session.created_at).toLocaleString()}</p>
            </div>
          </div>
        `;
      })
      .join("");

    document.getElementById("sessionsList").innerHTML = html || "<p>No sessions found.</p>";
  } catch (error) {
    console.error("Error loading sessions:", error);
  }
}

async function viewSessionDetail(sessionId) {
  try {
    const response = await fetch(`${API_BASE}/api/doctor/sessions/${sessionId}`);
    const data = await response.json();
    const session = data.session || {};

    const transcriptHtml = (session.transcript || [])
      .map(
        (entry) => `
      <div class="transcript-entry ${entry.role}">
        <strong>${entry.role.toUpperCase()}:</strong> ${entry.text}
        <span class="timestamp">${new Date(entry.timestamp).toLocaleTimeString()}</span>
      </div>
    `
      )
      .join("");

    const detailsHtml = `
      <div class="session-detail-modal">
        <h2>${session.patient_name} - Full Session</h2>
        <div class="session-state">
          <h3>Patient State</h3>
          <pre>${JSON.stringify(session.state, null, 2)}</pre>
        </div>
        <div class="session-transcript">
          <h3>Transcript</h3>
          ${transcriptHtml}
        </div>
      </div>
    `;

    alert(`Session Details:\n\n${detailsHtml}`);
  } catch (error) {
    console.error("Error loading session detail:", error);
  }
}

async function loadPatients() {
  try {
    const response = await fetch(`${API_BASE}/api/doctor/patients`);
    const data = await response.json();
    const patients = data.patients || [];

    const html = patients
      .map((patient) => {
        const diagnoses = patient.diagnoses || [];
        const notes = patient.notes || [];
        return `
          <div class="patient-card">
            <div class="patient-header">
              <h3>${patient.patient_id}</h3>
            </div>
            <div class="patient-detail">
              <p><strong>Diagnoses:</strong> ${diagnoses.length}</p>
              <p><strong>Clinical notes:</strong> ${notes.length}</p>
              <p class="patient-time">Updated: ${new Date(patient.updated_at).toLocaleString()}</p>
            </div>
            <div class="patient-actions">
              <button onclick="addNote('${patient.patient_id}')">Add Note</button>
              <button onclick="addDiagnosis('${patient.patient_id}')">Add Diagnosis</button>
            </div>
          </div>
        `;
      })
      .join("");

    document.getElementById("patientsList").innerHTML = html || "<p>No patients found.</p>";
  } catch (error) {
    console.error("Error loading patients:", error);
  }
}

async function addNote(patientId) {
  const note = prompt("Enter clinical note:");
  if (!note) return;

  try {
    const response = await fetch(`${API_BASE}/api/doctor/patients/${patientId}/notes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ note, doctor: "Dr. User" }),
    });
    const data = await response.json();
    alert("Note added successfully!");
    loadPatients();
  } catch (error) {
    console.error("Error adding note:", error);
  }
}

async function addDiagnosis(patientId) {
  const diagnosis = prompt("Enter diagnosis:");
  if (!diagnosis) return;
  const icdCode = prompt("Enter ICD code (optional):");
  const confidence = prompt("Confidence level (low/medium/high):") || "medium";

  try {
    const response = await fetch(`${API_BASE}/api/doctor/patients/${patientId}/diagnosis`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ diagnosis, icd_code: icdCode, confidence }),
    });
    const data = await response.json();
    alert("Diagnosis recorded!");
    loadPatients();
  } catch (error) {
    console.error("Error adding diagnosis:", error);
  }
}

async function loadDetailedAnalytics() {
  try {
    const response = await fetch(`${API_BASE}/api/doctor/analytics/summary`);
    const data = await response.json();

    const html = `
      <div class="analytics-summary">
        <h3>Session Statistics</h3>
        <table class="analytics-table">
          <tr><td>Total Sessions:</td><td>${data.total_sessions}</td></tr>
          <tr><td>Active Sessions:</td><td>${data.active_sessions}</td></tr>
          <tr><td>Closed Sessions:</td><td>${data.closed_sessions}</td></tr>
          <tr><td>Total Patients:</td><td>${data.total_patients}</td></tr>
        </table>
      </div>
    `;
    document.getElementById("analyticsSummary").innerHTML = html;
  } catch (error) {
    console.error("Error loading analytics:", error);
  }
}

// Initialize on page load
window.addEventListener("DOMContentLoaded", () => {
  loadAnalytics();
  setInterval(loadAnalytics, 5000); // Refresh every 5 seconds
});
