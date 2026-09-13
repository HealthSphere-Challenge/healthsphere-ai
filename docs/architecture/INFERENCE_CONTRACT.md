# Backend–AI inference contract

Status: stable transport is **APPROVED CONTRACT for HS-002; documentation only**. Model meaning is **PENDING HS-010**. No endpoint, model, feature pipeline, score, label, threshold, or artifact is implemented here.

Contract revision: `phase1-hs002-2026-09-13`. The backend contract is the application-level companion; AI owns the Pydantic producer/consumer schemas for this service boundary.

## Transport — APPROVED CONTRACT

The backend alone calls `POST /internal/v1/inferences`. Requests use a service-specific opaque bearer credential and `X-Request-ID`. IDs are UUIDv4. JSON uses `snake_case`; timestamps use RFC 3339 UTC with milliseconds. Connect timeout is 2 seconds and total timeout is 10 seconds. The backend performs no automatic application retry initially.

```json
{
  "schema_version": "1.0",
  "request_id": "c4a760a8-7d0b-4f98-9652-244be1ebcc2e",
  "subject_ref": "f630d635-64e2-432b-8175-60f61d220d4d",
  "features": { "pending_hs_010": true }
}
```

`subject_ref` is a pseudonymous request/service reference, not the application user ID. The exact feature object is **PENDING HS-010**. The AI service receives no session cookie, email, conversation, unrestricted profile, or direct database access.

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
    "missing_fields": ["pending_hs_010"]
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

## Completed result — PENDING HS-010

A future completed response has this structural obligation, but no field represented by a `pending_hs_010` placeholder has approved meaning or a usable runtime value:

```json
{
  "schema_version": "1.0",
  "request_id": "c4a760a8-7d0b-4f98-9652-244be1ebcc2e",
  "status": "completed",
  "result": {
    "target": "pending_hs_010",
    "population": "pending_hs_010",
    "horizon": "pending_hs_010",
    "score": null,
    "score_semantics": "pending_hs_010",
    "label": null,
    "explanation": null,
    "limitations": []
  },
  "provenance": {
    "model_name": "pending_hs_010",
    "model_version": "pending_hs_010",
    "feature_schema_version": "pending_hs_010",
    "preprocessing_version": "pending_hs_010",
    "calibration_version": null,
    "explanation_method": "pending_hs_010",
    "generated_at": "2026-09-13T09:05:43.000Z"
  }
}
```

HS-010 must approve the assessment target, eligible population, prediction horizon, feature schema, minimum inputs, score semantics, calibration, risk labels, thresholds, and explanation method before `completed` is implementable. Do not fabricate representative values, treat global feature importance as individual causation, or claim clinical validity.

## Compatibility and tests

AI owns Pydantic request and response schemas. Backend validates AI responses with its consumer schemas. Future fixture-based contract tests use synthetic cases for every state, malformed versions, missing/null fields, provenance, timeout, and invalid response mapping. Compatible additions remain optional; type, enum, unit, meaning, or nullability changes require a schema-version change and linked producer/consumer PR evidence. Python 3.13 with `uv` is the approved baseline; exact dependency versions are selected and tested in implementation tickets.
