# Next Steps — Roadmap to the End Goal

> Execution-ordered companion to `CONTEXT.md` (the full status/context doc — read that first if you need the "why", this is the "what next, in order"). Regenerate/update this whenever a major milestone lands.

## 1. End goal

A web-based AI-assisted cognitive screening platform: a participant performs a standardized multilingual speech task (picture description), the system extracts acoustic + linguistic + semantic features from the recording, fuses them via an ML classifier into a screening estimate, and presents an interpretable, longitudinally-tracked result to a clinician/caregiver — **for screening/monitoring support, not standalone diagnosis**.

MVP definition (CONTEXT.md §4): language selection → standardized task shown → browser recording → upload → preprocessing + feature extraction → ASR transcript where supported → fused-feature model → dashboard with results + key indicators → stored for longitudinal comparison.

## 2. Where things stand today

- **Backend (Phase 1, done):** FastAPI + SQLite persistence (`backend/db.py`), real 3-step contract (`POST /assessments` → `POST /assessments/{id}/audio` → `GET /assessments/{id}/results`) backed by actual model inference. The original mock endpoint (`POST /api/assessments`, `model_version: mock-0.0`) is kept only as a legacy comparison harness.
- **ML (Phase 1 first pass, done):** acoustics-only baseline (Logistic Regression + Random Forest) trained on ADReSSo 2021 with a participant-level split and full metric set (`ml/`, artifacts in `models/baseline_v1/`, gitignored). No ASR or NLP/semantic layer yet — acoustic features only.
- **Frontend:** full assessment flow (login → language → instructions → picture task → recording → processing → results) wired to the real backend, validated end-to-end live in-browser (real `baseline-logreg-v1` inference, not mock).
- **Auth:** `backend/routes/demo_auth.py` — demo-only stubs (any non-empty code logs in as a hardcoded participant) that exist purely to unblock frontend/ML integration testing. **Not real authentication.**
- **Stimulus image:** the picture-description task uses an original custom illustration (`frontend/src/components/assessment/PictureStimulus.jsx`), reworked this session to match the *structural* complexity (multiple characters, two simultaneous mishaps, foreground/background depth) of the Cookie Theft picture every ADReSSo training recording actually describes — without reproducing that copyrighted image. See §5 for the caveat this leaves open.
- **Dataset:** audited (`docs/dataset_audit.md`) — 164 recordings (85 Dementia / 79 Normal), one per participant, 44.1kHz throughout, filename-suffix confounds (`-i`/`_i`, `_severe`) checked and found not statistically significant on pause-related features. Language and exact task/prompt are still **unconfirmed** by the project supervisor.

## 3. Blocking questions for the supervisor (CONTEXT.md §12)

These gate real ML progress — no amount of engineering substitutes for them:

- [ ] Exact language(s) present in the ADReSSo download (assumed English, not confirmed).
- [ ] Exact task/prompt used for every recording (historically Cookie Theft picture description for ADReSSo, but not confirmed for *this* download).
- [ ] Any demographic metadata available (none shipped so far).
- [ ] Allowed storage/use/consent terms for the recordings (treat as sensitive by default until confirmed).

**ASR and NLP/semantic feature work cannot meaningfully start until language is confirmed** — don't build a pipeline for a guessed language.

## 4. Ordered next steps

1. **Get the four supervisor answers above.** Blocking, no-code item — do this first.
2. **Build the ASR layer** for the confirmed language(s) (`ml/asr/`, currently unimplemented per the repo structure in CONTEXT.md §7).
3. **Build the NLP/semantic feature layer**, validated per language rather than assumed from English NLP norms (`ml/nlp/`, currently unimplemented). Don't blindly translate transcripts and assume linguistic features are preserved (CONTEXT.md §8).
4. **Retrain**, fusing acoustic + ASR + NLP features. Re-run the full metric set — sensitivity/recall, specificity, precision, F1, ROC-AUC, confusion matrix, class distribution — broken down by language/task/demographics where sample size allows (CONTEXT.md §8).
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
