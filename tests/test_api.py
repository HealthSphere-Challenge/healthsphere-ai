from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from healthsphere_ai.api import create_app
from healthsphere_ai.artifacts import ArtifactError, ModelBundle

ARTIFACTS = Path("artifacts/hypertension_5y/v1")
TOKEN = "test-service-token"
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "X-Request-ID": "c4a760a8-7d0b-4f98-9652-244be1ebcc2e",
}
PAYLOAD = {
    "schema_version": "1.0",
    "request_id": "c4a760a8-7d0b-4f98-9652-244be1ebcc2e",
    "subject_ref": "f630d635-64e2-432b-8175-60f61d220d4d",
    "features": {
        "age_years": 42.0,
        "systolic_blood_pressure": 128.0,
        "diastolic_blood_pressure": 82.0,
        "heart_rate": 76.0,
        "bmi": 24.7,
        "sex_at_birth": "female",
        "smoking_status": "never",
    },
}


def app_client():
    app = create_app(bundle=ModelBundle.load(ARTIFACTS), internal_api_token=TOKEN)
    return TestClient(app)


def test_health_and_authoritative_route():
    with app_client() as client:
        assert client.get("/health").json() == {"status": "ready"}
        response = client.post("/internal/v1/inferences", json=PAYLOAD, headers=HEADERS)
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "completed"
        assert body["request_id"] == PAYLOAD["request_id"]
        assert body["result"]["calibrated"] is False
        assert body["result"]["score_type"] == "uncalibrated_experimental_probability_estimate"
        assert body["provenance"]["model_version"] == "hypertension_5y_v1.0.0"
        assert body["provenance"]["feature_schema_version"] == "hypertension_features_v1"
        assert "diagnosis" not in body["result"]
        assert (
            client.post("/internal/v1/predictions", json=PAYLOAD, headers=HEADERS).status_code
            == 404
        )


def test_missing_required_feature_returns_insufficient_data():
    payload = PAYLOAD | {"features": PAYLOAD["features"] | {"age_years": None}}
    with app_client() as client:
        response = client.post("/internal/v1/inferences", json=payload, headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["status"] == "insufficient_data"


def test_contract_validation_uses_canonical_error_envelope():
    payload = PAYLOAD | {"schema_version": "2.0"}
    with app_client() as client:
        response = client.post("/internal/v1/inferences", json=payload, headers=HEADERS)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["request_id"] == PAYLOAD["request_id"]
    assert "detail" not in response.json()


def test_request_id_header_must_match_envelope():
    headers = HEADERS | {"X-Request-ID": "5291676e-3037-4d38-8617-31e84391d71a"}
    with app_client() as client:
        response = client.post("/internal/v1/inferences", json=PAYLOAD, headers=headers)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "request_id_mismatch"


def test_authentication_uses_canonical_error_envelope():
    with app_client() as client:
        response = client.post("/internal/v1/inferences", json=PAYLOAD)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_runtime_failure_maps_to_unavailable(monkeypatch):
    bundle = ModelBundle.load(ARTIFACTS)

    def fail(_values):
        raise RuntimeError("private implementation detail")

    monkeypatch.setattr(bundle.model, "predict_proba", fail)
    app = create_app(bundle=bundle, internal_api_token=TOKEN)
    with TestClient(app) as client:
        response = client.post("/internal/v1/inferences", json=PAYLOAD, headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["status"] == "unavailable"
    assert response.json()["result"] is None
    assert "private implementation detail" not in response.text


def test_startup_fails_when_artifacts_are_unavailable(tmp_path):
    app = create_app(artifact_dir=tmp_path, internal_api_token=TOKEN)
    with pytest.raises(ArtifactError), TestClient(app):
        pass
