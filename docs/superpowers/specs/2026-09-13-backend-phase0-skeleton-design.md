# Design: Backend Phase 0 Skeleton (Upload + Mock Inference)

> Status: approved by user in chat 2026-09-13. First sub-project of `docs/ACTION_PLAN.md` Phase 0 (tickets 0.2 + 0.3).

## Context

Phase 0 of the project plan needs a working backend skeleton the frontend can call before any real ML pipeline exists, so frontend and backend work can proceed in parallel and de-risk the schedule ahead of the dataset arriving. `CONTEXT.md` §10 already fixes the response JSON contract; this design fixes everything else needed to stand the service up.

The repo already scaffolds `backend/routes/`, `backend/services/`, `backend/schemas/` as empty placeholder folders (see repo structure in `CONTEXT.md` §7) — this design follows that intended structure rather than a flat single-file app.

## Decisions

- **One combined endpoint, not two.** The Phase 0 checklist lists "upload endpoint" (0.2) and "mock inference endpoint" (0.3) as separate tickets, but there's no async/queueing need yet, so they're satisfied as two internal steps of one HTTP call rather than two round-trips: `POST /api/assessments` accepts the audio + metadata and returns the full result directly. This is also the shape the real pipeline will eventually have (upload triggers processing, single response comes back) — Phase 1 can insert real processing into the same handler without changing the frontend contract.
- **No persistence in Phase 0.** Longitudinal storage is explicitly Phase 1 scope in `docs/ACTION_PLAN.md`. Uploaded audio is read and discarded; nothing is written to a database.
- **Mock values must be unmistakably fake.** `model_version` is set to `"mock-0.0"` so no one downstream (dashboard screenshots, demos) mistakes this for a real result later.
- **venv + `requirements.txt`**, not Poetry — matches the simple stack already described in `CONTEXT.md` §6 and needs no extra tooling for the team to learn.

## API

### `GET /health`
Trivial liveness check for local dev / frontend integration testing. Returns `{"status": "ok"}`.

### `POST /api/assessments`
- **Request:** `multipart/form-data` — `audio` (file), `language` (str), `task_id` (str).
- **Response:** JSON matching `CONTEXT.md` §10:
  ```json
  {
    "assessment_id": "uuid",
    "language": "<echoed from request>",
    "risk_score": 0.42,
    "speech_features": { "...": "fixed mock values" },
    "linguistic_features": { "...": "fixed mock values" },
    "model_version": "mock-0.0",
    "needs_clinician_review": true
  }
  ```
- `assessment_id` is a freshly generated UUID per call (so the frontend dashboard has something unique to key off), everything else is fixed/mock data returned by a `services/mock_inference.py` function — `generate_mock_result(audio_bytes, language, task_id)` — whose signature already matches what the real pipeline will need (audio bytes plus the form fields), so the real implementation can replace the function body later without changing `routes/`.

## File layout

```
backend/
├── main.py                 # creates FastAPI app, mounts router, CORS config
├── requirements.txt        # fastapi, uvicorn, python-multipart
├── routes/
│   └── assessments.py      # GET /health, POST /api/assessments
├── schemas/
│   └── assessment.py       # Pydantic response model (AssessmentResult)
├── services/
│   └── mock_inference.py   # generate_mock_result(audio_bytes, language, task_id) -> AssessmentResult
└── README.md                # updated with venv/run instructions
```

## Out of scope (explicitly deferred)

- Any real audio processing, ASR, feature extraction, or ML inference.
- Database/persistence of assessments.
- Auth, rate limiting, input validation beyond FastAPI's basic type checking.
- Long-term file storage of uploaded audio (it's discarded after the mock response is built).

## Testing / verification

- `uvicorn backend.main:app --reload` starts without error.
- `GET /health` returns `200 {"status": "ok"}`.
- `POST /api/assessments` with a small sample audio file, a `language`, and a `task_id` returns `200` and a JSON body matching the contract above, with a fresh `assessment_id` on each call.
