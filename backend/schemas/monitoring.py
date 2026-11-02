from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ApplianceState(BaseModel):
    name: str
    state: Literal["on", "off", "unknown"] = "unknown"


class ObservationIn(BaseModel):
    """One structured observation of the monitored room.

    Same schema the vision model emits (monitoring/nurse_observer.py). Every
    field is optional: anything omitted defaults to 'nothing observed'.
    Unknown extra keys (e.g. a model's raw output) are ignored.
    """

    model_config = ConfigDict(extra="ignore")

    person_present: bool = False
    posture: str = "unknown"
    on_floor: bool = False
    motion: str = "none"
    location: str = Field(default="unknown", max_length=200)
    hands: str = Field(default="unknown", max_length=200)
    activity: str = Field(default="none", max_length=200)
    appliances: list[ApplianceState] = Field(default_factory=list, max_length=20)
    water_running: bool = False
    door_open: bool = False
    sharp_or_hot_object_in_hand: bool = False
    visible_smoke_or_flame: bool = False
    unsteady_or_swaying: bool = False
    fall_in_progress: bool = False
    sudden_descent: bool = False
    note: str = Field(default="", max_length=500)
    patient_id: str | None = Field(default=None, max_length=100)


class AlertOut(BaseModel):
    at: str
    level: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    kind: str
    summary: str
    evidence: str
    action: str
    patient_id: str | None = None
    source: str = "live"


class LiveCameraStatus(BaseModel):
    available: bool
    missing: list[str]
    observer: str
    observer_error: str | None = None
    last_error: str | None = None


class MonitoringStatus(BaseModel):
    live_camera: LiveCameraStatus
    counters: dict
    state: dict
