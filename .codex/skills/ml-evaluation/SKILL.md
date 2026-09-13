---
name: ml-evaluation
description: "Review experimental HealthSphere model evidence, explanation validity and release provenance."
---

# Ml Evaluation

Read the active approved ticket and relevant repository instructions first. This skill does not expand authorization.

- [Model Card](../../../docs/evaluation/MODEL_CARD.md)
- [Modeling Strategy](../../../docs/ml/MODELING_STRATEGY.md)
- [Testing Strategy](../../../docs/testing/TESTING_STRATEGY.md)

## Workflow

Check target and split validity before interpreting metrics. Compare XGBoost against the approved baseline; report sample counts, undefined metrics, calibration where feasible and small-subgroup limits. Confirm test data was not used for tuning. Match explanation claims to the method: global importance is not a patient-specific causal contribution. Verify artifact digest/version, schema compatibility and reload parity. Update the model card with measured results or explicit unknowns; never claim clinical validity or promote a missing/failed model.
