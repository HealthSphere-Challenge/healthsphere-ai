from copy import deepcopy
from uuid import UUID

import numpy as np
import pytest

from healthsphere_ai.artifacts import ModelBundle
from healthsphere_ai.inference import InferenceExecutionError, InferenceService
from healthsphere_ai.schemas import InferenceRequest

ARTIFACTS = __import__("pathlib").Path("artifacts/hypertension_5y/v1")


def request(**feature_overrides) -> InferenceRequest:
    features = {
        "age_years": 42.0,
        "systolic_blood_pressure": 128.0,
        "diastolic_blood_pressure": 82.0,
        "heart_rate": 76.0,
        "bmi": 24.7,
        "sex_at_birth": "female",
        "smoking_status": "never",
    }
    features.update(feature_overrides)
    return InferenceRequest.model_validate(
        {
            "schema_version": "1.0",
            "request_id": "c4a760a8-7d0b-4f98-9652-244be1ebcc2e",
            "subject_ref": "f630d635-64e2-432b-8175-60f61d220d4d",
            "features": features,
        }
    )


@pytest.fixture(scope="module")
def service() -> InferenceService:
    return InferenceService(ModelBundle.load(ARTIFACTS))


def test_complete_inference_is_deterministic_bounded_and_golden(service):
    first = service.predict(request())
    second = service.predict(request())
    assert first.status == "completed"
    assert first.request_id == UUID("c4a760a8-7d0b-4f98-9652-244be1ebcc2e")
    assert first.result is not None
    assert first.result.score == pytest.approx(second.result.score, abs=1e-12)
    assert first.result.score == pytest.approx(0.5450911521911621, abs=1e-8)
    assert 0 <= first.result.score <= 1
    assert first.result.calibrated is False
    assert first.result.label is None
    assert first.provenance.model_version == "hypertension_5y_v1.0.0"
    assert first.provenance.feature_schema_version == "hypertension_features_v1"


def test_optional_values_can_be_missing_and_categories_default_unknown(service):
    response = service.predict(
        request(heart_rate=None, bmi=None, sex_at_birth=None, smoking_status=None)
    )
    assert response.status == "completed"
    assert np.isfinite(response.result.score)


def test_required_missing_is_business_status(service):
    for name in ("age_years", "systolic_blood_pressure", "diastolic_blood_pressure"):
        response = service.predict(request(**{name: None}))
        assert response.status == "insufficient_data"
        assert response.result is None
        assert response.reason.code == "minimum_inputs_missing"
        assert response.reason.missing_fields == [name]


def test_underage_is_only_approved_ineligible_rule(service):
    response = service.predict(request(age_years=17.0))
    assert response.status == "ineligible"
    assert response.reason.code == "adult_population_required"


def test_transport_fields_never_change_model_score(service):
    original = request()
    changed = deepcopy(original)
    changed.request_id = UUID("5291676e-3037-4d38-8617-31e84391d71a")
    changed.subject_ref = UUID("35c887d3-d315-4554-8722-0049219f2efd")
    assert service.predict(original).result.score == service.predict(changed).result.score


def test_non_finite_and_malformed_category_are_rejected():
    with pytest.raises(ValueError):
        request(heart_rate=float("nan"))
    with pytest.raises(ValueError):
        request(smoking_status="sometimes")


def test_invalid_model_output_fails_closed(service, monkeypatch):
    monkeypatch.setattr(
        service.bundle.model,
        "predict_proba",
        lambda _values: np.asarray([[0.0, np.nan]]),
    )
    with pytest.raises(InferenceExecutionError):
        service.predict(request())
