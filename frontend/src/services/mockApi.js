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
export async function loginClinicalUser({ email, password }) {
  await delay(DELAY_MS.short);
  if (!email || !password) {
    throw new ApiError("Enter your email and password to continue.", "INVALID_CREDENTIALS");
  }
  return { name: email.split("@")[0].replace(/[._]/g, " "), role: "Clinical Professional" };
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
  loginClinicalUser,
};

export { ApiError };
