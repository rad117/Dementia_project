"""Nested response schemas for GET /assessments/{id} and
GET /assessments/{id}/results -- shaped to match exactly what
frontend/src/services/mockApi.js already produces (verified against
frontend/src/data/generate.js, frontend/src/utils/clinicalNarratives.js,
frontend/src/data/mockTranscripts.js, and
frontend/src/components/clinical/AssessmentAnalysisSections.jsx), so the
real API is a drop-in replacement for the mock with zero frontend changes.

Uses alias_generator=to_camel rather than per-field Field(alias=...) --
there are 60+ fields here and a hand-written alias is exactly the kind of
place a typo silently breaks one frontend field. backend/services/
results_mapper.py is the only code that constructs these models.
"""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class _CamelModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class TaskInfo(_CamelModel):
    id: str
    name: str


class QualityInfo(_CamelModel):
    audio_quality: str
    background_noise: str
    asr_confidence: float
    language_match: bool
    duration_seconds: float
    task_complete: bool


class ScreeningInfo(_CamelModel):
    estimate: float
    needs_clinician_review: bool
    model_version: str


class AssessmentInfo(_CamelModel):
    id: str
    patient_id: str
    date: str
    language: str
    task: TaskInfo
    quality: QualityInfo | None
    screening: ScreeningInfo | None
    status: str


class SpeechFeaturesAdvanced(_CamelModel):
    jitter_percent: float
    shimmer_percent: float
    hnr_db: float
    spectral_centroid_hz: float
    mfcc_summary: list[float]


class SpeechFeatures(_CamelModel):
    total_duration_sec: float
    speech_duration_sec: float
    speech_silence_ratio: float
    pause_ratio_percent: float
    speech_rate_wpm: float
    articulation_rate_wpm: float
    pause_count: float
    pause_frequency_per_min: float
    mean_pause_sec: float
    longest_pause_sec: float
    response_latency_sec: float
    voice_breaks: float
    mean_f0: float
    f0_variability: float
    energy_rms: float
    advanced: SpeechFeaturesAdvanced


class LinguisticFeatures(_CamelModel):
    total_words: float
    unique_words: float
    vocabulary_diversity: float
    repetitions: float
    revisions: float
    generic_substitutions: float
    fillers: float
    retrieval_events: float
    avg_sentence_length: float
    incomplete_utterances: float
    syntactic_complexity: float


class SemanticFeatures(_CamelModel):
    concept_coverage: float
    concepts_identified: float
    concepts_expected: float
    semantic_relevance: float
    information_density: float
    coherence: float
    redundancy: float


class ProductionFeatures(_CamelModel):
    pronunciation_deviation_events: float | None
    # phoneme_deviation_events is deliberately out of scope (see
    # ml/inference/predict.py's _PRONUNCIATION_CONFIDENCE_THRESHOLD
    # docstring) -- always null, never computed.
    phoneme_deviation_events: float | None = None


class FeatureSet(_CamelModel):
    speech: SpeechFeatures
    linguistic: LinguisticFeatures
    semantic: SemanticFeatures
    production: ProductionFeatures
    quality: QualityInfo


class TranscriptSegment(_CamelModel):
    id: str
    start_sec: float
    end_sec: float
    text: str
    type: str
    concept: str | None = None


class Transcript(_CamelModel):
    assessment_id: str
    language: str
    generated_note: str
    segments: list[TranscriptSegment]


class ChangeItem(_CamelModel):
    key: str
    label: str
    unit: str
    higher_is_better: bool
    current_value: float
    previous_value: float
    percent: float
    direction: str


class AiSummary(_CamelModel):
    overview: str
    observed_changes: list[str]
    speech_patterns: list[str]
    language_patterns: list[str]
    assessment_quality: list[str]
    review_points: list[str]
    disclaimer: str


class ModelExplanationOut(_CamelModel):
    indicators: list[str]
    model_version: str
    is_demo_explanation: bool


class AssessmentResultsV2(_CamelModel):
    assessment: AssessmentInfo
    features: FeatureSet | None
    transcript: Transcript | None
    previous_assessment: AssessmentInfo | None
    previous_features: FeatureSet | None
    what_changed: list[ChangeItem] | None
    ai_summary: AiSummary | None
    model_explanation: ModelExplanationOut | None
