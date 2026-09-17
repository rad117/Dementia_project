import { generatedAnalysis } from "./generate.js";
import { getAssessmentById } from "./mockAssessments.js";
import { generateTranscript } from "./mockTranscripts.js";

export function getAnalysisForAssessment(assessmentId) {
  return generatedAnalysis[assessmentId] ?? null;
}

export function getTranscriptForAssessment(assessmentId) {
  const assessment = getAssessmentById(assessmentId);
  const analysis = getAnalysisForAssessment(assessmentId);
  if (!assessment || !analysis) return null;
  return generateTranscript(assessment, analysis);
}
