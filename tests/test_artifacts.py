import json
from pathlib import Path

import joblib
import numpy as np
from xgboost import XGBClassifier

from healthsphere_ai.cohort import CohortRow
from healthsphere_ai.training import FEATURE_ORDER, matrix

ARTIFACTS = Path("artifacts/hypertension_5y/v1")


def test_committed_artifacts_match_schema_and_reload():
    metadata = json.loads((ARTIFACTS / "metadata.json").read_text())
    metrics = json.loads((ARTIFACTS / "metrics.json").read_text())
    assert metadata["target_id"] == "incident_essential_hypertension_5y_v1"
    assert metadata["feature_schema_version"] == "hypertension_features_v1"
    assert metadata["feature_order"] == list(FEATURE_ORDER)
    assert metadata["threshold"] == metrics["selection"]["threshold"]

    row = CohortRow(
        "synthetic-fixture",
        __import__("datetime").date(2026, 1, 1),
        0,
        {
            "age_years": 45.0,
            "systolic_blood_pressure": 125.0,
            "diastolic_blood_pressure": 80.0,
            "heart_rate": None,
            "bmi": None,
            "sex_at_birth": "unknown",
            "smoking_status": "unknown",
        },
        {},
    )
    preprocessing = joblib.load(ARTIFACTS / "preprocessing.joblib")
    model = XGBClassifier()
    model.load_model(ARTIFACTS / "model.json")
    probability = model.predict_proba(preprocessing.transform(matrix([row])))[:, 1]
    assert probability.shape == (1,)
    assert np.logical_and(probability >= 0, probability <= 1).all()
