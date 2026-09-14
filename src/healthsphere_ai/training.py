"""Leakage-safe reproducible training primitives for the frozen HS-010 model."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from healthsphere_ai.cohort import LEAKAGE_BLACKLIST, CohortRow

FEATURE_ORDER = (
    "age_years",
    "systolic_blood_pressure",
    "diastolic_blood_pressure",
    "heart_rate",
    "bmi",
    "sex_at_birth",
    "smoking_status",
)
REQUIRED = ("age_years", "systolic_blood_pressure", "diastolic_blood_pressure")
OPTIONAL_NUMERIC = ("heart_rate", "bmi")
CATEGORICAL = ("sex_at_birth", "smoking_status")
SPLIT_SEED = 20260915


@dataclass(frozen=True)
class Split:
    train: list[int]
    validation: list[int]
    test: list[int]


def split_patients(rows: list[CohortRow], seed: int = SPLIT_SEED) -> Split:
    """Create deterministic 70/15/15 target-stratified patient partitions."""
    indices = np.arange(len(rows))
    labels = np.array([row.target for row in rows])
    train, remainder = train_test_split(indices, test_size=0.30, random_state=seed, stratify=labels)
    validation, test = train_test_split(
        remainder,
        test_size=0.50,
        random_state=seed,
        stratify=labels[remainder],
    )
    return Split(sorted(train.tolist()), sorted(validation.tolist()), sorted(test.tolist()))


def validate_rows(rows: list[CohortRow]) -> None:
    """Reject schema, required-input, identifier, and temporal leakage."""
    ids = [row.patient_id for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate patients in cohort")
    for row in rows:
        unexpected = set(row.features) - set(FEATURE_ORDER)
        prohibited = set(row.features) & LEAKAGE_BLACKLIST
        if unexpected or prohibited:
            raise ValueError(f"Invalid feature columns: {sorted(unexpected | prohibited)}")
        if any(row.features.get(name) is None for name in REQUIRED):
            raise ValueError("Required feature is absent")
        if any(observed_at > row.index_date for observed_at in row.feature_dates.values()):
            raise ValueError("Post-index feature detected")


def matrix(rows: list[CohortRow]) -> np.ndarray:
    """Create the stable raw inference matrix in schema order."""
    validate_rows(rows)
    return np.asarray(
        [[row.features[name] for name in FEATURE_ORDER] for row in rows], dtype=object
    )


def make_preprocessor() -> ColumnTransformer:
    optional = Pipeline(
        [
            ("impute", SimpleImputer(strategy="median", add_indicator=True)),
        ]
    )
    categorical = Pipeline(
        [
            ("impute", SimpleImputer(strategy="constant", fill_value="unknown")),
            ("encode", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )
    return ColumnTransformer(
        [
            ("required", "passthrough", [0, 1, 2]),
            ("optional", optional, [3, 4]),
            ("categorical", categorical, [5, 6]),
        ],
        verbose_feature_names_out=False,
    )


def classification_metrics(
    y: np.ndarray, probabilities: np.ndarray, threshold: float
) -> dict[str, Any]:
    predictions = probabilities >= threshold
    tn, fp, fn, tp = confusion_matrix(y, predictions, labels=[0, 1]).ravel()
    return {
        "n": int(len(y)),
        "positive_n": int(y.sum()),
        "negative_n": int(len(y) - y.sum()),
        "prevalence": float(y.mean()),
        "threshold": float(threshold),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "sensitivity": float(recall_score(y, predictions, zero_division=0)),
        "specificity": float(tn / (tn + fp)) if tn + fp else None,
        "precision": float(precision_score(y, predictions, zero_division=0)),
        "f1": float(f1_score(y, predictions, zero_division=0)),
        "roc_auc": float(roc_auc_score(y, probabilities)),
        "pr_auc": float(average_precision_score(y, probabilities)),
        "brier_score": float(brier_score_loss(y, probabilities)),
    }


def select_f1_threshold(y: np.ndarray, probabilities: np.ndarray) -> float:
    """Freeze the validation-only threshold maximizing F1, preferring lower ties."""
    candidates = np.unique(np.concatenate(([0.0], probabilities, [1.0])))
    scores = [f1_score(y, probabilities >= value, zero_division=0) for value in candidates]
    return float(candidates[int(np.argmax(scores))])


def calibration_bins(
    y: np.ndarray, probabilities: np.ndarray, bins: int = 5
) -> list[dict[str, Any]]:
    edges = np.linspace(0, 1, bins + 1)
    result = []
    for number in range(bins):
        include = (probabilities >= edges[number]) & (
            probabilities <= edges[number + 1]
            if number == bins - 1
            else probabilities < edges[number + 1]
        )
        result.append(
            {
                "lower": float(edges[number]),
                "upper": float(edges[number + 1]),
                "n": int(include.sum()),
                "mean_probability": float(probabilities[include].mean()) if include.any() else None,
                "event_rate": float(y[include].mean()) if include.any() else None,
            }
        )
    return result


def bootstrap_metrics(
    y: np.ndarray,
    probabilities: np.ndarray,
    threshold: float,
    replicates: int = 2000,
    seed: int = 20260916,
) -> dict[str, Any]:
    """Patient-level stratified bootstrap with deterministic within-class resampling."""
    rng = np.random.default_rng(seed)
    classes = [np.flatnonzero(y == value) for value in (0, 1)]
    values: dict[str, list[float]] = {
        name: []
        for name in (
            "pr_auc",
            "roc_auc",
            "sensitivity",
            "specificity",
            "precision",
            "f1",
            "brier_score",
        )
    }
    for _ in range(replicates):
        sample = np.concatenate([rng.choice(group, len(group), replace=True) for group in classes])
        metrics = classification_metrics(y[sample], probabilities[sample], threshold)
        for name in values:
            value = metrics[name]
            if value is not None:
                values[name].append(float(value))
    return {
        "seed": seed,
        "replicates": replicates,
        "method": (
            "patient-level stratified bootstrap; resample each outcome class with replacement"
        ),
        "single_class_samples_skipped": 0,
        "confidence_intervals_95": {
            name: {
                "lower": float(np.percentile(items, 2.5)),
                "upper": float(np.percentile(items, 97.5)),
            }
            for name, items in values.items()
        },
    }


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_split_manifest(path: Path, rows: list[CohortRow], split: Split) -> None:
    partitions = {
        name: [
            {"patient_id": rows[index].patient_id, "target": rows[index].target}
            for index in indexes
        ]
        for name, indexes in asdict(split).items()
    }
    write_json(path, {"seed": SPLIT_SEED, "unit": "patient", "partitions": partitions})


def dump_preprocessor(path: Path, preprocessor: ColumnTransformer) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(preprocessor, path)
