# Dementia Screening Platform — Team Action Plan & Learning Roadmap

> Companion to `CONTEXT.md` (root of repo). That file is the canonical status/spec doc — this one turns it into assignable work and a personal/team learning path. If the two ever disagree, `CONTEXT.md` wins; update this file to match.

---

## 1. What This Project Actually Is

In plain language: you're building a website where someone looks at a picture and describes it out loud (a "picture description task" — a standard tool in cognitive/speech research). The site records their voice. Behind the scenes, software:

1. Cleans up the audio.
2. Measures *how* they spoke — pauses, speech rate, pitch, hesitation (this is the **acoustic** layer).
3. Transcribes *what* they said using speech recognition, or ASR (the **ASR/transcript** layer).
4. Analyzes the transcript for meaning — did they mention the right objects, was their vocabulary rich, was it coherent (the **NLP/semantic** layer).
5. Feeds all three layers into a trained classifier that estimates whether the speech pattern looks more like the "dementia" group or the "control" group in your training data.
6. Shows the result on a dashboard, tracked over time, as a **screening flag for a clinician to review — not a diagnosis.**

This is a real, established research area (see: DementiaBank/Pitt Corpus, the ADReSS/ADReSSo challenges) — you are not inventing a new technique, you are engineering a solid, known pipeline around a dataset you're about to receive. That's good news: the hard research question ("does this work at all?") is already answered in the literature; your job is data engineering, careful ML practice, and product execution.

**The one sentence to keep repeating to your team:** the model tells you *this speech pattern resembles the impaired group statistically* — it never tells you *this person has dementia*.

---

## 2. What "Labelled Audio Files" Means for You

You said the dataset will be labelled audio recordings (dementia patients + controls). Concretely, this means each audio file will come with at least a class label (e.g., `dementia` / `control`, possibly staged severity). Before writing a single line of ML code against it, get answers to these — they change your entire pipeline design:

| Question | Why it matters |
|---|---|
| Is the label per-recording or per-participant? | If a participant has multiple recordings, they must **all** stay in the same train/val/test split (see Section 6 — speaker leakage). |
| Binary (dementia vs. control) or staged severity? | A binary-only dataset can only train a binary-only model. Don't promise stage prediction you can't back. |
| What language(s)? | Determines which ASR/NLP models you can actually use. Multilingual support is scoped to "whatever's in the data," not universal coverage. |
| What task produced each recording? | Picture description, free speech, reading? Feature definitions (e.g., "expected concept coverage") depend on knowing the exact prompt. |
| Class balance? | Dementia-vs-control audio datasets are frequently imbalanced — this drives your choice of metrics and resampling strategy. |
| Any demographic metadata (age, education, sex)? | Needed to check whether your model is learning cognitive signal vs. confounding demographics. |
| Storage/consent constraints? | This is clinical-adjacent data about real patients — treat it as sensitive by default until told otherwise. |

This audit is literally the first ML task in the plan below — do it before any feature engineering.

---

## 3. Team Workstreams

Six tracks, matching the repo layout (`frontend/`, `backend/`, `ml/`, etc.). Assign one or two people per track; Data+ML and Speech+NLP are the technically heaviest and benefit from people who want to build ML skills.

### Track A — Data & Classical ML
**Owns:** `ml/preprocessing/`, `ml/training/`, dataset splits, evaluation.
**Objective:** turn raw labelled audio into a clean, leakage-free, well-understood dataset, and train/evaluate classical baseline classifiers.

### Track B — Speech & NLP
**Owns:** `ml/asr/`, `ml/features/`, `ml/nlp/`.
**Objective:** extract acoustic features (librosa) and transcript-based linguistic/semantic features; get ASR working for whatever languages are in the dataset.

### Track C — Backend
**Owns:** `backend/`.
**Objective:** FastAPI service for audio upload, orchestrating the ML pipeline, and returning structured results; persistence for longitudinal history.

### Track D — Frontend
**Owns:** `frontend/`.
**Objective:** the assessment UI — task display, mic recording, multilingual selection, and the clinician-facing results dashboard.

### Track E — Product/SIH Extensions
**Owns:** future modules (games, reminders, caregiver dashboard).
**Objective:** lower priority — only start once the MVP screening pipeline works end-to-end.

### Track F — Testing & Docs
**Owns:** `tests/`, `docs/`.
**Objective:** integration tests across the pipeline, reproducibility (can someone else re-run your training and get the same numbers?), and the final report/demo materials.

---

## 4. Phased Action Plan

This mirrors `CONTEXT.md` Section 9 but broken into concrete, assignable tickets.

### Phase 0 — Before/without the real dataset (can start immediately)
| # | Task | Track | Notes |
|---|---|---|---|
| 0.1 | Build frontend task flow + browser mic recording against mock tasks | D | No real data needed |
| 0.2 | Build FastAPI upload endpoint skeleton | C | Accepts audio, returns a stub response |
| 0.3 | Build a mock inference endpoint returning the JSON shape in `CONTEXT.md` §10 | C | Unblocks frontend dashboard work |
| 0.4 | Build the dashboard UI off the mock JSON | D | |
| 0.5 | Set up branch/module ownership, PR review norms | F | |
| 0.6 | Everyone on Track A/B: get comfortable with `librosa`, `pandas`, `scikit-learn` on **public** audio datasets (never claim these as evidence for the real model) | A, B | See Section 5 skills list |

### Phase 1 — Once the labelled dataset is in hand
| # | Task | Track | Notes |
|---|---|---|---|
| 1.1 | **Dataset audit** — answer every question in Section 2 above | A | Blocks everything else in this phase |
| 1.2 | Build participant-level train/val/test split | A | Hard constraint — see Section 6 |
| 1.3 | Real acoustic feature extraction pipeline | B | Duration, pause stats, pitch/prosody, MFCCs, energy |
| 1.4 | Select/wire up ASR for the languages actually present | B | Model choice depends on 1.1 |
| 1.5 | Transcript-based linguistic/semantic features | B | Repetitions, fillers, lexical diversity, coherence, concept coverage vs. expected task content |
| 1.6 | Train first baseline classifier (Logistic Regression or Random Forest) | A | Full metric set — see Section 6, not just accuracy |
| 1.7 | Wire the real pipeline into the backend, replacing the mock endpoint | C | |
| 1.8 | Integration test: audio in → JSON result out | F | |

### Phase 2 — Iterate
| # | Task | Track |
|---|---|---|
| 2.1 | Try Gradient Boosting/XGBoost against the clean baseline | A |
| 2.2 | Break down performance by language/task/demographics | A, F |
| 2.3 | If sample size allows, try pretrained speech embeddings (e.g. wav2vec2-style) | B |
| 2.4 | Build feature-contribution explanation view in the dashboard | D |
| 2.5 | Start SIH-26003 extensions (games, reminders, caregiver view) | E |

---

## 5. ML Skills to Learn, by Track

You don't need to become a research scientist. You need working fluency in a fairly narrow, well-defined slice of ML. Ordered roughly by priority/sequence.

### Foundation (everyone touching ML code)
- Python fundamentals + NumPy/Pandas for data wrangling.
- Core ML concepts: train/val/test splits, overfitting, cross-validation, what a confusion matrix is.
- **Why accuracy alone lies to you**: precision, recall/sensitivity, specificity, F1, ROC-AUC — and why these matter more on imbalanced medical-style datasets.
- Git/GitHub workflow well enough to not step on teammates (branches, PRs, resolving conflicts).

### Track A — Data & Classical ML
- `scikit-learn` end to end: `train_test_split` (and why you'll actually implement a custom **grouped** split by participant instead), pipelines, `StandardScaler`, `LogisticRegression`, `RandomForestClassifier`, `GradientBoostingClassifier`/XGBoost.
- Cross-validation done correctly with grouped data (`GroupKFold`, not plain `KFold`).
- Class imbalance handling: class weights, stratified sampling, resampling — and when each is appropriate.
- Feature scaling/normalization and why tree-based models don't need it but linear models do.
- Basic statistics: what a p-value/confidence interval tells you about whether a result is real or noise, given a likely small sample size.
- Model interpretability basics: feature importance, SHAP values — you'll need to explain *why* the model flagged someone, not just that it did.

### Track B — Speech & NLP
- Digital audio basics: sample rate, waveforms, spectrograms — enough to understand what `librosa` is computing.
- `librosa`: loading audio, silence/pause detection, pitch (F0) extraction, MFCCs, energy/RMS, speech rate estimation.
- Automatic Speech Recognition (ASR) at a practical level: using a pretrained multilingual ASR model (e.g., Whisper-family or similar) via its Python API — you're consuming these, not training your own from scratch.
- NLP fundamentals: tokenization, lexical diversity metrics (e.g., type-token ratio), embeddings, semantic similarity (cosine similarity between sentence embeddings).
- Multilingual NLP awareness: why you can't just translate everything to English and assume linguistic features survive (idioms, filler words, and grammar differ — see `CONTEXT.md` §8).
- Enough transformer/embedding-model literacy to load and use a pretrained multilingual sentence embedding model (you are a consumer of Hugging Face models here, not a model trainer).

### Track C — Backend
- FastAPI: routes, request/response schemas (Pydantic), file upload handling.
- Structuring a service that calls into an ML pipeline synchronously/asynchronously and returns structured JSON.
- Basic database modeling (SQLite → PostgreSQL later) for participants/assessments/history.
- Not deep ML skill, but you must understand the JSON contract in `CONTEXT.md` §10 well enough to keep it stable as the ML side evolves.

### Track D — Frontend
- Browser MediaRecorder API for mic capture.
- Basic charting (Chart.js or similar) to visualize model output/history.
- No ML skill required, but understanding what the numbers you're displaying actually mean (risk score, confidence, feature contributions) will make the dashboard far better designed.

### Track F — Testing & Docs
- Reproducibility practices: fixed random seeds, documenting exact preprocessing steps, environment pinning (`requirements.txt`).
- Enough ML literacy to sanity-check Track A/B's reported metrics (e.g., "is 98% accuracy on a 200-sample imbalanced dataset actually believable, or a leakage red flag?").

### Suggested learning order for someone new to ML on this project
1. Python + Pandas/NumPy basics (if not already comfortable).
2. Core ML concepts + `scikit-learn` on any simple tabular dataset (not audio yet) — get one classifier trained end to end with proper metrics.
3. Audio basics + `librosa` on a public dataset (e.g., any freely available speech corpus) purely to learn the tooling — remember: never present results from this as evidence about the real model.
4. Grouped/participant-level splitting and cross-validation — this is the single most project-specific, easy-to-get-wrong skill. Practice it deliberately.
5. ASR + NLP feature extraction once ASR/language decisions are made in the dataset audit.
6. Model interpretability (feature importance/SHAP) once a baseline model exists.

---

## 6. Guardrails to Repeat Often (from `CONTEXT.md` §8)

- **No speaker leakage** — split by participant, never by recording.
- **Don't promise severity staging** unless the labels actually support it.
- **Don't assume translated transcripts preserve linguistic signal** — validate features per language present.
- **Voice-only dataset** — no facial-expression classifier, no webcam-based diagnosis claims.
- **Never present mock/public data as evidence for the real model** — mock data validates the *software pipeline* only.
- **Report the full metric set**, broken down by language/task/demographics where sample size allows — not just accuracy.
- **Treat the data as sensitive by default**: minimize raw audio retention, control access, anonymize where possible.

---

## 7. Immediate Next Steps

1. Confirm the dataset audit answers (Section 2) as soon as the data arrives — this is Track A's first and highest-priority ticket.
2. Assign owners to Tracks A–F from Section 3.
3. Kick off Phase 0 tasks (Section 4) now — they don't depend on the dataset and de-risk the timeline.
4. Everyone maps themselves onto the Section 5 skills list and starts closing gaps in parallel with Phase 0 engineering work.
