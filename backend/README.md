# Backend

FastAPI backend for the assessment pipeline. SQLite-backed persistence
(`backend/db.py`), real ML inference (`ml/inference/predict.py`, currently
serving `models/baseline_v2`, the acoustic+ASR+NLP fused model), and a
3-step assessment contract:

1. `POST /assessments` — create a pending assessment, returns its `id`.
2. `POST /assessments/{id}/audio` — upload the recorded audio; runs
   inference and persists the result.
3. `GET /assessments/{id}/results` — fetch the persisted result.

`POST /auth/participant` and `GET /patients` (`backend/routes/demo_auth.py`)
are demo-only stubs that let the frontend's login screen pass without real
authentication — not production auth (see `docs/NEXT_STEPS.md`).

## Setup

From the repo root:

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r backend/requirements-dev.txt
```

## Run

```bash
uvicorn backend.main:app --reload
```

CORS defaults to local dev origins (`http://localhost:5173`,
`http://127.0.0.1:5173`, Vite's default). Set `BACKEND_CORS_ORIGINS`
(comma-separated) to the real deployed frontend origin(s) before any
non-local deployment.

## Test

```bash
pytest tests/backend -v
```

## Manual smoke test

```bash
curl http://127.0.0.1:8000/health

curl -X POST http://127.0.0.1:8000/assessments \
     -H "Content-Type: application/json" \
     -d '{"patientId": "demo-patient", "language": "en", "taskId": "cookie-theft"}'
# -> {"id": "<assessment_id>", "status": "pending_recording"}

curl -X POST "http://127.0.0.1:8000/assessments/<assessment_id>/audio" \
     -F "audio=@some_file.wav;type=audio/wav"
# -> {"id": "<assessment_id>", "status": "complete"}

curl http://127.0.0.1:8000/assessments/<assessment_id>/results
```

Expect the final response to contain `assessment_id`, `language`,
`risk_score`, `speech_features`, `linguistic_features`, `model_version`,
and `needs_clinician_review`.
