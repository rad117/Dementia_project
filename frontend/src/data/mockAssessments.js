import { generatedAssessments } from "./generate.js";

// Oldest -> newest per patient, already sorted globally by patientId then date.
export const mockAssessments = [...generatedAssessments].sort((a, b) => {
  if (a.patientId !== b.patientId) return a.patientId.localeCompare(b.patientId);
  return a.date.localeCompare(b.date);
});

export function getAssessmentById(id) {
  return mockAssessments.find((a) => a.id === id) ?? null;
}

export function getAssessmentsForPatient(patientId) {
  return mockAssessments
    .filter((a) => a.patientId === patientId)
    .sort((a, b) => a.date.localeCompare(b.date));
}

export function getPreviousAssessment(assessment) {
  const history = getAssessmentsForPatient(assessment.patientId);
  const idx = history.findIndex((a) => a.id === assessment.id);
  if (idx <= 0) return null;
  return history[idx - 1];
}

export function getLatestAssessmentForPatient(patientId) {
  const history = getAssessmentsForPatient(patientId);
  return history[history.length - 1] ?? null;
}
