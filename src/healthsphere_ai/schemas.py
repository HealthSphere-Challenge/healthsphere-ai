"""HS-002 transport and frozen HS-011 model schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class PredictionFeatures(StrictModel):
    age_years: float | None = Field(default=None, le=130)
    systolic_blood_pressure: float | None = Field(default=None, gt=0, le=400)
    diastolic_blood_pressure: float | None = Field(default=None, gt=0, le=300)
    heart_rate: float | None = Field(default=None, gt=0, le=300)
    bmi: float | None = Field(default=None, gt=0, le=150)
    sex_at_birth: Literal["male", "female", "unknown"] | None = None
    smoking_status: Literal["never", "former", "current", "unknown"] | None = None


class InferenceRequest(StrictModel):
    schema_version: Literal["1.0"]
    request_id: UUID = Field(strict=False)
    subject_ref: UUID = Field(strict=False)
    features: PredictionFeatures

    @field_validator("request_id", "subject_ref")
    @classmethod
    def require_uuid4(cls, value: UUID) -> UUID:
        if value.version != 4:
            raise ValueError("must be a UUIDv4")
        return value


class InferenceReason(StrictModel):
    code: str
    missing_fields: list[str] | None = None


class CompletedResult(StrictModel):
    target: str
    population: str
    horizon: str
    score: float
    score_type: Literal["uncalibrated_experimental_probability_estimate"]
    calibrated: Literal[False]
    label: None = None
    explanation: None = None
    limitations: list[str]


class Provenance(StrictModel):
    model_name: str
    model_version: str
    feature_schema_version: str
    preprocessing_version: str
    calibration_version: None = None
    explanation_method: str
    prediction_horizon_days: int
    calibrated: Literal[False]
    calibration_status: str
    generated_at: datetime


class InferenceResponse(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    request_id: UUID
    status: Literal["completed", "insufficient_data", "ineligible", "unavailable"]
    result: CompletedResult | None
    reason: InferenceReason | None
    provenance: Provenance | None


class ErrorDetail(StrictModel):
    code: str
    message: str
    details: list[dict[str, object]] | None = None
    request_id: UUID | None = None
    retry_after_seconds: int | None = None


class ErrorResponse(StrictModel):
    error: ErrorDetail
