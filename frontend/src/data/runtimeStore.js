// In-memory mutable store seeded from the generated mock data. Lets the
// participant flow "create" a real assessment during the session without
// mutating the deterministic generator output that clinical screens rely on.
import { mockAssessments } from "./mockAssessments.js";
import { getAnalysisForAssessment, getTranscriptForAssessment } from "./mockAnalysis.js";

const assessments = [...mockAssessments];
const analysisMap = {};
const transcriptMap = {};

for (const a of mockAssessments) {
  analysisMap[a.id] = getAnalysisForAssessment(a.id);
  transcriptMap[a.id] = getTranscriptForAssessment(a.id);
}

let nextSeq = 9000;

export function listAssessments() {
  return assessments;
}

export function findAssessment(id) {
  return assessments.find((a) => a.id === id) ?? null;
}

export function listAssessmentsForPatient(patientId) {
  return assessments
    .filter((a) => a.patientId === patientId)
    .sort((a, b) => a.date.localeCompare(b.date));
}

export function nextAssessmentId() {
  nextSeq += 1;
  return `A-LIVE-${nextSeq}`;
}

export function addAssessment(assessment) {
  assessments.push(assessment);
}

export function setAnalysis(assessmentId, analysis, transcript) {
  analysisMap[assessmentId] = analysis;
  transcriptMap[assessmentId] = transcript;
}

export function getAnalysis(assessmentId) {
  return analysisMap[assessmentId] ?? null;
}

export function getTranscript(assessmentId) {
  return transcriptMap[assessmentId] ?? null;
}
