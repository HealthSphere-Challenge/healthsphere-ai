"""Reusable inference service using only verified frozen artifacts."""

from __future__ import annotations

from datetime import UTC, datetime

import numpy as np

from healthsphere_ai.artifacts import ModelBundle
from healthsphere_ai.schemas import (
    CompletedResult,
    InferenceReason,
    InferenceRequest,
    InferenceResponse,
    Provenance,
)

REQUIRED_FIELDS = (
    "age_years",
    "systolic_blood_pressure",
    "diastolic_blood_pressure",
)
LIMITATIONS = [
    "Uncalibrated experimental score trained only on synthetic Synthea data.",
    "Not clinically validated and not suitable for diagnosis or treatment decisions.",
]


class InferenceExecutionError(RuntimeError):
    """Raised when verified artifacts cannot produce a valid prediction."""


class InferenceService:
    def __init__(self, bundle: ModelBundle) -> None:
        self.bundle = bundle

    def _provenance(self) -> Provenance:
        metadata = self.bundle.metadata
        return Provenance(
            model_name="HealthSphere experimental hypertension XGBoost",
            model_version=metadata["model_version"],
            feature_schema_version=metadata["feature_schema_version"],
            preprocessing_version=metadata["preprocessing_version"],
            explanation_method="global_native_xgboost_gain_only",
            prediction_horizon_days=1825,
            calibrated=False,
            calibration_status="uncalibrated; trained and evaluated on synthetic Synthea data",
            generated_at=datetime.now(UTC),
        )

    def predict(self, request: InferenceRequest) -> InferenceResponse:
        features = request.features.model_dump()
        missing = [name for name in REQUIRED_FIELDS if features[name] is None]
        if missing:
            return InferenceResponse(
                request_id=request.request_id,
                status="insufficient_data",
                result=None,
                reason=InferenceReason(code="minimum_inputs_missing", missing_fields=missing),
                provenance=None,
            )
        if features["age_years"] < 18:
            return InferenceResponse(
                request_id=request.request_id,
                status="ineligible",
                result=None,
                reason=InferenceReason(code="adult_population_required"),
                provenance=None,
            )
        features["sex_at_birth"] = features["sex_at_birth"] or "unknown"
        features["smoking_status"] = features["smoking_status"] or "unknown"
        order = self.bundle.metadata["feature_order"]
        raw_matrix = np.asarray([[features[name] for name in order]], dtype=object)
        try:
            transformed = self.bundle.preprocessing.transform(raw_matrix)
            score = float(self.bundle.model.predict_proba(transformed)[0, 1])
        except Exception as exc:
            raise InferenceExecutionError("The model could not produce an inference.") from exc
        if not np.isfinite(score) or not 0 <= score <= 1:
            raise InferenceExecutionError("The model returned an invalid score.")
        return InferenceResponse(
            request_id=request.request_id,
            status="completed",
            result=CompletedResult(
                target=self.bundle.metadata["target_id"],
                population="eligible adult at first paired-BP encounter after 365 days history",
                horizon="1825 days after index encounter stop",
                score=score,
                score_type="uncalibrated_experimental_probability_estimate",
                calibrated=False,
                limitations=LIMITATIONS,
            ),
            reason=None,
            provenance=self._provenance(),
        )
