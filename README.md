# Memora

AI-assisted, multilingual cognitive screening and memory-assistance platform. Participants complete a short standardized speech task (currently the Cookie Theft picture description); the system extracts acoustic, ASR/transcript, and linguistic/semantic features from the recording and feeds them into a trained ML classifier to produce a screening estimate, which a clinician reviews on a dashboard.

> **Not a diagnostic tool.** This is a screening/monitoring aid and research prototype. It flags cases for clinician review — it does not diagnose dementia.

**Two halves, one platform:** speech-based cognitive screening (below) and camera-based **safety monitoring** (falls, appliances left on, wandering), both reviewed from the same clinician dashboard. See [Safety monitoring](#safety-monitoring).

## Live demo

- **App:** https://memora-health.vercel.app (clinician demo login: `dr.sharma@memora.org` / `demo1234`)
- **API:** https://memora-backend-a8yh.onrender.com ([docs](https://memora-backend-a8yh.onrender.com/docs))

The API runs on Render's free tier and sleeps when idle: open it about a minute before a demo.
Sessions live in memory only (privacy by design), so a full page refresh signs you out; navigate with the sidebar.

## How it works

```
Patient → Web assessment UI → Task prompt → Mic recording → Audio upload
        → Acoustic features + ASR transcript → NLP/semantic features
        → Feature fusion → ML model → Risk score + explanation
        → Clinician dashboard (review, patient history, trends)
```

- **Acoustic/paralinguistic** — pauses, speech rate, pitch/prosody, energy, MFCCs (`ml/features/`)
- **ASR/transcript** — speech-to-text via faster-whisper (`ml/asr/`)
- **NLP/semantic** — lexical diversity, filler/pronoun ratios, repetition, Cookie Theft concept coverage (`ml/nlp/`)
- **Model** — Logistic Regression / Random Forest baselines trained on the fused feature vector (`ml/training/`), served in-process by the backend (`ml/inference/predict.py`)

See [`CONTEXT.md`](CONTEXT.md) for the full product/research spec, dataset audit, and project history.

## Repo structure

```
backend/     FastAPI app — auth, assessments API, SQLite persistence
frontend/    React 19 + Vite — patient screening flow + clinician dashboard
ml/          Feature extraction (acoustic/ASR/NLP), training, inference
monitoring/  Safety monitoring: rules engine, vision observer, service, storage
models/      Committed trained model artifacts (baseline_v1, baseline_v2)
data/        Dataset docs only — raw audio is never committed (gitignored)
tests/       Backend + ML test suites (pytest)
docs/        Architecture notes, dataset audit, action plan
```

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | React 19, Vite, React Router, Tailwind CSS, Recharts |
| Backend | Python, FastAPI, SQLite |
| ML | scikit-learn, librosa, faster-whisper |
| Deployment | Vercel (frontend), Render (backend, Docker) |

## Getting started

### Backend

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows; use source .venv/bin/activate on macOS/Linux
pip install -r backend/requirements-dev.txt

uvicorn backend.main:app --reload
```

Runs on `http://127.0.0.1:8000`. Seeds a demo clinician (`dr.sharma@memora.org` / `demo1234`) and a mock patient roster on startup. Full setup, deploy, and API smoke-test instructions: [`backend/README.md`](backend/README.md).

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Runs on `http://localhost:5173` against a built-in mock API by default — no backend required. To talk to a real backend, copy `.env.example` to `.env.local` and set `VITE_USE_MOCK_API=false`. Details: [`frontend/README.md`](frontend/README.md).

### Tests

```bash
pytest                 # backend + ML (pytest.ini at repo root)
cd frontend && npm run test   # frontend (Vitest)
```

## Models

Two trained baselines are committed under `models/`:

- **`baseline_v1`** — acoustics-only (fast, no ASR latency)
- **`baseline_v2`** — acoustic + ASR + NLP fused (live default; better cross-validated ROC-AUC, higher per-request latency)

Trained on the ADReSSo 2021 dataset (English, Cookie Theft task, N=164, binary dementia/control labels). See [`models/README.md`](models/README.md) and [`docs/dataset_audit.md`](docs/dataset_audit.md) for details, and `CONTEXT.md` Section 8 for the constraints (no speaker leakage, no overclaiming clinical validity) this project is held to.

## Safety monitoring

A room camera feeds a vision model and a temporal rules engine (`monitoring/`) that raises caregiver alerts for falls, a stove or tap left on, prolonged absence, night-time wandering and repeated unfinished tasks. Alerts appear on the clinician dashboard under **Safety monitor** (`/clinical/safety`) and are stored in the same SQLite database as assessments. It monitors hazards and behaviour only; it does not diagnose and does not classify faces or expressions.

- **No camera or GPU needed to try it:** open Safety monitor, pick a patient and run one of five incident scenarios (stove left on then a fall, bathroom fall, night-time wandering, tap left running, repeated unfinished task). Each replays the vision model's structured observations through the real rules engine; alerts then show on the clinical overview and the patient's profile.
- **Live camera is optional:** `pip install mediapipe` and run `scripts/download_pose_model.sh` for pose-based fall detection on an ordinary CPU, then press *Start camera* on the Safety monitor page. The vision model (`pip install -r monitoring/requirements.txt`, needs a GPU) is only called when the pose looks odd, or every 10 minutes to re-read appliances. Without these packages, `POST /monitoring/frame` answers `{"status":"unavailable"}` and everything else keeps working.
- **Family alerts:** add contacts on a patient's profile; serious live alerts are sent by SMS or WhatsApp through Twilio. Without Twilio credentials on the server nothing is sent and attempts are logged as `dry_run`. Simulated alerts never message anyone.
- Full details, endpoints and configuration: [`monitoring/README.md`](monitoring/README.md).

One-command checks and a launcher: `scripts/check_all.sh`, `scripts/run_all.sh`.

## Contributors

- **Speech screening platform** (frontend, backend, ML): Radhesh Nair, Leena Sathvika Pallampati. Full commit history is preserved.
- **Safety monitoring (CARE-VLM)**: the senior's internship project, integrated into `monitoring/`; original scripts are in `monitoring/archive/`.
- **Integration**: Sheersh.

## Deployment

- **Backend** — Render Web Service built from the root `Dockerfile`, configured via `render.yaml`. Free-tier RAM constraints mean the Whisper ASR model is pinned to `base.en`; see [`backend/README.md`](backend/README.md#deploy-render) for the full tradeoff writeup (ephemeral disk, cold starts, OOM history).
- **Frontend** — Vercel, built from `frontend/`, with SPA rewrites in `frontend/vercel.json`.

## Status

Phase 1 (dataset-backed ML pipeline + real backend contract) is complete and deployed end to end. See `CONTEXT.md` Section 1 for the current status snapshot and Section 9 for the phased plan, and [`docs/NEXT_STEPS.md`](docs/NEXT_STEPS.md) / [`docs/ACTION_PLAN.md`](docs/ACTION_PLAN.md) for what's next.
