---
name: ml-engineering
description: "Develop approved Synthea preprocessing and XGBoost experiments without target leakage or inference drift."
---

# Ml Engineering

Read the active approved ticket and relevant repository instructions first. This skill does not expand authorization.

- [Dataset Strategy](../../../docs/data/DATASET_STRATEGY.md)
- [Modeling Strategy](../../../docs/ml/MODELING_STRATEGY.md)

## Workflow

Verify target, population, index time, horizon, labels and evaluation plan are approved before fitting any model. Inspect actual patient counts, joins, feature availability and missingness. Preserve raw data and prevent patient/time/outcome leakage; fit transforms only on training data. Record data/code/dependency/split/seed versions and build a scikit-learn-compatible pipeline. If data cannot support the target, stop training and report a no-go rather than fabricate labels. Serialize only after measured evaluation and verify reload parity.
