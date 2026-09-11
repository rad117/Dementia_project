# CONTEXT.md — AI-Assisted Multilingual Cognitive Screening & Memory Assistance Platform

> Working context document. Read this first when picking the project back up — it tells you what the project is, where things stand, and what to do next. Full source detail lives in `Project_Master_Context_Team.pdf` (team meeting notes with the project supervisor, referred to as "ma'am").

## 1. Status Snapshot

- **As of:** 2026-09-12
- **Repo:** `rad117/Dementia_project` (GitHub) — created, currently near-empty (placeholder README only, before this commit).
- **Dataset:** Private, classified voice-recording dataset (dementia patients + controls) expected **2026-09-13**. Not yet in hand. Exact labels, languages, and per-participant recording counts are unknown until then.
- **Code:** None written yet. This session scaffolds the repo folder layout only (no implementation).
- **Next concrete action:** once the dataset arrives, run the dataset audit in the checklist (Section 9) before writing any ML code against it.

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
Scaffolded as empty placeholder folders in this session; no implementation code yet.

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
- [ ] Build frontend assessment flow with mock tasks + browser mic recording.
- [ ] Build backend file-upload endpoint (FastAPI skeleton).
- [ ] Build a mock ML inference endpoint returning structured JSON (see Section 10 for shape).
- [ ] Build a mock clinician dashboard + longitudinal-history UI off that mock JSON.
- [ ] Set up GitHub branching convention and module ownership (see Section 11).

### Phase 1 — Dataset arrives (2026-09-13 onward)
- [ ] **Dataset audit** — confirm from ma'am/the data itself:
  - Exact label scheme (dementia vs control only, or staged?).
  - Which languages are present.
  - One recording per participant, or multiple?
  - Exact task/prompt used per recording.
  - Class distribution and any usable demographic metadata.
  - Allowed storage/use constraints on the recordings.
- [ ] Build participant-level train/val/test split (Section 8).
- [ ] Build real audio-feature extraction pipeline (librosa-based).
- [ ] Build/select an ASR pipeline for the languages actually present.
- [ ] Build NLP/semantic feature extraction, validated per language.
- [ ] Train first interpretable baseline (Logistic Regression / SVM / Random Forest), evaluate with full metric set (Section 8), replacing the mock inference endpoint.

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

- [ ] Get dataset requirements/labels from ma'am.
- [ ] Confirm exactly which languages are present.
- [ ] Confirm one vs. multiple recordings per participant.
- [ ] Confirm the exact task/prompt used for every recording.
- [ ] Determine class distribution and available demographic metadata.
- [ ] Determine allowed use/storage of recordings.
- [ ] Confirm branch ownership per module (Section 11).

## 13. Source

This document is a condensed, working version of `Project_Master_Context_Team.pdf` in the repo root — go back to the PDF for full section-by-section detail (e.g. full data model field list, complete frontend screen-by-screen spec) if this summary is ever insufficient. A synchronized copy of this file is also kept as `CONTEXT.docx` for sharing outside the repo.
