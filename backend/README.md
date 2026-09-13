# Backend

FastAPI backend for the assessment pipeline. Phase 0 status: skeleton only —
`/health` and `POST /api/assessments` both return fixed mock data
(`model_version: "mock-0.0"`). No real audio processing, ML inference, or
persistence yet — see `docs/ACTION_PLAN.md` Phase 1.

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

## Test

```bash
pytest tests/backend -v
```

## Manual smoke test

```bash
curl http://127.0.0.1:8000/health

curl -F "audio=@some_file.wav;type=audio/wav" \
     -F "language=en" \
     -F "task_id=cookie-theft" \
     http://127.0.0.1:8000/api/assessments
```

Expect a `200` with a JSON body containing `assessment_id`, `language`,
`risk_score`, `speech_features`, `linguistic_features`, `model_version`
(`"mock-0.0"`), and `needs_clinician_review`.
