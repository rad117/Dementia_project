# Next Steps — Roadmap to the End Goal

> Execution-ordered companion to `CONTEXT.md` (the full status/context doc — read that first if you need the "why", this is the "what next, in order"). Regenerate/update this whenever a major milestone lands.

## 1. End goal

A web-based AI-assisted cognitive screening platform: a participant performs a standardized multilingual speech task (picture description), the system extracts acoustic + linguistic + semantic features from the recording, fuses them via an ML classifier into a screening estimate, and presents an interpretable, longitudinally-tracked result to a clinician/caregiver — **for screening/monitoring support, not standalone diagnosis**.

MVP definition (CONTEXT.md §4): language selection → standardized task shown → browser recording → upload → preprocessing + feature extraction → ASR transcript where supported → fused-feature model → dashboard with results + key indicators → stored for longitudinal comparison.

## 2. Where things stand today

- **Backend (Phase 1, done):** FastAPI + SQLite persistence (`backend/db.py`), real 3-step contract (`POST /assessments` → `POST /assessments/{id}/audio` → `GET /assessments/{id}/results`) backed by actual model inference. The original mock endpoint (`POST /api/assessments`, `model_version: mock-0.0`) is kept only as a legacy comparison harness.
- **ML — two trained baselines now exist:** `models/baseline_v1/` (acoustics-only, Logistic Regression + Random Forest, participant-level split, full metric set) and `models/baseline_v2/` (same two model types, retrained with acoustic + ASR + NLP features fused in). **ASR layer done** (`ml/asr/transcribe.py`, faster-whisper CPU/English `small.en`, plus `ml/asr/build_transcript_cache.py` — all 164 recordings transcribed). **NLP/semantic layer done** (`ml/nlp/linguistic.py` + `ml/nlp/build_linguistic_cache.py`) — lexical diversity, pronoun/filler ratios, repetition, Cookie Theft concept coverage, TF-IDF sentence-coherence proxy. **Fusion measurably helped**: cross-validated ROC-AUC rose from 0.605→0.791 (RF) and 0.668→0.778 (LogReg) — promising on this small (N=164) sample, not a clinical validity claim. `ml/inference/predict.py` is feature-name-aware (only pays ASR latency when the loaded model needs it), but the backend's **live default is still `baseline_v1`** — promoting to `baseline_v2` is an open decision (adds real per-request transcription latency).
- **Frontend:** full assessment flow (login → language → instructions → picture task → recording → processing → results) wired to the real backend, validated end-to-end live in-browser (real `baseline-logreg-v1` inference, not mock).
- **Auth:** `backend/routes/demo_auth.py` — demo-only stubs (any non-empty code logs in as a hardcoded participant) that exist purely to unblock frontend/ML integration testing. **Not real authentication.**
- **Stimulus image:** the picture-description task uses an original custom illustration (`frontend/src/components/assessment/PictureStimulus.jsx`), reworked this session to match the *structural* complexity (multiple characters, two simultaneous mishaps, foreground/background depth) of the Cookie Theft picture every ADReSSo training recording actually describes — without reproducing that copyrighted image. See §5 for the caveat this leaves open.
- **Dataset:** audited (`docs/dataset_audit.md`) — 164 recordings (85 Dementia / 79 Normal), one per participant, 44.1kHz throughout, filename-suffix confounds (`-i`/`_i`, `_severe`) checked and found not statistically significant on pause-related features. **Language (English-only) and task (Cookie Theft picture description) confirmed by the project supervisor (2026-09-20)** — real ASR transcripts read as coherent Cookie Theft descriptions, corroborating the confirmation.

## 3. Blocking questions for the supervisor (CONTEXT.md §12)

Two of the four are now resolved; two remain open:

- [x] Exact language(s) present in the ADReSSo download — **English-only, confirmed 2026-09-20**.
- [x] Exact task/prompt used for every recording — **Cookie Theft picture description, confirmed 2026-09-20**.
- [ ] Any demographic metadata available (none shipped so far).
- [ ] Allowed storage/use/consent terms for the recordings (treat as sensitive by default until confirmed).

The remaining two don't block ASR/NLP engineering work, only real (non-demo) participant data handling later.

## 4. Ordered next steps

1. ~~Get the four supervisor answers above.~~ **Language and task confirmed (2026-09-20).** Demographic metadata and consent terms remain open but don't block engineering work below.
2. ~~**Build the ASR layer**~~ **Done** — `ml/asr/transcribe.py` (faster-whisper, CPU, English `small.en` checkpoint, extensible to other languages via explicit `language`/`model_size` params) + `ml/asr/build_transcript_cache.py` (resumable batch transcription, cache at `data/adresso2021_transcripts_cache.csv`). Standalone — not yet fused into `train_baseline.py`.
3. ~~**Build the NLP/semantic feature layer**~~ **Done** — `ml/nlp/linguistic.py` (English-only, Cookie Theft-specific concept list; TF-IDF coherence proxy chosen over a neural embedding to avoid a heavy new dependency — see module docstring) + `ml/nlp/build_linguistic_cache.py` (reads the ASR transcript cache, writes `data/adresso2021_linguistic_cache.csv`).
4. ~~**Retrain**, fusing acoustic + ASR + NLP features.~~ **Done** — `models/baseline_v2/` (`python -m ml.training.train_baseline --use-asr-nlp-features --model-dir models/baseline_v2 --model-version-tag v2-fused`). `ml/inference/predict.py` now populates `linguistic_features` (was hardcoded `{}`) and uses `language` for real, conditionally on whether the loaded model needs ASR/NLP columns. Full metric set re-run and compared against `baseline_v1` — cross-validated ROC-AUC improved substantially (see §2). **Open decision, not yet made:** whether to point the backend's live default (`predict.py`'s `model_dir` default) at `baseline_v2` — it's a real latency tradeoff (per-request CPU transcription), should be a deliberate call, not a silent swap.
5. **Validate the reworked picture stimulus empirically.** Record a handful of control descriptions against the new illustration and sanity-check the acoustic feature/risk-score distribution isn't skewed relative to the ADReSSo-trained baseline. This is the domain-shift mitigation discussed this session — matching structural complexity narrows the gap but doesn't prove it's closed.
6. **Revisit the `needs_clinician_review` risk-score threshold** — currently a placeholder with no clinical basis (CONTEXT.md §1). Set this from real evaluation results, not intuition.
7. **Replace `backend/routes/demo_auth.py` with real authentication** before handling any real participant data.
8. **Build the explanation layer** (feature-contribution display) and longitudinal history view for the clinician dashboard (CONTEXT.md §9 Phase 2).
9. **Formalize GitHub branching convention and module ownership** (CONTEXT.md §9/§11 — still unchecked since Phase 0).
10. **Privacy/compliance pass**: access control, anonymization, retention limits — before any real (non-demo) participant data is collected (CONTEXT.md §8).
11. **Lower priority**: SIH-26003 memory-assistance extensions (cognitive games, adaptive difficulty, reminders, caregiver dashboard, offline support) — only once the core screening pipeline is solid (CONTEXT.md §9 Phase 2).

## 5. Known limitations to keep surfacing

- The legacy mock endpoint (`POST /api/assessments`, `mock-0.0`) and the demo auth stubs are both temporary scaffolding, not production paths — don't let either get mistaken for the real thing in a demo or a report.
- The picture-description stimulus is an **original illustration**, not the licensed BDAE Cookie Theft image. Using the real image would require a license from Pearson/PRO-ED — it is not obtainable by screenshotting or re-sourcing from another website (copyright doesn't reset based on host site).
- The ML model reports a risk score with **no clinical validation** behind its threshold yet — frame all output as a research/screening prototype, never a diagnosis (CONTEXT.md §3).
