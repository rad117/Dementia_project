from pydantic import BaseModel

from backend.schemas.results import _CamelModel


class ParticipantCodeRequest(BaseModel):
    code: str


class AssistedLoginRequest(_CamelModel):
    patient_id: str


class ClinicalLoginRequest(BaseModel):
    email: str
    password: str


class ParticipantLoginResponse(_CamelModel):
    patient_id: str
    name: str
    token: str


class ClinicalLoginResponse(BaseModel):
    name: str
    role: str
    token: str
