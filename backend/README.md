# Backend

FastAPI backend for the assessment pipeline. SQLite-backed persistence
(`backend/db.py`), real ML inference (`ml/inference/predict.py`, currently
serving `models/baseline_v2`, the acoustic+ASR+NLP fused model), and a
3-step assessment contract:

1. `POST /assessments` — create a pending assessment, returns its `id`.
2. `POST /assessments/{id}/audio` — upload the recorded audio; runs
   inference and persists the result.
3. `GET /assessments/{id}/results` — fetch the persisted result.

Real authentication (`backend/routes/auth.py`, `backend/services/auth.py`):
participants log in with a per-patient `login_code` (no password), clinicians
with email/password (PBKDF2-hashed). Both issue an opaque bearer session
token (12h TTL) -- pass it as `Authorization: Bearer <token>` on every other
request. `backend/seed.py` seeds a demo clinician
(`dr.sharma@memora.org` / `demo1234`) and the mock patient roster
(`CA-1001`/`PT-1001`, ...) on every startup, idempotently.

## Setup

From the repo root:

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r backend/requirements-dev.txt

# Confirms .venv is actually active and the ML stack resolved -- a plain
# `python`/`uvicorn` invocation without activating .venv first will import
# the system interpreter instead and fail with ModuleNotFoundError at
# request time (on the first /assessments/{id}/audio call) instead of here.
python -c "import faster_whisper, librosa, parselmouth, shap"
```

## Run

```bash
uvicorn backend.main:app --reload
```

CORS defaults to local dev origins (`http://localhost:5173`,
`http://127.0.0.1:5173`, Vite's default). Set `BACKEND_CORS_ORIGINS`
(comma-separated) to the real deployed frontend origin(s) before any
non-local deployment.

## Deploy (Render)

Needs a long-running process (not a serverless function), so it's deployed as
a Render Web Service from the root-level `Dockerfile`.

1. Push this repo to GitHub (Render builds from a connected repo).
2. In the Render dashboard: **New +** -> **Blueprint**, point it at this repo.
   Render reads `render.yaml` (repo root) and provisions the web service on
   the **free** plan.
3. Set the `BACKEND_CORS_ORIGINS` env var (marked `sync: false` in
   `render.yaml`, so Render prompts for it) to the deployed frontend's origin,
   e.g. `https://your-app.vercel.app`.
4. Health check path is `/health` (`backend/routes/assessments.py`) — Render
   uses this to know when the service is ready.

**Free-tier tradeoff**: `render.yaml` deliberately has no persistent disk (a
paid-plan feature). `DB_PATH`/`HF_HOME` fall back to the code defaults, which
live in the container's ephemeral filesystem — so the SQLite database resets
and the ~484MB `small.en` faster-whisper checkpoint re-downloads from Hugging
Face Hub every time the service redeploys or wakes from Render's free-tier
idle sleep (services sleep after 15 min with no traffic; the next request
wakes it, taking roughly 30-60s plus the model download before it's fully
warm). Fine for demoing the live flow in one sitting; assessment history
won't survive between sessions. If that becomes a problem, switch `plan` in
`render.yaml` to a paid tier and add a `disk` block mounted at `/data`, then
point `DB_PATH`/`HF_HOME` at it.

## Test

```bash
pytest tests/backend -v
```

## Manual smoke test

```bash
curl http://127.0.0.1:8000/health

# Log in as the seeded participant PT-1001 (patient CA-1001) and capture the token.
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/auth/participant \
     -H "Content-Type: application/json" \
     -d '{"code": "PT-1001"}' | python -c "import sys,json;print(json.load(sys.stdin)['token'])")

curl -X POST http://127.0.0.1:8000/assessments \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer $TOKEN" \
     -d '{"patientId": "CA-1001", "language": "en", "taskId": "cookie-theft"}'
# -> {"id": "<assessment_id>", "status": "pending_recording"}

curl -X POST "http://127.0.0.1:8000/assessments/<assessment_id>/audio" \
     -H "Authorization: Bearer $TOKEN" \
     -F "audio=@some_file.wav;type=audio/wav"
# -> {"id": "<assessment_id>", "status": "complete"}

curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/assessments/<assessment_id>/results
```

Clinician endpoints (`GET /assessments`, the full `GET /patients` shape) need
a clinician token instead:

```bash
CLIN_TOKEN=$(curl -s -X POST http://127.0.0.1:8000/auth/clinical \
     -H "Content-Type: application/json" \
     -d '{"email": "dr.sharma@memora.org", "password": "demo1234"}' \
     | python -c "import sys,json;print(json.load(sys.stdin)['token'])")

curl -H "Authorization: Bearer $CLIN_TOKEN" "http://127.0.0.1:8000/assessments?needsReview=true"
```

Expect the final response to contain `assessment_id`, `language`,
`risk_score`, `speech_features`, `linguistic_features`, `model_version`,
and `needs_clinician_review`.
