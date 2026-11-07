// Mock implementation of the API service interface. Simulates network
// delay and occasional/forceable errors so the frontend behaves like it is
// talking to a real backend before one exists.
import { mockPatients, getPatientById } from "../data/mockPatients.js";
import {
  listAssessmentsForPatient,
  findAssessment,
  listAssessments,
  addAssessment,
  nextAssessmentId,
  setAnalysis,
  getAnalysis,
  getTranscript,
} from "../data/runtimeStore.js";
import { generateTranscript } from "../data/mockTranscripts.js";
import { generateLiveFeatures, generateLiveQuality, computeScreeningEstimate, REVIEW_THRESHOLD } from "../data/generate.js";
import { pictureDescriptionTask } from "../data/mockTasks.js";
import {
  computeWhatChanged,
  generateAiSummary,
  generateModelExplanation,
} from "../utils/clinicalNarratives.js";

const DELAY_MS = { short: 350, medium: 700, long: 1100 };

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Tests/manual QA can force the next call to fail by setting
 * window.__mockApiFailNext = "uploadAssessmentAudio" (or any method name).
 * This keeps the demo deterministic by default while still exercising the
 * real error UI paths.
 */
function shouldForceFail(methodName) {
  if (typeof window === "undefined") return false;
  if (window.__mockApiFailNext === methodName) {
    window.__mockApiFailNext = null;
    return true;
  }
  return false;
}

class ApiError extends Error {
  constructor(message, code = "MOCK_ERROR") {
    super(message);
    this.code = code;
  }
}

export async function getPatients(params = {}) {
  await delay(DELAY_MS.medium);
  if (shouldForceFail("getPatients")) {
    throw new ApiError("We couldn't reach the analysis service. Please try again.");
  }

  const { query = "", language = "all", reviewStatus = "all", sort = "recent" } = params;

  let results = mockPatients.map((patient) => {
    const history = listAssessmentsForPatient(patient.id);
    const latest = history[history.length - 1] ?? null;
    return { ...patient, latestAssessment: latest, assessmentCount: history.length };
  });

  const normalizedQuery = query.trim().toLowerCase();
  if (normalizedQuery) {
    results = results.filter(
      (p) => p.name.toLowerCase().includes(normalizedQuery) || p.id.toLowerCase().includes(normalizedQuery)
    );
  }

  if (language !== "all") {
    results = results.filter((p) => p.preferredLanguage === language);
  }

  if (reviewStatus !== "all") {
    results = results.filter((p) => {
      const needsReview = p.latestAssessment?.screening.needsClinicianReview;
      return reviewStatus === "needs-review" ? needsReview : !needsReview;
    });
  }

  results.sort((a, b) => {
    if (sort === "name") return a.name.localeCompare(b.name);
    if (sort === "review") {
      return (b.latestAssessment?.screening.needsClinicianReview ? 1 : 0) -
        (a.latestAssessment?.screening.needsClinicianReview ? 1 : 0);
    }
    const dateA = a.latestAssessment?.date ?? "";
    const dateB = b.latestAssessment?.date ?? "";
    return dateB.localeCompare(dateA);
  });

  return results;
}

export async function getPatient(id) {
  await delay(DELAY_MS.short);
  const patient = getPatientById(id);
  if (!patient) return null;
  const history = listAssessmentsForPatient(id);
  return { ...patient, latestAssessment: history[history.length - 1] ?? null, assessmentCount: history.length };
}

export async function getPatientAssessments(id) {
  await delay(DELAY_MS.short);
  return listAssessmentsForPatient(id);
}

export async function getAssessment(id) {
  await delay(DELAY_MS.short);
  return findAssessment(id);
}

export async function createAssessment(payload) {
  await delay(DELAY_MS.short);
  const id = nextAssessmentId();
  const assessment = {
    id,
    patientId: payload.patientId,
    date: new Date().toISOString().slice(0, 10),
    language: payload.language,
    task: { id: payload.taskId ?? pictureDescriptionTask.id, name: pictureDescriptionTask.name },
    quality: null,
    screening: null,
    status: "pending_recording",
  };
  addAssessment(assessment);
  return assessment;
}

export async function uploadAssessmentAudio(id, audioBlob) {
  await delay(DELAY_MS.long);
  if (shouldForceFail("uploadAssessmentAudio")) {
    throw new ApiError("We couldn't reach the analysis service. Your assessment has not been lost. Please try again.");
  }

  const assessment = findAssessment(id);
  if (!assessment) throw new ApiError("Assessment not found.", "NOT_FOUND");

  const quality = generateLiveQuality(id + (audioBlob?.size ?? 0));
  const features = generateLiveFeatures(id, quality);
  const estimate = computeScreeningEstimate(features);

  assessment.quality = quality;
  assessment.screening = {
    estimate,
    needsClinicianReview: estimate >= REVIEW_THRESHOLD,
    modelVersion: "screening-v0.1-demo",
  };
  assessment.status = "complete";

  const transcript = generateTranscript(assessment, features);
  setAnalysis(id, features, transcript);

  return { success: true, assessmentId: id };
}

export async function getAssessmentResults(id) {
  await delay(DELAY_MS.medium);
  const assessment = findAssessment(id);
  if (!assessment) return null;
  const features = getAnalysis(id);
  const transcript = getTranscript(id);
  if (!features) return { assessment, features: null, transcript: null };

  const history = listAssessmentsForPatient(assessment.patientId);
  const idx = history.findIndex((a) => a.id === id);
  const previousAssessment = idx > 0 ? history[idx - 1] : null;
  const previousFeatures = previousAssessment ? getAnalysis(previousAssessment.id) : null;

  const whatChanged = computeWhatChanged(features, previousFeatures);
  const aiSummary = generateAiSummary({
    assessment,
    features,
    previousFeatures,
    whatChanged,
    quality: assessment.quality,
  });
  const modelExplanation = generateModelExplanation(features, assessment);

  return {
    assessment,
    features,
    transcript,
    previousAssessment,
    previousFeatures,
    whatChanged,
    aiSummary,
    modelExplanation,
  };
}

export async function getAllAssessments() {
  await delay(DELAY_MS.short);
  return listAssessments();
}

// Placeholder identity check for the participant login screen — real
// authentication is owned by the backend team.
export async function verifyParticipantCode(code) {
  await delay(DELAY_MS.short);
  const normalized = code.trim().toUpperCase();
  const patient = mockPatients.find((p) => p.loginCode.toUpperCase() === normalized);
  if (!patient) {
    throw new ApiError("We couldn't find that participant code. Please check the code or ask a staff member for help.", "INVALID_CODE");
  }
  return { patientId: patient.id, name: patient.name };
}

// Placeholder clinical login — accepts any non-empty credentials in demo mode.
export async function verifyParticipantAssisted(patientId) {
  await delay(DELAY_MS.short);
  const patient = getPatientById(patientId);
  if (!patient) {
    throw new ApiError("Patient not found.", "PATIENT_NOT_FOUND");
  }
  return { patientId: patient.id, name: patient.name };
}

export async function loginClinicalUser({ email, password }) {
  await delay(DELAY_MS.short);
  if (!email || !password) {
    throw new ApiError("Enter your email and password to continue.", "INVALID_CREDENTIALS");
  }
  return { name: email.split("@")[0].replace(/[._]/g, " "), role: "Clinical Professional" };
}

export async function logout() {
  await delay(DELAY_MS.short);
  return null;
}

// ---- Safety monitoring (mirrors backend /monitoring/*) -------------------
// In-memory only. The mock reports the live camera as unavailable, exactly
// what the real backend does on a machine without the vision libraries.
let mockMonitoringAlerts = [];

const MOCK_SCENARIOS = [
  { id: "kitchen_fall", title: "Stove left on, then a fall", description: "Cooking, walks away from a lit stove, then falls in the hallway." },
  { id: "bathroom_fall", title: "Fall in the bathroom", description: "Becomes unsteady at the sink, falls and stays on the floor." },
  { id: "night_wandering", title: "Night-time wandering", description: "Up at 2 a.m., opens the front door and leaves the monitored area." },
  { id: "tap_running", title: "Tap left running", description: "Fills a glass at the sink and walks away with the tap on." },
  { id: "repeated_task", title: "Repeating an unfinished task", description: "Keeps going back to search for the same thing without finishing." },
];

// Same alerts the real rules engine produces for each scenario
// (see monitoring/service.py SCENARIOS), newest first.
const FALL = [
  ["CRITICAL", "fall_motionless", "On the floor and not moving for 8s.", "posture=lying, on_floor=True, motion=still", "Attend immediately. Treat as a fall until confirmed otherwise."],
  ["CRITICAL", "fall_event", "A fall was observed.", "fall_in_progress=True, sudden_descent=True", "Attend immediately. Do not move them if they report neck, back or hip pain — call for medical help."],
  ["MEDIUM", "unsteady", "Appears unsteady on their feet.", "location=bathroom sink", "Check in. Look for trip hazards and consider a seated task."],
];
const MOCK_SCENARIO_ALERTS = {
  kitchen_fall: [
    ["CRITICAL", "fall_motionless", "On the floor and not moving for 10s.", "posture=lying, on_floor=True, motion=still", "Attend immediately. Treat as a fall until confirmed otherwise."],
    ["CRITICAL", "fall_event", "A fall was observed.", "fall_in_progress=True, sudden_descent=True, location=hallway", "Attend immediately. Do not move them if they report neck, back or hip pain — call for medical help."],
    ["MEDIUM", "prolonged_absence", "Not seen in the monitored area for 35 s.", "last seen 35 s ago", "Check where they are. Confirm they have not left the home."],
    ["HIGH", "unattended_heat_stove", "The stove has been on and unattended for 25 s.", "stove state=on for 25 s; no person in view.", "Attend now and turn the stove off."],
  ],
  bathroom_fall: FALL,
  night_wandering: [
    ["MEDIUM", "prolonged_absence", "Not seen in the monitored area for 30 s.", "last seen 30 s ago", "Check where they are. Confirm they have not left the home."],
    ["HIGH", "night_door_open", "An external door is open at 02:00.", "door open since 02:00:20", "Attend now. Confirm they have not left the home."],
    ["MEDIUM", "night_activity", "Up and moving about at 02:00.", "activity=walking, location=bedroom doorway", "Check in. Night wandering raises fall and exit risk."],
  ],
  tap_running: [
    ["MEDIUM", "unattended_water", "Tap running unattended for 30 s.", "water_running=True for 30 s", "Check for overflow and turn the tap off."],
  ],
  repeated_task: [
    ["MEDIUM", "repetition_searching for keys", "Has repeated 'searching for keys' 3 times in 1 min without finishing.", "activity log: searching for keys ×3", "Check in gently. Offer to help complete the task, or redirect to something else."],
  ],
};

function mockScenarioAlerts(scenario, patientId) {
  const at = (secondsAgo) => new Date(Date.now() - secondsAgo * 1000).toISOString().slice(0, 19);
  return MOCK_SCENARIO_ALERTS[scenario].map(([level, kind, summary, evidence, action], i) => ({
    at: at(5 + i * 10), level, kind, summary, evidence, action,
    patient_id: patientId ?? null, source: "demo", scenario,
  }));
}

export async function getMonitoringStatus() {
  await delay(DELAY_MS.short);
  return {
    live_camera: {
      available: false,
      missing: ["torch", "transformers"],
      observer: "not_loaded",
      observer_error: null,
      last_error: null,
    },
    counters: { frames: 0, clips: 0, observer: "not_loaded" },
    state: { heat_on: {}, water_running_s: 0, seconds_since_seen: null, on_floor_s: 0, recent_activities: [] },
  };
}

export async function getMonitoringAlerts({ patient_id: patientId, limit = 50 } = {}) {
  await delay(DELAY_MS.short);
  return mockMonitoringAlerts.filter((a) => !patientId || a.patient_id === patientId).slice(0, limit);
}

export async function getMonitoringScenarios() {
  await delay(DELAY_MS.short);
  return MOCK_SCENARIOS;
}

export async function runMonitoringDemo({ scenario = "kitchen_fall", patientId } = {}) {
  await delay(DELAY_MS.medium);
  if (!MOCK_SCENARIO_ALERTS[scenario]) throw new ApiError(`Unknown scenario "${scenario}".`, "NOT_FOUND");
  const fresh = mockScenarioAlerts(scenario, patientId);
  const kept = mockMonitoringAlerts.filter((a) => !(a.scenario === scenario && a.patient_id === (patientId ?? null)));
  mockMonitoringAlerts = [...fresh, ...kept];
  return fresh;
}

export async function clearMonitoringDemo() {
  await delay(DELAY_MS.short);
  const deleted = mockMonitoringAlerts.length;
  mockMonitoringAlerts = [];
  return { deleted };
}

// ---- Live camera (the mock has no analysis pipeline) ----------------------
export async function submitMonitoringFrame() {
  await delay(DELAY_MS.short);
  return { status: "unavailable", missing: ["backend"] };
}

export async function getLastObservation() {
  await delay(DELAY_MS.short);
  return {};
}

// ---- Family alert contacts (mirrors backend /monitoring/contacts) ---------
let mockContacts = [];
let nextContactId = 1;

export async function getGuardianContacts(patientId) {
  await delay(DELAY_MS.short);
  return mockContacts.filter((c) => c.patient_id === patientId);
}

export async function addGuardianContact({ patientId, name, phone, channel = "sms" }) {
  await delay(DELAY_MS.short);
  if (!/^\+[1-9]\d{7,14}$/.test(phone || "")) {
    throw new ApiError("Phone must be in international format, e.g. +919876543210", "VALIDATION");
  }
  const contact = { id: nextContactId++, patient_id: patientId, name, phone, channel };
  mockContacts = [...mockContacts, contact];
  return contact;
}

export async function deleteGuardianContact(contactId) {
  await delay(DELAY_MS.short);
  mockContacts = mockContacts.filter((c) => c.id !== contactId);
  return { deleted: contactId };
}

export async function sendGuardianTest() {
  await delay(DELAY_MS.short);
  return { status: "dry_run" };
}

export const mockApi = {
  getPatients,
  getPatient,
  getPatientAssessments,
  getAssessment,
  createAssessment,
  uploadAssessmentAudio,
  getAssessmentResults,
  getAllAssessments,
  verifyParticipantCode,
  verifyParticipantAssisted,
  loginClinicalUser,
  logout,
  getMonitoringStatus,
  getMonitoringAlerts,
  getMonitoringScenarios,
  runMonitoringDemo,
  clearMonitoringDemo,
  submitMonitoringFrame,
  getLastObservation,
  getGuardianContacts,
  addGuardianContact,
  deleteGuardianContact,
  sendGuardianTest,
};

export { ApiError };
