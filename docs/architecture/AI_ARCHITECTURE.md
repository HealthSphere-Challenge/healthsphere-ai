# Predictive AI architecture

Status: approved direction; only raw data and placeholder directories exist. Stage 2 does not train or serve a model.

Browser → frontend → backend → AI. Backend owns application identity, PostgreSQL and history. AI accepts minimum required structured features and returns experimental predictions with provenance. No direct browser calls, application database access or conversational generation. MedQuAD/MTS-Dialog belong to Agent, not predictive training.

## Planned modules

`src/preprocessing/`, `src/training/`, `src/evaluation/`, `src/explainability/` hold reproducible logic; notebooks explore but are not the only executable pipeline. `models/` holds approved versioned artifacts outside ordinary source Git; `app/` contains the lightweight inference API/schema/service boundary; `tests/` validates transforms, artifacts and contracts. These are planned paths, not implemented modules.

Python, scikit-learn-compatible preprocessing and XGBoost primary model are approved. A simple interpretable baseline provides comparison. Package versions, environment tool, artifact format/path, explanation method and serving runtime details remain unresolved. Serialize preprocessing and model together; evaluate reload parity before release. A `.joblib` file is a candidate format, not an existing artifact.

## Producer contract responsibilities

Co-design HS-002 with the backend. AI owns the feature schema, units/missingness/eligibility, target/horizon, score semantics, explanation method and model/pipeline versions. The backend owns authorized input selection and result persistence. Reject unsupported versions/inputs or return a defined unavailable/ineligible result; never invent a score to maintain API success.

Response field names and endpoint paths are unresolved until target validation and contract approval. Candidate metadata includes model identity/version, feature-schema version, target definition/version, preprocessing version, artifact digest and training-data provenance. Do not expose unnecessary patient identity. Internal service authentication/timeouts must be coordinated before deployment.

## Artifact lifecycle

Raw inventory → target feasibility gate → patient/time-safe feature pipeline → baseline and XGBoost evaluation → model card/release decision → trusted serialized artifact → inference parity/contract checks. Only trusted controlled artifacts may be deserialized; verify digest/version and fail closed if missing or incompatible. Do not train on requests or auto-download arbitrary models at startup.

See [dataset strategy](../data/DATASET_STRATEGY.md), [modeling](../ml/MODELING_STRATEGY.md), [model card](../evaluation/MODEL_CARD.md) and [testing](../testing/TESTING_STRATEGY.md).
