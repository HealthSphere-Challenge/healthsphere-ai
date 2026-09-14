import json
from pathlib import Path

from healthsphere_ai.cohort import LEAKAGE_BLACKLIST


def test_frozen_spec_is_training_free_and_matches_leakage_contract() -> None:
    spec = json.loads(Path("specs/hypertension_5y_v1.json").read_text())
    assert spec["status"] == "approved_for_training"
    assert spec["target_version"] == "incident_essential_hypertension_5y_v1"
    assert spec["feature_schema_version"] == "hypertension_features_v1"
    assert set(spec["leakage_blacklist"]) == LEAKAGE_BLACKLIST
    assert spec["artifact_expectations"]["stage_8_creates_model_artifacts"] is False


def test_required_runtime_features_are_bounded_and_obtainable() -> None:
    spec = json.loads(Path("specs/hypertension_5y_v1.json").read_text())
    required = {feature["name"] for feature in spec["features"] if feature["required"]}
    assert required == {"age_years", "systolic_blood_pressure", "diastolic_blood_pressure"}
    assert all(feature["runtime_source"] for feature in spec["features"])
    assert spec["split"]["unit"] == "patient"
    assert spec["split"]["patient_overlap_allowed"] is False
