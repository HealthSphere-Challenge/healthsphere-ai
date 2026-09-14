# Model card — hypertension_5y_v1.0.0

## Status

**MODEL SELECTED for experimental HS-011 integration review.** The model is an XGBoost classifier trained and evaluated only on synthetic Synthea records. Selection means the reproducible experimental pipeline passed its integrity gates; it does not establish clinical usefulness or approval.

## Intended use and output

Given information legitimately available about an eligible adult at the first paired-blood-pressure encounter after 365 days of observable history, the model estimates the probability of a first recorded SNOMED-CT `59621000` essential-hypertension event in the following 1,825 days. The index is encounter stop. The output is one probability for `incident_essential_hypertension_5y_v1`, under feature schema `hypertension_features_v1`.

The conceptual runtime flow is: HealthSphere backend → structured `hypertension_features_v1` → frozen preprocessing → XGBoost model → experimental probability → backend assessment. `healthsphere-agent` does not calculate this probability.

## Population and inputs

The eligible population is adults with at least 365 days of observable history, no qualifying hypertension at or before index, a paired BP at index, and either an event inside the horizon or complete event-free follow-up. Early record termination or death without sufficient follow-up is censored.

Required inputs are age in years and paired systolic/diastolic BP in mmHg. Optional inputs are sex at birth, heart rate in bpm, BMI in kg/m², and smoking status. Required missing inputs make inference unavailable. Optional numeric values use medians learned from train plus missing indicators. Optional categorical values use an explicit `unknown` category; the encoder safely ignores other valid unseen runtime categories. Patient identifiers are excluded from prediction.

## Data and provenance

Training uses the reproducibly generated Massachusetts Synthea CSV cohort: requested living population 5,000; exported histories 5,724; deceased 724; patient seed 20260913; clinician seed 20260914; reference date 20260913; default modules. The release asset is labeled Synthea 4.0.0 while internal metadata reports `v3.4.0-18-ga07a65555`; this discrepancy is retained.

The reconstructed labeled cohort has 3,224 patients: 159 positive and 3,065 negative (4.93%). The deterministic patient-level stratified split uses seed 20260915:

| Partition | Patients | Positive | Negative | Prevalence |
|---|---:|---:|---:|---:|
| Train | 2,256 | 111 | 2,145 | 4.92% |
| Validation | 484 | 24 | 460 | 4.96% |
| Test | 484 | 24 | 460 | 4.96% |

All preprocessing and class weights were fitted from train only. Model family, hyperparameters, threshold, and calibration policy were frozen from train/validation before test was evaluated once.

## Model comparison and selection

Validation PR-AUC was the primary metric. Dummy PR-AUC was 0.0496, class-weighted logistic regression was 0.0807, and the selected XGBoost configuration was 0.1174. XGBoost exceeded logistic regression by 0.0367, passing the predeclared 0.02 parsimony margin. Its validation ROC-AUC was 0.6944. Eight bounded XGBoost configurations were evaluated. The selected parameters and complete validation evidence are in `artifacts/hypertension_5y/v1/metrics.json`.

The evaluation threshold `0.6089538335800171` maximized validation F1. It is an experimental evaluation threshold and is not a clinical cutoff. No calibrator was fitted because validation contained only 24 positives; fitting and assessing a flexible calibration layer on that same small partition would provide weak evidence.

## Held-out synthetic test results

| Metric | Result |
|---|---:|
| PR-AUC | 0.1562 |
| ROC-AUC | 0.6287 |
| Brier score | 0.2128 |
| Sensitivity | 0.2917 |
| Specificity | 0.8239 |
| Precision | 0.0795 |
| F1 | 0.1250 |

At the frozen threshold the confusion matrix was TN 379, FP 81, FN 17, TP 7. The high Brier score and reliability bins show substantial probability overestimation. This limits interpretation of the probability and must remain visible during HS-011 review.

A deterministic patient-level stratified bootstrap used 2,000 replicates and seed 20260916. The 95% interval was 0.0594–0.2982 for PR-AUC and 0.5220–0.7287 for ROC-AUC. Sensitivity was 0.1250–0.4583 and precision was 0.0337–0.1304. These wide intervals reflect only 24 positive test cases.

## Explainability and subgroup analysis

Global native XGBoost gain importance is serialized in the metrics report. It describes feature influence inside this model; it is not a causal statement or a patient-specific explanation. SHAP was not added because it was unnecessary for this small prototype and would add dependency and interpretation costs.

Sex and broad-age test subgroup results are descriptive synthetic evidence only. Female and male groups each contain 12 positives. The 18–39 and 40–64 groups contain 12 and 11 positives; the 65+ group contains one and is explicitly insufficient. No real-world fairness conclusion is supported.

## Limitations and prohibited use

BP-conditioned indexing selects patients whose BP was measured and creates healthcare-capture and measured-patient selection effects. The target is a first *recorded* diagnosis, which depends on synthetic care and coding patterns. Censoring depends on record coverage. Synthea generation artifacts may produce associations unlike real patients. Prevalence, calibration, subgroup behavior, and performance have not been validated on external or real-world data. The held-out evidence is imprecise and the probabilities are poorly calibrated.

This model must not be used for diagnosis, treatment decisions, emergency triage, or clinical decision-making. It is not a medical device, treatment recommender, current-hypertension screener, or emergency system.

## Reproduction and artifacts

Run:

```bash
uv run python scripts/train_hypertension_model.py data/raw/synthea_5000_reproducible/csv
```

Artifacts are under `artifacts/hypertension_5y/v1/`: native XGBoost `model.json`, `preprocessing.joblib`, `metadata.json`, `metrics.json`, and the synthetic-patient split manifest. Metadata records versions, hashes, seeds, provenance, schema, threshold, and primary metrics. Serialization reload parity passed.
