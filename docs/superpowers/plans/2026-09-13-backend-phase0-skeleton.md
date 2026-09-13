# Backend Phase 0 Skeleton Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up a working FastAPI backend skeleton with a health check and a combined upload+mock-inference endpoint, so the frontend has a real API contract to build against before any real ML pipeline exists.

**Architecture:** A `backend/` Python package with `main.py` (app + CORS), `routes/assessments.py` (HTTP layer), `schemas/assessment.py` (Pydantic response model), and `services/mock_inference.py` (mock result generator with the signature the real ML pipeline will later replace). One HTTP call (`POST /api/assessments`) does both "upload" and "inference" — no queueing/async needed yet.

**Tech Stack:** Python, FastAPI, Uvicorn, Pydantic v2, pytest, httpx (for `TestClient`).

**Spec:** `docs/superpowers/specs/2026-09-13-backend-phase0-skeleton-design.md`

## Global Constraints

- venv + `requirements.txt` for dependency management — no Poetry.
- No persistence — assessments are not saved to a database in Phase 0.
- No real audio processing/ASR/ML — all results are fixed mock data.
- `model_version` must always be `"mock-0.0"` so mock results are unmistakable.
- Single combined endpoint `POST /api/assessments` — not separate upload/infer calls.
- CORS is permissive (`allow_origins=["*"]`) for local dev only.
- Uploaded audio bytes are read and discarded — never written to permanent storage.
- All imports use the `backend.` absolute package path (repo root is the working directory for both `uvicorn` and `pytest`).

---

### Task 1: Backend package scaffold + `/health` endpoint

**Files:**
- Create: `backend/__init__.py` (empty)
- Create: `backend/requirements.txt`
- Create: `backend/requirements-dev.txt`
- Create: `backend/routes/__init__.py` (empty)
- Create: `backend/routes/assessments.py`
- Create: `backend/main.py`
- Test: `tests/backend/test_health.py`

**Interfaces:**
- Produces: `backend.main:app` (FastAPI instance) — later tasks and tests import this.
- Produces: `backend.routes.assessments:router` (`APIRouter`) — mounted by `main.py`, extended in Task 4.

- [ ] **Step 1: Write the failing test**

```python
# tests/backend/test_health.py
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Run test to verify it fails**

Run (from repo root): `pytest tests/backend/test_health.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'backend'` (nothing exists yet).

- [ ] **Step 3: Write minimal implementation**

```python
# backend/requirements.txt
fastapi
uvicorn[standard]
python-multipart
```

```python
# backend/requirements-dev.txt
-r requirements.txt
pytest
httpx
```

```python
# backend/routes/assessments.py
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}
```

```python
# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routes.assessments import router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
```

`backend/__init__.py` and `backend/routes/__init__.py` are empty files.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/backend/test_health.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/__init__.py backend/requirements.txt backend/requirements-dev.txt backend/routes/__init__.py backend/routes/assessments.py backend/main.py tests/backend/test_health.py
git commit -m "feat(backend): add FastAPI skeleton with /health endpoint"
```

---

### Task 2: `AssessmentResult` schema

**Files:**
- Create: `backend/schemas/__init__.py` (empty)
- Create: `backend/schemas/assessment.py`
- Test: `tests/backend/test_schemas.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `backend.schemas.assessment:AssessmentResult` (Pydantic `BaseModel`) with fields `assessment_id: str`, `language: str`, `risk_score: float`, `speech_features: dict`, `linguistic_features: dict`, `model_version: str`, `needs_clinician_review: bool` — used by Task 3 and Task 4.

- [ ] **Step 1: Write the failing test**

```python
# tests/backend/test_schemas.py
from backend.schemas.assessment import AssessmentResult


def test_assessment_result_round_trip():
    result = AssessmentResult(
        assessment_id="abc-123",
        language="en",
        risk_score=0.42,
        speech_features={"pause_count": 3},
        linguistic_features={"lexical_diversity": 0.5},
        model_version="mock-0.0",
        needs_clinician_review=True,
    )

    dumped = result.model_dump()

    assert dumped["assessment_id"] == "abc-123"
    assert dumped["model_version"] == "mock-0.0"
    assert dumped["needs_clinician_review"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/backend/test_schemas.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'backend.schemas'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/schemas/assessment.py
from pydantic import BaseModel


class AssessmentResult(BaseModel):
    assessment_id: str
    language: str
    risk_score: float
    speech_features: dict
    linguistic_features: dict
    model_version: str
    needs_clinician_review: bool
```

`backend/schemas/__init__.py` is empty.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/backend/test_schemas.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/schemas/__init__.py backend/schemas/assessment.py tests/backend/test_schemas.py
git commit -m "feat(backend): add AssessmentResult schema"
```

---

### Task 3: Mock inference service

**Files:**
- Create: `backend/services/__init__.py` (empty)
- Create: `backend/services/mock_inference.py`
- Test: `tests/backend/test_mock_inference.py`

**Interfaces:**
- Consumes: `backend.schemas.assessment.AssessmentResult` (Task 2).
- Produces: `backend.services.mock_inference:generate_mock_result(language: str, task_id: str) -> AssessmentResult` — called by Task 4's route handler. This exact signature is what the real ML pipeline will replace later without touching `routes/`.

- [ ] **Step 1: Write the failing test**

```python
# tests/backend/test_mock_inference.py
from backend.services.mock_inference import generate_mock_result


def test_generate_mock_result_shape():
    result = generate_mock_result("en", "cookie-theft")

    assert result.language == "en"
    assert result.model_version == "mock-0.0"
    assert isinstance(result.risk_score, float)
    assert isinstance(result.needs_clinician_review, bool)


def test_generate_mock_result_unique_ids():
    first = generate_mock_result("en", "cookie-theft")
    second = generate_mock_result("en", "cookie-theft")

    assert first.assessment_id != second.assessment_id
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/backend/test_mock_inference.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'backend.services'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/services/mock_inference.py
import uuid

from backend.schemas.assessment import AssessmentResult


def generate_mock_result(language: str, task_id: str) -> AssessmentResult:
    return AssessmentResult(
        assessment_id=str(uuid.uuid4()),
        language=language,
        risk_score=0.42,
        speech_features={
            "duration_seconds": 45.2,
            "pause_count": 6,
            "speech_rate_wpm": 118.0,
        },
        linguistic_features={
            "lexical_diversity": 0.61,
            "word_count": 87,
            "filler_word_count": 4,
        },
        model_version="mock-0.0",
        needs_clinician_review=True,
    )
```

`task_id` is accepted but unused for now — it's part of the permanent signature so the real pipeline (which will vary output by task) can replace this function body without changing any caller.

`backend/services/__init__.py` is empty.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/backend/test_mock_inference.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/__init__.py backend/services/mock_inference.py tests/backend/test_mock_inference.py
git commit -m "feat(backend): add mock inference service"
```

---

### Task 4: `POST /api/assessments` endpoint

**Files:**
- Modify: `backend/routes/assessments.py`
- Test: `tests/backend/test_assessments.py`

**Interfaces:**
- Consumes: `backend.services.mock_inference.generate_mock_result(language, task_id) -> AssessmentResult` (Task 3); `backend.schemas.assessment.AssessmentResult` (Task 2).
- Produces: `POST /api/assessments` route on `backend.routes.assessments:router`, already mounted by `backend.main:app` (Task 1) — nothing later depends on new names.

- [ ] **Step 1: Write the failing test**

```python
# tests/backend/test_assessments.py
import io

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def _post_assessment():
    audio_bytes = io.BytesIO(b"fake-audio-bytes")
    return client.post(
        "/api/assessments",
        files={"audio": ("sample.wav", audio_bytes, "audio/wav")},
        data={"language": "en", "task_id": "cookie-theft"},
    )


def test_create_assessment_returns_mock_result():
    response = _post_assessment()

    assert response.status_code == 200
    body = response.json()
    assert body["language"] == "en"
    assert body["model_version"] == "mock-0.0"
    assert "risk_score" in body
    assert "speech_features" in body
    assert "linguistic_features" in body
    assert "needs_clinician_review" in body


def test_create_assessment_ids_are_unique_per_call():
    first_id = _post_assessment().json()["assessment_id"]
    second_id = _post_assessment().json()["assessment_id"]

    assert first_id != second_id
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/backend/test_assessments.py -v`
Expected: FAIL — `404 Not Found` (route doesn't exist yet), assertion on `response.status_code == 200` fails.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/routes/assessments.py
from fastapi import APIRouter, File, Form, UploadFile

from backend.schemas.assessment import AssessmentResult
from backend.services.mock_inference import generate_mock_result

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.post("/api/assessments", response_model=AssessmentResult)
async def create_assessment(
    audio: UploadFile = File(...),
    language: str = Form(...),
    task_id: str = Form(...),
) -> AssessmentResult:
    await audio.read()  # Phase 0: audio is discarded, not processed or stored.
    return generate_mock_result(language, task_id)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/backend/test_assessments.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/routes/assessments.py tests/backend/test_assessments.py
git commit -m "feat(backend): add POST /api/assessments endpoint"
```

---

### Task 5: README run instructions + manual smoke test

**Files:**
- Modify: `backend/README.md`

**Interfaces:**
- Consumes: everything from Tasks 1–4 (the running service).
- Produces: nothing new for other tasks — this is the last task in this plan.

- [ ] **Step 1: Update the README**

```markdown
# Backend

FastAPI backend for the assessment pipeline. Phase 0 status: skeleton only —
`/health` and `POST /api/assessments` both return fixed mock data
(`model_version: "mock-0.0"`). No real audio processing, ML inference, or
persistence yet — see `docs/ACTION_PLAN.md` Phase 1.

## Setup

From the repo root:

\`\`\`bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r backend/requirements-dev.txt
\`\`\`

## Run

\`\`\`bash
uvicorn backend.main:app --reload
\`\`\`

## Test

\`\`\`bash
pytest tests/backend -v
\`\`\`

## Manual smoke test

\`\`\`bash
curl http://127.0.0.1:8000/health

curl -F "audio=@some_file.wav;type=audio/wav" \
     -F "language=en" \
     -F "task_id=cookie-theft" \
     http://127.0.0.1:8000/api/assessments
\`\`\`

Expect a `200` with a JSON body containing `assessment_id`, `language`,
`risk_score`, `speech_features`, `linguistic_features`, `model_version`
(`"mock-0.0"`), and `needs_clinician_review`.
```

- [ ] **Step 2: Manually verify end-to-end**

Run: `uvicorn backend.main:app --reload` (from repo root, venv active), then in another terminal run both `curl` commands above.
Expected: `/health` returns `{"status":"ok"}`; `/api/assessments` returns `200` with the full mock JSON contract.

- [ ] **Step 3: Commit**

```bash
git add backend/README.md
git commit -m "docs(backend): add setup, run, and smoke-test instructions"
```

---

## Self-Review Notes

- **Spec coverage:** `/health` (Task 1), combined upload+inference endpoint (Task 4), `AssessmentResult` contract fields (Task 2), mock service with replaceable signature (Task 3), venv/requirements setup and run docs (Tasks 1 & 5), no-persistence/audio-discarded constraints (Task 4) — all spec sections have a task.
- **Placeholder scan:** no TBD/TODO; all code blocks are complete and runnable as written.
- **Type consistency:** `generate_mock_result(language: str, task_id: str) -> AssessmentResult` matches its Task 3 definition and Task 4's call site exactly; `AssessmentResult` fields are identical across Task 2's definition, Task 3's construction, and Task 4/README's documented response shape.
