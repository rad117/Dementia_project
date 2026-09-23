import KeyIndicatorCard from "./KeyIndicatorCard.jsx";
import QualityCard from "./QualityCard.jsx";
import ScreeningSummary from "./ScreeningSummary.jsx";
import FeatureSection from "./FeatureSection.jsx";
import TranscriptViewer from "./TranscriptViewer.jsx";
import ChangeSummary from "./ChangeSummary.jsx";
import AISummary from "./AISummary.jsx";
import ModelExplanation from "./ModelExplanation.jsx";
import Accordion from "../common/Accordion.jsx";
import Stagger from "../motion/Stagger.jsx";
import clinicalStyles from "./clinical.module.css";
import styles from "./AssessmentAnalysisSections.module.css";

function buildSparkline(history, getValue) {
  return history.map((h) => ({ value: getValue(h.features) }));
}

export default function AssessmentAnalysisSections({ results, history = [] }) {
  const { assessment, features, transcript, whatChanged, aiSummary, modelExplanation } = results;

  if (!features) {
    return (
      <div className={clinicalStyles.panel}>
        <p style={{ color: "var(--muted)" }}>Analysis is not yet available for this assessment.</p>
      </div>
    );
  }

  const keyIndicators = [
    {
      label: "Speech rate",
      value: features.speech.speechRateWpm,
      unit: "WPM",
      key: "speechRateWpm",
      getValue: (f) => f.speech.speechRateWpm,
    },
    {
      label: "Pause ratio",
      value: features.speech.pauseRatioPercent,
      unit: "%",
      key: "pauseRatioPercent",
      getValue: (f) => f.speech.pauseRatioPercent,
    },
    {
      label: "Response latency",
      value: features.speech.responseLatencySec,
      unit: "sec",
      key: "responseLatencySec",
      getValue: (f) => f.speech.responseLatencySec,
    },
    {
      label: "Vocabulary diversity",
      value: features.linguistic.vocabularyDiversity,
      unit: "",
      key: "vocabularyDiversity",
      getValue: (f) => f.linguistic.vocabularyDiversity,
    },
    {
      label: "Concept coverage",
      value: `${features.semantic.conceptsIdentified} / ${features.semantic.conceptsExpected}`,
      unit: "",
      key: "conceptCoverage",
      getValue: (f) => f.semantic.conceptCoverage,
    },
  ];

  const changeByKey = {};
  (whatChanged ?? []).forEach((c) => (changeByKey[c.key] = c));

  return (
    <Stagger className={styles.stack}>
      <Stagger.Item className={clinicalStyles.twoCol}>
        <ScreeningSummary screening={assessment.screening} />
        <QualityCard quality={assessment.quality} />
      </Stagger.Item>

      <Stagger.Item>
        <h2 className={styles.groupTitle}>Key indicators</h2>
        <div className={styles.indicatorGrid}>
          {keyIndicators.map((indicator) => {
            const change = changeByKey[indicator.key];
            return (
              <KeyIndicatorCard
                key={indicator.key}
                label={indicator.label}
                value={indicator.value}
                unit={indicator.unit}
                direction={change?.direction}
                percent={change?.percent}
                sparklineData={history.length >= 2 ? buildSparkline(history, indicator.getValue) : null}
              />
            );
          })}
        </div>
      </Stagger.Item>

      <Stagger.Item className={clinicalStyles.twoCol}>
        <FeatureSection
          title="Speech characteristics"
          items={[
            { label: "Total duration", value: features.speech.totalDurationSec, unit: "sec" },
            { label: "Speech duration", value: features.speech.speechDurationSec, unit: "sec" },
            { label: "Speech/silence ratio", value: features.speech.speechSilenceRatio },
            { label: "Response latency", value: features.speech.responseLatencySec, unit: "sec" },
            { label: "Speech rate", value: features.speech.speechRateWpm, unit: "WPM" },
            { label: "Articulation rate", value: features.speech.articulationRateWpm, unit: "WPM" },
            { label: "Pause count", value: features.speech.pauseCount },
            { label: "Pause frequency", value: features.speech.pauseFrequencyPerMin, unit: "/min" },
            { label: "Mean pause duration", value: features.speech.meanPauseSec, unit: "sec" },
            { label: "Longest pause", value: features.speech.longestPauseSec, unit: "sec" },
            { label: "Voice breaks", value: features.speech.voiceBreaks },
            { label: "Mean pitch (F0)", value: features.speech.meanF0, unit: "Hz" },
            { label: "Pitch variability", value: features.speech.f0Variability },
            { label: "Energy / intensity", value: features.speech.energyRms },
          ]}
        >
          <Accordion title="Advanced acoustic analysis">
            <FeatureSection
              bare
              title=""
              items={[
                { label: "Jitter", value: features.speech.advanced.jitterPercent, unit: "%" },
                { label: "Shimmer", value: features.speech.advanced.shimmerPercent, unit: "%" },
                { label: "HNR", value: features.speech.advanced.hnrDb, unit: "dB" },
                { label: "Spectral centroid", value: features.speech.advanced.spectralCentroidHz, unit: "Hz" },
              ]}
              footnote={`MFCC summary (5 coefficients): ${features.speech.advanced.mfccSummary.join(", ")}`}
            />
          </Accordion>
        </FeatureSection>

        <FeatureSection
          title="Linguistic analysis"
          items={[
            { label: "Total words", value: features.linguistic.totalWords },
            { label: "Unique words", value: features.linguistic.uniqueWords },
            { label: "Vocabulary diversity", value: features.linguistic.vocabularyDiversity, tooltip: "Ratio of unique words to total words." },
            { label: "Fillers", value: features.linguistic.fillers },
            { label: "Repetitions", value: features.linguistic.repetitions },
            { label: "Revisions", value: features.linguistic.revisions },
            { label: "Word-finding indicators", value: features.linguistic.retrievalEvents, tooltip: "Instances suggesting word-retrieval effort." },
            { label: "Generic substitutions", value: features.linguistic.genericSubstitutions, tooltip: "Use of vague words (e.g. 'thing') in place of a specific term." },
            { label: "Average utterance length", value: features.linguistic.avgSentenceLength, unit: "words" },
            { label: "Incomplete utterances", value: features.linguistic.incompleteUtterances },
            { label: "Syntactic complexity", value: features.linguistic.syntacticComplexity },
          ]}
        />
      </Stagger.Item>

      <Stagger.Item className={clinicalStyles.twoCol}>
        <FeatureSection
          title="Semantic / task analysis"
          items={[
            { label: "Concept coverage", value: `${features.semantic.conceptsIdentified} / ${features.semantic.conceptsExpected}` },
            { label: "Semantic relevance", value: features.semantic.semanticRelevance },
            { label: "Information density", value: features.semantic.informationDensity },
            { label: "Coherence", value: features.semantic.coherence },
            { label: "Redundancy", value: features.semantic.redundancy },
          ]}
          footnote={`${features.semantic.conceptsIdentified} of ${features.semantic.conceptsExpected} expected task concepts were identified.`}
        />

        <FeatureSection
          title="Speech production"
          items={[
            { label: "Pronunciation variation events", value: features.production.pronunciationDeviationEvents },
            { label: "Phoneme-level deviation events", value: features.production.phonemeDeviationEvents },
            { label: "ASR confidence", value: `${(assessment.quality.asrConfidence * 100).toFixed(0)}%` },
          ]}
          footnote="Accent, dialect, hearing, speech production differences, dentures, recording quality and language-specific phonology can all affect these measures."
        />
      </Stagger.Item>

      <Stagger.Item>
        <ChangeSummary whatChanged={whatChanged} />
      </Stagger.Item>

      <Stagger.Item>
        <TranscriptViewer transcript={transcript} />
      </Stagger.Item>

      <Stagger.Item className={clinicalStyles.twoCol}>
        <AISummary summary={aiSummary} />
        <ModelExplanation explanation={modelExplanation} />
      </Stagger.Item>
    </Stagger>
  );
}
