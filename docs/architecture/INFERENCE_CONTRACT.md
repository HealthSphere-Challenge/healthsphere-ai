# Backend–AI inference contract

Status: stable HS-002 transport is the **AUTHORITATIVE CONTRACT**. HS-011 implements the
trained hypertension model behind that contract. The earlier Stage 10 `/predictions`
wording was superseded; no competing endpoint exists.

Contract revision: `phase1-hs002-2026-09-13`. The backend contract is the application-level companion; AI owns the Pydantic producer/consumer schemas for this service boundary.

## Transport — APPROVED CONTRACT

The backend alone calls `POST /internal/v1/inferences`. Requests use a service-specific opaque bearer credential and `X-Request-ID`. IDs are UUIDv4. JSON uses `snake_case`; timestamps use RFC 3339 UTC with milliseconds. Connect timeout is 2 seconds and total timeout is 10 seconds. The backend performs no automatic application retry initially.

```json
{
  "schema_version": "1.0",
  "request_id": "c4a760a8-7d0b-4f98-9652-244be1ebcc2e",
  "subject_ref": "f630d635-64e2-432b-8175-60f61d220d4d",
  "features": {
    "age_years": 42,
    "systolic_blood_pressure": 128,
    "diastolic_blood_pressure": 82,
    "heart_rate": 76,
    "bmi": 24.7,
    "sex_at_birth": "female",
    "smoking_status": "never"
  }
}
```

`subject_ref` is a pseudonymous request/service reference, not the application user ID. Only
the nested feature object enters preprocessing; transport fields never enter the model matrix.
The AI service receives no session cookie, email, conversation, unrestricted profile, or
direct database access. `X-Request-ID` must contain the same UUIDv4 as the envelope.

## Response states — APPROVED CONTRACT

AI returns exactly one state: `completed`, `insufficient_data`, `ineligible`, or `unavailable`. Non-completed states contain `result: null`; a consumer must never translate them to a score or low-risk result.

```json
{
  "schema_version": "1.0",
  "request_id": "c4a760a8-7d0b-4f98-9652-244be1ebcc2e",
  "status": "insufficient_data",
  "result": null,
  "reason": {
    "code": "minimum_inputs_missing",
    "missing_fields": ["age_years"]
  },
  "provenance": null
}
```

For `unavailable`, `reason.code` may identify a safe category such as `model_unavailable` or `inference_unavailable`, without exposing provider internals. Canonical transport errors use the shared error object:

```json
{
  "error": {
    "code": "validation_error",
    "message": "The inference request could not be validated.",
    "details": null,
    "request_id": "c4a760a8-7d0b-4f98-9652-244be1ebcc2e",
    "retry_after_seconds": null
  }
}
```

## Completed result — HS-011

The completed response preserves the HS-002 envelope and exposes the frozen experimental
score with explicit calibration limitations:

```json
{
  "schema_version": "1.0",
  "request_id": "c4a760a8-7d0b-4f98-9652-244be1ebcc2e",
  "status": "completed",
  "result": {
    "target": "incident_essential_hypertension_5y_v1",
    "population": "eligible adult at first paired-BP encounter after 365 days history",
    "horizon": "1825 days after index encounter stop",
    "score": 0.1234,
    "score_type": "uncalibrated_experimental_probability_estimate",
    "calibrated": false,
    "label": null,
    "explanation": null,
    "limitations": []
  },
  "provenance": {
    "model_name": "HealthSphere experimental hypertension XGBoost",
    "model_version": "hypertension_5y_v1.0.0",
    "feature_schema_version": "hypertension_features_v1",
    "preprocessing_version": "hypertension_preprocessing_v1",
    "calibration_version": null,
    "explanation_method": "global_native_xgboost_gain_only",
    "prediction_horizon_days": 1825,
    "calibrated": false,
    "calibration_status": "uncalibrated; trained and evaluated on synthetic Synthea data",
    "generated_at": "2026-09-13T09:05:43.000Z"
  }
}
```

Required model inputs are age and paired systolic/diastolic BP. Their absence produces
`insufficient_data`; an age below the approved adult population produces `ineligible`.
Optional numeric inputs may be null and use the frozen preprocessing. Optional categories
default to `unknown`. The score is uncalibrated synthetic-data evidence. No label, diagnosis,
clinical threshold, or patient-specific explanation is produced.

## Compatibility and tests

AI owns Pydantic request and response schemas. Backend validates AI responses with its consumer schemas. Future fixture-based contract tests use synthetic cases for every state, malformed versions, missing/null fields, provenance, timeout, and invalid response mapping. Compatible additions remain optional; type, enum, unit, meaning, or nullability changes require a schema-version change and linked producer/consumer PR evidence. Python 3.13 with `uv` is the approved baseline; exact dependency versions are selected and tested in implementation tickets.
