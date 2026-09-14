"""Trusted loading and integrity checks for the frozen HS-010 artifacts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
from sklearn.compose import ColumnTransformer
from xgboost import XGBClassifier

EXPECTED_TARGET = "incident_essential_hypertension_5y_v1"
EXPECTED_SCHEMA = "hypertension_features_v1"
EXPECTED_MODEL_VERSION = "hypertension_5y_v1.0.0"
EXPECTED_MODEL_CLASS = "XGBClassifier"
EXPECTED_FEATURE_ORDER = [
    "age_years",
    "systolic_blood_pressure",
    "diastolic_blood_pressure",
    "heart_rate",
    "bmi",
    "sex_at_birth",
    "smoking_status",
]


class ArtifactError(RuntimeError):
    """Raised when trusted artifacts are unavailable, corrupt, or incompatible."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class ModelBundle:
    model: XGBClassifier
    preprocessing: ColumnTransformer
    metadata: dict[str, Any]
    metrics: dict[str, Any]

    @classmethod
    def load(cls, directory: Path) -> ModelBundle:
        metadata_path = directory / "metadata.json"
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ArtifactError("Model metadata is unavailable or invalid.") from exc

        expected = metadata.get("artifact_sha256")
        if not isinstance(expected, dict):
            raise ArtifactError("Artifact digest manifest is missing.")
        for filename in (
            "model.json",
            "preprocessing.joblib",
            "metrics.json",
            "split_manifest.json",
        ):
            path = directory / filename
            if not path.is_file():
                raise ArtifactError(f"Required artifact is missing: {filename}")
            if expected.get(filename) != sha256(path):
                raise ArtifactError(f"Artifact integrity check failed: {filename}")

        compatibility = {
            "target_id": EXPECTED_TARGET,
            "feature_schema_version": EXPECTED_SCHEMA,
            "model_version": EXPECTED_MODEL_VERSION,
            "model_class": EXPECTED_MODEL_CLASS,
            "feature_order": EXPECTED_FEATURE_ORDER,
        }
        for field, value in compatibility.items():
            if metadata.get(field) != value:
                raise ArtifactError(f"Artifact metadata is incompatible: {field}")

        try:
            metrics = json.loads((directory / "metrics.json").read_text(encoding="utf-8"))
            preprocessing = joblib.load(directory / "preprocessing.joblib")
            model = XGBClassifier()
            model.load_model(directory / "model.json")
        except Exception as exc:
            raise ArtifactError("A verified model artifact could not be loaded.") from exc
        if not isinstance(preprocessing, ColumnTransformer):
            raise ArtifactError("Preprocessing artifact has an incompatible type.")
        return cls(model=model, preprocessing=preprocessing, metadata=metadata, metrics=metrics)
