// Internal deterministic generator for mock assessments + analysis features.
// Not part of the public data API — mockAssessments.js / mockAnalysis.js
// expose the slices other modules should import.
import { mockPatients } from "./mockPatients.js";
import { pictureDescriptionTask } from "./mockTasks.js";
import { seededFromString, range, roundTo, clamp } from "../utils/random.js";

// Composite screening-estimate cutoff used to populate the demo "needs
// review" queue. Calibrated against the generated dataset so a handful of
// later visits from declining-trend patients cross it — not a validated
// clinical threshold.
export const REVIEW_THRESHOLD = 0.45;

const TREND_DIRECTION = {
  // positive = metric gets "better" (higher speech rate, higher vocab, etc.) over time
  declining: -1,
  improving: 1,
  stable: 0,
  mixed: 0,
};

const MS_PER_DAY = 24 * 60 * 60 * 1000;

function assessmentDates(count, rng) {
  // Most recent assessment lands a few days before "today" in the demo timeline.
  const anchor = new Date("2026-09-14T00:00:00Z");
  const dates = [];
  let cursor = anchor.getTime();
  for (let i = 0; i < count; i++) {
    dates.unshift(new Date(cursor).toISOString().slice(0, 10));
    cursor -= Math.round(range(rng, 75, 130)) * MS_PER_DAY;
  }
  return dates; // oldest -> newest
}

function buildFeatureSet({ rng, index, trend, mixedSign, quality }) {
  const dir = trend === "mixed" ? mixedSign : TREND_DIRECTION[trend];
  const t = index; // 0 = oldest

  // Baselines with mild per-patient variation, then trend applied across visits.
  const speechRateWpm = clamp(roundTo(range(rng, 92, 118) + dir * t * range(rng, 6, 11)), 45, 150);
  const articulationRateWpm = clamp(roundTo(speechRateWpm + range(rng, 14, 22)), 60, 170);
  const pauseFrequencyPerMin = clamp(roundTo(range(rng, 10, 15) - dir * t * range(rng, 0.8, 1.6), 1), 4, 34);
  const meanPauseSec = clamp(roundTo(range(rng, 0.8, 1.2) - dir * t * range(rng, 0.05, 0.12), 2), 0.4, 3.2);
  const longestPauseSec = clamp(roundTo(meanPauseSec * range(rng, 2.4, 3.2), 1), 1, 9);
  const responseLatencySec = clamp(roundTo(range(rng, 1.6, 2.4) - dir * t * range(rng, 0.3, 0.55), 1), 0.8, 7);
  const speechSilenceRatio = clamp(roundTo(range(rng, 0.66, 0.8) + dir * t * range(rng, 0.018, 0.035), 2), 0.35, 0.92);
  const pauseRatioPercent = clamp(roundTo((1 - speechSilenceRatio) * 100), 6, 55);
  const voiceBreaks = Math.max(0, Math.round(range(rng, 1, 4) - dir * t * 0.3));
  const meanF0 = clamp(roundTo(range(rng, 150, 210)), 90, 260);
  const f0Variability = clamp(roundTo(range(rng, 0.32, 0.5), 2), 0.1, 0.7);
  const totalDurationSec = Math.round(range(rng, 45, 70));
  const speechDurationSec = Math.round(totalDurationSec * speechSilenceRatio);
  const pauseCount = Math.round((pauseFrequencyPerMin / 60) * totalDurationSec);
  const energyRms = clamp(roundTo(range(rng, 0.45, 0.7), 2), 0.2, 0.9);

  const totalWords = Math.max(20, Math.round((speechRateWpm / 60) * totalDurationSec));
  const vocabularyDiversity = clamp(roundTo(range(rng, 0.56, 0.72) + dir * t * range(rng, 0.018, 0.035), 2), 0.3, 0.85);
  const uniqueWords = Math.max(10, Math.round(totalWords * vocabularyDiversity));
  const repetitions = Math.max(0, Math.round(range(rng, 1, 4) - dir * t * 0.35));
  const revisions = Math.max(0, Math.round(range(rng, 0, 3) - dir * t * 0.25));
  const genericSubstitutions = Math.max(0, Math.round(range(rng, 0, 3) - dir * t * 0.2));
  const fillers = Math.max(0, Math.round(range(rng, 4, 9) - dir * t * 0.6));
  const retrievalEvents = Math.max(0, Math.round(range(rng, 1, 5) - dir * t * 0.4));
  const avgSentenceLength = clamp(roundTo(range(rng, 7.5, 9.5) + dir * t * 0.1, 1), 4, 14);
  const incompleteUtterances = Math.max(0, Math.round(range(rng, 1, 5) - dir * t * 0.4));
  const syntacticComplexity = clamp(roundTo(range(rng, 0.45, 0.62) + dir * t * range(rng, 0.005, 0.015), 2), 0.2, 0.85);

  const conceptsExpected = pictureDescriptionTask.expectedConcepts.length;
  const conceptsIdentified = clamp(
    Math.round(range(rng, 5, 8) + dir * t * range(rng, 0.55, 0.95)),
    2,
    conceptsExpected
  );
  const conceptCoverage = roundTo(conceptsIdentified / conceptsExpected, 2);
  const semanticRelevance = clamp(roundTo(range(rng, 0.62, 0.8) + dir * t * range(rng, 0.01, 0.02), 2), 0.3, 0.95);
  const informationDensity = clamp(roundTo(range(rng, 0.48, 0.65) + dir * t * range(rng, 0.008, 0.018), 2), 0.25, 0.85);
  const coherence = clamp(roundTo(range(rng, 0.58, 0.75) + dir * t * range(rng, 0.008, 0.018), 2), 0.3, 0.92);
  const redundancy = clamp(roundTo(range(rng, 0.16, 0.28) - dir * t * range(rng, 0.005, 0.015), 2), 0.05, 0.5);

  const pronunciationDeviationEvents = Math.max(0, Math.round(range(rng, 2, 6) - dir * t * 0.4));
  const phonemeDeviationEvents = Math.max(0, pronunciationDeviationEvents + Math.round(range(rng, 0, 3)));

  // Advanced acoustic — secondary/expandable, never surfaced on the main screen.
  const jitterPercent = clamp(roundTo(range(rng, 0.4, 1.1) - dir * t * 0.02, 2), 0.2, 2.5);
  const shimmerPercent = clamp(roundTo(range(rng, 2.5, 5.5) - dir * t * 0.08, 2), 1.5, 9);
  const hnrDb = clamp(roundTo(range(rng, 14, 22) + dir * t * 0.15, 1), 8, 28);
  const spectralCentroidHz = clamp(roundTo(range(rng, 1400, 2200)), 800, 3000);
  const mfccSummary = Array.from({ length: 5 }, (_, i) => roundTo(range(rng, -20, 20) + i, 2));

  return {
    speech: {
      totalDurationSec,
      speechDurationSec,
      speechSilenceRatio,
      pauseRatioPercent,
      speechRateWpm,
      articulationRateWpm,
      pauseCount,
      pauseFrequencyPerMin,
      meanPauseSec,
      longestPauseSec,
      responseLatencySec,
      voiceBreaks,
      meanF0,
      f0Variability,
      energyRms,
      advanced: { jitterPercent, shimmerPercent, hnrDb, spectralCentroidHz, mfccSummary },
    },
    linguistic: {
      totalWords,
      uniqueWords,
      vocabularyDiversity,
      repetitions,
      revisions,
      genericSubstitutions,
      fillers,
      retrievalEvents,
      avgSentenceLength,
      incompleteUtterances,
      syntacticComplexity,
    },
    semantic: {
      conceptCoverage,
      conceptsIdentified,
      conceptsExpected,
      semanticRelevance,
      informationDensity,
      coherence,
      redundancy,
    },
    production: {
      pronunciationDeviationEvents,
      phonemeDeviationEvents,
    },
    quality,
  };
}

function buildQuality(rng, forcePoor) {
  const asrConfidence = forcePoor
    ? clamp(roundTo(range(rng, 0.55, 0.68), 2), 0, 1)
    : clamp(roundTo(range(rng, 0.85, 0.97), 2), 0, 1);
  const audioQuality = forcePoor ? "fair" : asrConfidence > 0.9 ? "good" : "fair";
  const backgroundNoise = forcePoor ? "moderate" : asrConfidence > 0.9 ? "low" : "moderate";
  return {
    audioQuality,
    backgroundNoise,
    asrConfidence,
    languageMatch: !forcePoor || rng() > 0.3,
    durationSeconds: Math.round(range(rng, 45, 70)),
    taskComplete: true,
  };
}

function computeScreeningEstimate(features) {
  // Purely a demo composite so the number moves in the same direction as the
  // underlying indicators. Not a validated clinical formula.
  const speechScore = clamp((130 - features.speech.speechRateWpm) / 90, 0, 1);
  const pauseScore = clamp(features.speech.pauseRatioPercent / 55, 0, 1);
  const latencyScore = clamp(features.speech.responseLatencySec / 6, 0, 1);
  const vocabScore = clamp(1 - features.linguistic.vocabularyDiversity / 0.75, 0, 1);
  const conceptScore = clamp(1 - features.semantic.conceptCoverage, 0, 1);
  const composite =
    0.24 * speechScore + 0.2 * pauseScore + 0.2 * latencyScore + 0.18 * vocabScore + 0.18 * conceptScore;
  return roundTo(clamp(composite, 0.05, 0.95), 2);
}

function generateForPatient(patient) {
  const rng = seededFromString(patient.id);
  const count = patient.assessmentCount;
  const dates = assessmentDates(count, rng);
  const mixedSign = patient.trend === "mixed" ? (rng() > 0.5 ? 1 : -1) : 0;

  const assessments = [];
  const analysisByAssessmentId = {};

  dates.forEach((date, idx) => {
    const id = `A-${patient.id.slice(3)}${idx}`;
    const forcePoor = patient.id === "CA-1005" && idx === 1; // one deliberately poor-quality recording
    const quality = buildQuality(rng, forcePoor);
    const features = buildFeatureSet({ rng, index: idx, trend: patient.trend, mixedSign, quality });
    const estimate = computeScreeningEstimate(features);

    const assessment = {
      id,
      patientId: patient.id,
      date,
      language: patient.preferredLanguage,
      task: { id: pictureDescriptionTask.id, name: pictureDescriptionTask.name },
      quality,
      screening: {
        estimate,
        needsClinicianReview: estimate >= REVIEW_THRESHOLD,
        modelVersion: "screening-v0.1-demo",
      },
    };

    assessments.push(assessment);
    analysisByAssessmentId[id] = { assessmentId: id, ...features };
  });

  return { assessments, analysisByAssessmentId };
}

const allAssessments = [];
const allAnalysis = {};

for (const patient of mockPatients) {
  const { assessments, analysisByAssessmentId } = generateForPatient(patient);
  allAssessments.push(...assessments);
  Object.assign(allAnalysis, analysisByAssessmentId);
}

export const generatedAssessments = allAssessments;
export const generatedAnalysis = allAnalysis;

// Used by mockApi to synthesize a plausible result for a freshly recorded,
// live participant submission (not part of the seeded longitudinal dataset).
export function generateLiveFeatures(seed, quality) {
  const rng = seededFromString(seed);
  return buildFeatureSet({ rng, index: 0, trend: "stable", mixedSign: 0, quality });
}

export function generateLiveQuality(seed) {
  const rng = seededFromString(seed);
  return buildQuality(rng, false);
}

export { computeScreeningEstimate };
