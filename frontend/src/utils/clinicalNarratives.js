// Deterministic, template-based narrative generation from structured data.
// No external model or LLM call — every sentence traces back to a concrete
// field on the assessment/feature objects passed in.

const CHANGE_METRICS = [
  {
    key: "speechRateWpm",
    label: "Speech rate",
    get: (f) => f.speech.speechRateWpm,
    unit: "WPM",
    higherIsBetter: true,
  },
  {
    key: "pauseFrequencyPerMin",
    label: "Pause frequency",
    get: (f) => f.speech.pauseFrequencyPerMin,
    unit: "per min",
    higherIsBetter: false,
  },
  {
    key: "responseLatencySec",
    label: "Response latency",
    get: (f) => f.speech.responseLatencySec,
    unit: "sec",
    higherIsBetter: false,
  },
  {
    key: "conceptCoverage",
    label: "Concept coverage",
    get: (f) => f.semantic.conceptCoverage,
    unit: "",
    higherIsBetter: true,
  },
  {
    key: "vocabularyDiversity",
    label: "Vocabulary diversity",
    get: (f) => f.linguistic.vocabularyDiversity,
    unit: "",
    higherIsBetter: true,
  },
];

const NOISE_FLOOR_PERCENT = 3;

export function computeWhatChanged(currentFeatures, previousFeatures) {
  if (!previousFeatures) return null;

  const items = CHANGE_METRICS.map((metric) => {
    const currentValue = metric.get(currentFeatures);
    const previousValue = metric.get(previousFeatures);
    const delta = currentValue - previousValue;
    const percent = previousValue === 0 ? 0 : (delta / Math.abs(previousValue)) * 100;
    let direction = "steady";
    if (Math.abs(percent) >= NOISE_FLOOR_PERCENT) {
      direction = delta > 0 ? "increased" : "decreased";
    }
    return {
      ...metric,
      currentValue,
      previousValue,
      percent: Math.round(Math.abs(percent)),
      direction,
    };
  });

  return items;
}

export function generateAiSummary({ assessment, features, previousFeatures, whatChanged, quality }) {
  const overview = `Assessment ${assessment.id} recorded a ${assessment.task.name.toLowerCase()} task in ${assessment.language}, lasting ${quality.durationSeconds} seconds. Screening estimate: ${(assessment.screening.estimate * 100).toFixed(0)}/100 (illustrative).`;

  const observedChanges =
    whatChanged && whatChanged.some((c) => c.direction !== "steady")
      ? whatChanged
          .filter((c) => c.direction !== "steady")
          .map((c) => `${c.label} ${c.direction} by ${c.percent}% versus the previous assessment.`)
      : previousFeatures
      ? ["No measured indicator changed by more than the noise threshold versus the previous assessment."]
      : ["No previous assessment is available for comparison."];

  const speechPatterns = [
    `Speech rate measured at ${features.speech.speechRateWpm} WPM with a pause ratio of ${features.speech.pauseRatioPercent}%.`,
    `Mean pause duration ${features.speech.meanPauseSec}s; longest pause ${features.speech.longestPauseSec}s.`,
    `Response latency measured at ${features.speech.responseLatencySec}s.`,
  ];

  const languagePatterns = [
    `Vocabulary diversity ${features.linguistic.vocabularyDiversity} across ${features.linguistic.totalWords} total words (${features.linguistic.uniqueWords} unique).`,
    `${features.linguistic.fillers} filler instances and ${features.linguistic.repetitions} repetitions observed.`,
    `Concept coverage: ${features.semantic.conceptsIdentified} of ${features.semantic.conceptsExpected} expected task concepts identified.`,
  ];

  const assessmentQuality = [
    `Audio quality: ${quality.audioQuality}. Background noise: ${quality.backgroundNoise}.`,
    `ASR confidence: ${(quality.asrConfidence * 100).toFixed(0)}%.`,
    quality.audioQuality === "poor" || quality.asrConfidence < 0.75
      ? "Recording quality may limit the reliability of derived indicators."
      : "Recording quality was sufficient for the derived indicators.",
  ];

  const reviewPoints = [];
  if (assessment.screening.needsClinicianReview) {
    reviewPoints.push("Composite screening estimate is elevated relative to this patient's baseline — recommend clinician review.");
  }
  if (whatChanged?.some((c) => c.key === "conceptCoverage" && c.direction === "decreased")) {
    reviewPoints.push("Concept coverage decreased versus the previous assessment.");
  }
  if (whatChanged?.some((c) => c.key === "responseLatencySec" && c.direction === "increased")) {
    reviewPoints.push("Response latency increased versus the previous assessment.");
  }
  if (quality.asrConfidence < 0.75) {
    reviewPoints.push("Lower ASR confidence — consider requesting a repeat recording in quieter conditions.");
  }
  if (reviewPoints.length === 0) {
    reviewPoints.push("No indicator-based review flags were raised for this assessment.");
  }

  return {
    overview,
    observedChanges,
    speechPatterns,
    languagePatterns,
    assessmentQuality,
    reviewPoints,
    disclaimer:
      "This is a deterministic, structured-data summary generated for clinical review. It is not a diagnosis and does not represent patient-reported history.",
  };
}

export function generateModelExplanation(features, assessment) {
  const indicators = [];
  if (features.speech.pauseRatioPercent > 30) indicators.push("Higher pause ratio");
  if (features.speech.responseLatencySec > 2.4) indicators.push("Longer response latency");
  if (features.speech.speechRateWpm < 95) indicators.push("Lower speech rate");
  if (features.linguistic.vocabularyDiversity < 0.6) indicators.push("Lower vocabulary diversity");
  if (features.semantic.conceptCoverage < 0.65) indicators.push("Lower concept coverage");
  if (features.linguistic.repetitions >= 3) indicators.push("Increased repetitions");

  if (indicators.length === 0) {
    indicators.push("No indicator exceeded its demo contribution threshold for this assessment.");
  }

  return {
    indicators,
    modelVersion: assessment.screening.modelVersion,
    isDemoExplanation: true,
  };
}
