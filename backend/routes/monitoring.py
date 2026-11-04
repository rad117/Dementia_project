"""Safety monitoring: camera/observation-driven risk alerts for the clinician dashboard.

Every endpoint here responds with JSON even when the optional camera/ML
packages are not installed -- the speech-screening half of the application
never depends on this module being usable.
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from backend import db
from backend.schemas.monitoring import AlertOut, MonitoringStatus, ObservationIn, ScenarioOut
from backend.services.auth import require_clinician
from monitoring import store
from monitoring.service import DEFAULT_SCENARIO, MAX_FRAME_BYTES, SCENARIOS, get_service, list_scenarios

# Camera observations describe a real person in a real room: every endpoint
# here requires a signed-in clinician (same bearer token as the dashboard).
router = APIRouter(
    prefix="/monitoring", tags=["monitoring"], dependencies=[Depends(require_clinician)]
)


def _alert_out(row: dict) -> AlertOut:
    return AlertOut(**{k: row[k] for k in AlertOut.model_fields})


@router.get("/status", response_model=MonitoringStatus)
def monitoring_status() -> dict:
    return get_service().status()


@router.get("/alerts", response_model=list[AlertOut])
def list_alerts(limit: int = 50, patient_id: str | None = None) -> list[AlertOut]:
    limit = max(1, min(limit, 200))
    return [_alert_out(r) for r in store.list_alerts(limit=limit, patient_id=patient_id)]


@router.get("/observation")
def last_observation() -> dict:
    """Most recent raw observation -- for debugging why an alert did or didn't fire."""
    return store.last_observation() or {}


@router.post("/observations", response_model=list[AlertOut], status_code=201)
def ingest_observation(payload: ObservationIn) -> list[AlertOut]:
    """Submit a structured observation; returns any risk alerts it triggered."""
    data = payload.model_dump(exclude={"patient_id"})
    alerts = get_service().ingest_observation(data, patient_id=payload.patient_id)
    return [AlertOut(**a, patient_id=payload.patient_id) for a in alerts]


@router.post("/frame")
async def submit_frame(frame: UploadFile = File(...), patient_id: str | None = None) -> dict:
    """Submit one camera JPEG. Returns status 'unavailable' if the vision stack is not installed."""
    data = await frame.read(MAX_FRAME_BYTES + 1)
    try:
        return get_service().add_frame(data, patient_id=patient_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/scenarios", response_model=list[ScenarioOut])
def scenarios() -> list[dict]:
    """The scripted incidents the demo can replay."""
    return list_scenarios()


@router.post("/demo", response_model=list[AlertOut], status_code=201)
def run_demo(patient_id: str | None = None, scenario: str = DEFAULT_SCENARIO) -> list[AlertOut]:
    """Replay a scripted incident through the real rules engine as demo alerts.

    Default scenario: an unattended stove, then a fall. See GET /monitoring/scenarios.
    """
    if scenario not in SCENARIOS:
        raise HTTPException(status_code=404, detail=f"Unknown scenario '{scenario}'")
    if patient_id and db.get_patient_row(patient_id) is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    alerts = get_service().run_demo(patient_id=patient_id, scenario=scenario)
    return [AlertOut(**a, patient_id=patient_id, source="demo", scenario=scenario) for a in alerts]


@router.delete("/demo")
def clear_demo() -> dict:
    return {"deleted": store.clear_source("demo")}
