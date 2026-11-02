"""Safety monitoring: camera/observation-driven risk alerts for the clinician dashboard.

Every endpoint here responds with JSON even when the optional camera/ML
packages are not installed -- the speech-screening half of the application
never depends on this module being usable.
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from backend.schemas.monitoring import AlertOut, MonitoringStatus, ObservationIn
from backend.services.auth import require_clinician
from monitoring import store
from monitoring.service import MAX_FRAME_BYTES, get_service

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


@router.post("/demo", response_model=list[AlertOut], status_code=201)
def run_demo(patient_id: str | None = None) -> list[AlertOut]:
    """Replay a scripted incident (unattended stove, then a fall) as demo alerts."""
    alerts = get_service().run_demo(patient_id=patient_id)
    return [AlertOut(**a, patient_id=patient_id, source="demo") for a in alerts]


@router.delete("/demo")
def clear_demo() -> dict:
    return {"deleted": store.clear_source("demo")}
