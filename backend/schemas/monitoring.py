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
    scenario: str | None = None


class ScenarioOut(BaseModel):
    id: str
    title: str
    description: str


class LiveCameraStatus(BaseModel):
    available: bool
    missing: list[str]
    pose: bool = False
    vlm: bool = False
    observer: str
    observer_error: str | None = None
    last_error: str | None = None


class MonitoringStatus(BaseModel):
    live_camera: LiveCameraStatus
    counters: dict
    state: dict


class ContactIn(BaseModel):
    patient_id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=100)
    phone: str = Field(description="International format, e.g. +919876543210")
    channel: Literal["sms", "whatsapp"] = "sms"


class ContactOut(BaseModel):
    id: int
    patient_id: str
    name: str
    phone: str
    channel: str


class NotificationOut(BaseModel):
    id: int
    at: str
    patient_id: str | None = None
    contact_id: int | None = None
    channel: str
    alert_kind: str | None = None
    status: str
    detail: str | None = None
