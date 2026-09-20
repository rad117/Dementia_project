# CONTEXT.md — AI-Assisted Multilingual Cognitive Screening & Memory Assistance Platform

> Working context document. Read this first when picking the project back up — it tells you what the project is, where things stand, and what to do next. Full source detail lives in `Project_Master_Context_Team.pdf` (team meeting notes with the project supervisor, referred to as "ma'am").

## 1. Status Snapshot

- **As of:** 2026-09-20
- **Repo:** `rad117/Dementia_project` (GitHub) — Phase 0 backend skeleton, frontend, and a real ML baseline pipeline are all implemented and merged to `main`.
- **Dataset:** ADReSSo 2021 received and extracted to `data/adresso2021/` (gitignored — raw audio is never committed, see Section 8). Headline: 85 `Dementia/` + 79 `Normal/` `.wav` files, one recording per participant, binary label only. No demographics shipped with this download. **Language and task confirmed by the project supervisor (2026-09-20): English-only, Cookie Theft picture description** — see Section 12. 23 `Dementia/` filenames carry a `-i`/`_i` suffix and one is `..._severe.wav` — **meaning confirmed by the project supervisor (2026-09-20): `-i`/`_i` means the interviewer's voice was edited out of the recording (a preprocessing confound for pause/silence-based features, tracked via a manifest column and checked in training — see `docs/dataset_audit.md`); `_severe` means a confirmed severe-dementia case. This is a single (N=1) data point — not a basis for any severity-prediction feature or model (see Section 8).** Full aggregate audit: `docs/dataset_audit.md`.
- **Code:** Backend Phase 1 done — `backend/` now persists assessments in SQLite and serves the 3-step contract the frontend expects (`POST /assessments` → `POST /assessments/{id}/audio` → `GET /assessments/{id}/results`), backed by a real trained acoustic baseline model (see `ml/`); the original mock endpoint (`POST /api/assessments`, `model_version: "mock-0.0"`) is kept as a legacy demo/comparison harness. ML pipeline (`ml/`) Phase 1 first pass done — acoustics-only baseline (Logistic Regression + Random Forest, participant-level split, full metric set) trained on the real dataset; artifacts in `models/baseline_v1/` (gitignored). **ASR layer done** (`ml/asr/transcribe.py`, faster-whisper CPU/English) and **NLP/semantic layer done** (`ml/nlp/linguistic.py` — lexical diversity, pronoun/filler ratios, repetition, Cookie Theft concept coverage, TF-IDF sentence-coherence proxy) — both standalone, not yet fused into training.
- **Next concrete action:** (1) retrain fusing acoustic + ASR + NLP features into `train_baseline.py` and re-evaluate with the full metric set (Section 9 Phase 1/2); (2) get demographic metadata and storage/consent terms from ma'am (Section 12 — still open, lower urgency than language/task which are now resolved); (3) revisit the `needs_clinician_review` risk-score threshold (currently a placeholder, no clinical basis) once real evaluation results accumulate.

## 2. Project Summary

A web-based AI-assisted cognitive screening platform for older adults. Participants perform standardized speech tasks (primarily picture description); the system extracts acoustic, linguistic, and semantic indicators from the recording and combines them via an ML classifier to produce a screening estimate — **for screening/monitoring support, not standalone medical diagnosis**. The product wraps the research model in a multilingual assessment UI, an explainable-results dashboard, longitudinal tracking, and optional memory-assistance features drawn from SIH Problem Statement 26003.

## 3. Viability Assessment

**Verdict: Viable.** This is a well-studied research area (see DementiaBank/Pitt Corpus, ADReSS/ADReSSo challenges) — fusing acoustic + linguistic features and training a classical ML classifier (SVM / Random Forest / XGBoost) on picture-description speech is a proven, achievable approach for a team project, not a research moonshot. The software pipeline (frontend → recording → ASR → feature extraction → ML → dashboard) can be built and demoed *today* using mock data, which decouples engineering progress from dataset-arrival risk.

Key risks to keep in view, honestly:

- **Everything model-specific is blocked on the dataset.** Labels, languages present, sample size, and recordings-per-participant are all unknown until 2026-09-13 — no exact architecture or performance number can be promised before then.
- **Multilingual support is the hardest engineering piece.** Scope it to "whatever languages the dataset actually contains," not universal language coverage.
- **Do not overclaim clinical validity.** Statistical performance ≠ clinical validity; frame the product as an AI-assisted screening/research prototype throughout.
- **Speaker leakage is the easiest way to produce fake-good results** — see Section 8.

## 4. Objectives

**Research objective:** determine whether fusing acoustic, ASR/transcript, and NLP/semantic features from picture-description speech can distinguish dementia/impaired speech from controls better than any single feature layer alone, and characterize how well this generalizes across languages and tasks.

**Product objective:** deliver a usable multilingual web assessment that records a participant's speech, runs it through the analysis pipeline, and presents an interpretable screening profile with longitudinal history to a clinician/caregiver — flagging for review rather than diagnosing.

**Minimum Viable Product (MVP):**
1. User selects language.
2. Website shows a standardized picture/task.
3. Browser records the response.
4. Audio uploads to backend.
5. Backend runs preprocessing + feature extraction.
6. ASR generates a transcript where supported.
7. Model combines validated features → screening estimate.
8. Dashboard shows task results, key indicators, and model output.
9. Assessment is stored for longitudinal comparison.

Everything beyond this (games, reminders, caregiver workflows, webcam) is an extension — see Section 7.

## 5. System Pipeline

```
USER → WEB ASSESSMENT → STANDARDIZED TASK → AUDIO RECORDING → AUDIO PREPROCESSING
     → SPEECH/ACOUSTIC FEATURES + ASR → NLP/SEMANTIC FEATURES → FEATURE FUSION
     → ML MODEL → RISK/PROFILE → DASHBOARD
```

| Stage | Input | What happens | Output |
|---|---|---|---|
| 1. Assessment UI | Prompt/image | Show task + instructions in selected language | User response |
| 2. Recording | Microphone | Browser records speech | Audio file |
| 3. Audio processing | Audio | Clean/standardize, compute basic properties | Processed audio + acoustic features |
| 4. Speech recognition | Audio | ASR → transcript | Transcript |
| 5. Speech/NLP analysis | Audio + transcript | Fluency, pauses, vocabulary, semantics, repetitions | Feature vector |
| 6. ML inference | Feature vector | Apply trained classifier | Class/risk estimate |
| 7. Explanation | Model + features | Show contributing factors | Cognitive/speech profile |
| 8. Storage | Assessment result | Save history securely | Longitudinal record |

**Three analysis layers feeding the feature vector:**
- **Acoustic/paralinguistic** (*how* they spoke): duration, speech/silence ratio, pause count/duration, response latency, speech rate, pitch/prosody, energy, MFCCs.
- **ASR/transcript** (*what* they said): transcript, word/sentence counts, repetitions, filler markers, vocabulary usage, task-object mentions.
- **NLP/semantic** (*what it means*): semantic similarity to expected task content, concept coverage, lexical diversity, redundancy, complexity, coherence, multilingual embeddings.

## 6. Tech Stack

| Layer | Choice | Reason |
|---|---|---|
| Frontend | HTML + CSS + JavaScript (React optional later) | Enough for recording, task flow, API calls, dashboard |
| Backend | Python + FastAPI | Natural bridge to the audio/ML ecosystem |
| ML | NumPy, Pandas, scikit-learn | Feature engineering + baseline classifiers |
| Audio | librosa + standard audio utilities | Acoustic/spectral feature extraction |
| ASR | Pretrained multilingual ASR (model TBD by languages in dataset) | Speech → transcript |
| NLP | Multilingual transformer embeddings as appropriate | Semantic/linguistic analysis |
| Database | SQLite initially → PostgreSQL later if needed | Assessment/user/history storage |
| Charts | Chart.js (or equivalent) | Clinician dashboard visualization |
| Version control | Git + GitHub | Team collaboration/history |

## 7. Repo Structure

```
project/
├── frontend/            # index.html, styles.css, app.js
├── backend/
│   ├── main.py
│   ├── routes/
│   ├── services/
│   └── schemas/
├── ml/
│   ├── preprocessing/
│   ├── features/
│   ├── asr/
│   ├── nlp/
│   ├── training/
│   └── inference/
├── data/                # README only — no private dataset committed
├── models/
├── tests/
├── docs/
├── CONTEXT.md           # this file
└── README.md
```
`backend/` is now implemented (Phase 0 mock skeleton, see Section 9). `frontend/`, `ml/`, `models/` are still empty placeholders. `data/` holds the extracted (gitignored) ADReSSo dataset locally — never committed.

## 8. Critical Constraints (do not violate)

- **No speaker leakage:** split train/val/test **by participant**, never by recording — a participant's recordings must all land in the same split, or the model can learn voice identity instead of cognitive status.
- **Don't promise dementia stages** unless the dataset actually has reliable stage labels — if it's only dementia-vs-control, the model can only learn that distinction.
- **Don't blindly translate transcripts to English** and assume linguistic/semantic features are preserved — validate NLP feature definitions per language actually present.
- **Don't build/advertise a facial-expression dementia classifier** — the current dataset is voice-only; webcam is at most an optional behavioral/interface module until labeled video data exists.
- **Don't present mock/synthetic/public data as evidence for the real model** — it's only valid for validating the software pipeline.
- **Report more than accuracy:** sensitivity/recall, specificity, precision, F1, ROC-AUC, confusion matrix, class distribution, cross-validation results — and break these down by language/task/demographics where sample size allows.
- **Privacy:** avoid storing raw audio/video longer than necessary; consider access control and anonymization from the start.

## 9. Plan of Action

### Phase 0 — Before dataset arrives (2026-09-12, today)
- [x] Read source PDF, assess viability, write this context doc.
- [x] Scaffold repo folder structure (empty placeholders).
- [x] Build frontend assessment flow with mock tasks + browser mic recording. — React app under `frontend/`, `useRecorder` hook wraps MediaRecorder.
- [x] Build backend file-upload endpoint (FastAPI skeleton). — combined with mock inference into one endpoint, see below.
- [x] Build a mock ML inference endpoint returning structured JSON (see Section 10 for shape). — `POST /api/assessments` in `backend/routes/assessments.py`; mock logic in `backend/services/mock_inference.py`. Full setup/run/test instructions in `backend/README.md`.
- [x] Build a mock clinician dashboard + longitudinal-history UI off that mock JSON. — `frontend/src/pages/clinical/*`, currently against `mockApi.js`.
- [ ] Set up GitHub branching convention and module ownership (see Section 11).

### Phase 1 — Dataset arrives (2026-09-13 onward)
- [x] **Dataset audit** — confirm from ma'am/the data itself (see Section 12 and `docs/dataset_audit.md` for the full breakdown):
  - Exact label scheme (dementia vs control only, or staged?). — **binary only**; the `-i`/`_i`/`_severe` filename suffixes are confirmed (interviewer-removed / one severe case), not a usable severity scheme (N=1).
  - Which languages are present. — **still unknown, no metadata shipped with this download.**
  - One recording per participant, or multiple? — **confirmed: one recording per participant** (164 unique IDs, no duplicates).
  - Exact task/prompt used per recording. — **still unknown, no metadata shipped.**
  - Class distribution and any usable demographic metadata. — **class distribution confirmed** (85 Dementia / 79 Normal); **no demographic metadata included.**
  - Allowed storage/use constraints on the recordings. — **still unknown, treat as sensitive by default until confirmed** (see Section 8).
- [x] Build participant-level train/val/test split (Section 8). — `ml/preprocessing/split.py`, `GroupShuffleSplit`/`GroupKFold` keyed on participant ID.
- [x] Build real audio-feature extraction pipeline (librosa-based). — `ml/features/acoustic.py` (pauses, pitch, energy, MFCCs); handles both dataset `.wav` files and browser-uploaded WebM/Opus via a PyAV fallback.
- [x] Build/select an ASR pipeline for the languages actually present. — `ml/asr/transcribe.py` (faster-whisper, CPU, English `small.en` checkpoint) + `ml/asr/build_transcript_cache.py` batch/caching script; validated against real recordings (transcripts read as coherent Cookie Theft descriptions). Standalone — not yet fused into `train_baseline.py`.
- [x] Build NLP/semantic feature extraction, validated per language. — `ml/nlp/linguistic.py`: lexical diversity (TTR), pronoun/filler-word ratios, bigram repetition, Cookie Theft concept-coverage, and a TF-IDF-based sentence-coherence proxy (no embedding model, avoids a heavy new dependency — see module docstring for the tradeoff). English-only, task-specific to Cookie Theft.
- [x] Train first interpretable baseline (Logistic Regression / Random Forest), evaluate with full metric set (Section 8), replacing the mock inference endpoint. — `ml/training/train_baseline.py`, artifacts in `models/baseline_v1/` (gitignored); wired into the backend's real endpoints via `ml/inference/predict.py` (Section 10). Acoustics-only — ASR (`ml/asr/`) and NLP (`ml/nlp/`) layers now exist standalone (see above) but are not yet fused into this training script; that fusion + retrain is the next concrete action (Section 1).

### Phase 2 — Iterate
- [ ] Compare classical baselines (add Gradient Boosting/XGBoost); tune only after a clean baseline exists.
- [ ] Evaluate performance by language, task type, and available demographics.
- [ ] If dataset size supports it, compare against pretrained speech representations/transformer approaches.
- [ ] Build the explanation layer (feature-contribution display) for the dashboard.
- [ ] Layer in SIH-26003 memory-assistance features as modular extensions — **lower priority than the core screening pipeline**: cognitive games, adaptive difficulty, reminders, caregiver dashboard, offline support.

## 10. API/Backend Concept

Frontend sends selected task/language + recorded audio → backend validates/stores/processes → audio pipeline extracts features/transcript → ML service predicts + explains → backend returns structured JSON → frontend renders + stores the record.

```json
{
  "assessment_id": "...",
  "language": "...",
  "risk_score": 0.72,
  "speech_features": {},
  "linguistic_features": {},
  "model_version": "...",
  "needs_clinician_review": true
}
```

**Data model sketch:** Participant, Assessment, Task response, Extracted features, Prediction, History, Consent/privacy metadata — see PDF Section 15 for full field-level detail if needed.

## 11. Team Module Breakdown

| Workstream | Responsibilities |
|---|---|
| Data + ML | Dataset audit, preprocessing, feature extraction, splitting, baselines, evaluation |
| Speech + NLP | ASR, transcript cleaning, linguistic/semantic features, multilingual experiments |
| Backend | FastAPI, upload/inference endpoints, database integration |
| Frontend | Assessment UI, recorder, task flow, dashboard |
| SIH/Product | Games, reminders, adaptive logic, caregiver workflow |
| Testing + Docs | Integration testing, edge cases, reproducibility, report/demo |

## 12. Open Questions / Immediate Checklist

- [x] Get dataset requirements/labels from ma'am — **confirmed 2026-09-20**: `-i`/`_i` (23 files) means the interviewer's voice was edited out of the recording; `_severe` (`data/adresso2021/Dementia/adrso078_severe.wav`) means a confirmed severe-dementia case. Both are now tracked as manifest columns (`instructor_removed`, `severity` — see `ml/preprocessing/manifest.py`) rather than used to include/exclude files. The single severe example is not usable as a severity-model label (N=1) — see Section 8.
- [x] Confirm exactly which languages are present. — **English-only, confirmed by the project supervisor (2026-09-20)**.
- [x] Confirm one vs. multiple recordings per participant. — **One recording per participant**, confirmed by filename audit (164 unique `adrsoNNN` IDs, no duplicates across `Dementia`/`Normal`).
- [x] Confirm the exact task/prompt used for every recording. — **Cookie Theft picture description, confirmed by the project supervisor (2026-09-20)**.
- [x] Determine class distribution — **85 Dementia / 79 Normal**, confirmed. — [ ] available demographic metadata — **none shipped with this download**, still need to ask.
- [ ] Determine allowed use/storage of recordings (data-use-agreement terms, retention limits).
- [ ] Confirm branch ownership per module (Section 11).
- [ ] Check whether the source Drive folder has more than this one zip part (the filename `adresso2021-...-1-001.zip` is Google Drive's split-export naming — there may be a metadata/transcript zip that didn't get downloaded).

## 13. Source

This document is a condensed, working version of `Project_Master_Context_Team.pdf` in the repo root — go back to the PDF for full section-by-section detail (e.g. full data model field list, complete frontend screen-by-screen spec) if this summary is ever insufficient. A synchronized copy of this file is also kept as `CONTEXT.docx` for sharing outside the repo.
