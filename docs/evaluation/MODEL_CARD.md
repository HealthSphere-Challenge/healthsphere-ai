# Experimental incident essential-hypertension model card

**Status: approved specification; not trained, evaluated, released, or clinically validated.**

## Intended use

The planned model estimates an experimental probability of a first recorded SNOMED-CT essential-hypertension event within five years for a Synthea-like adult who has at least one year of observable history and a qualifying paired blood-pressure encounter. It is an informational challenge prototype. It is not a diagnosis, current-state classifier, treatment recommender, emergency triage system, or substitute for medical judgment.

## Frozen target and population

Target `incident_essential_hypertension_5y_v1` uses SNOMED-CT `59621000`. The index is the stop day of the first adult encounter, after 365 days of observable history, containing paired systolic and diastolic observations. Existing target records on or before index exclude the patient. An event must occur strictly after index and within 1,825 days. Event-free records need the full horizon; earlier death or record end is censored.

## Dataset provenance

Training is planned only on the reproducible Massachusetts Synthea cohort requested as 5,000 living people and exported as 5,724 histories, including 724 deceased. The release asset is labeled 4.0.0 while generated metadata reports `v3.4.0-18-ga07a65555`; both facts must remain in model metadata. Seeds, command, date, checksum, and Java requirements are in [the provenance record](../data/SYNTHEA_5000_PROVENANCE.md).

Synthetic data does not demonstrate clinical validity, real-population generalization, fairness, or operational reliability.

## Planned features

Schema `hypertension_features_v1` contains age, sex at birth, paired systolic/diastolic blood pressure, heart rate, backend-derived BMI, and smoking status. Every value is available on or before index and maps to a current HealthSphere profile or measurement field. Administrative identifiers, future data, target-derived data, weight redundancy, glucose sparsity, and unmapped history codes are excluded.

## Evaluation plan

Stage 9 must compare a prevalence dummy classifier, class-weighted logistic regression, and XGBoost on one deterministic stratified 70/15/15 patient split. PR-AUC is primary. Report prevalence, confusion matrix, sensitivity, specificity, precision, F1, ROC-AUC, PR-AUC, Brier score, calibration curve, and patient-level bootstrap confidence intervals. Imputation, encoding, class weights, calibration, and threshold choice use training/validation only. The untouched test set is evaluated once for the final report.

## Known limitations and prohibited uses

The selected cohort is conditioned on a blood-pressure encounter and excludes censored negative histories, creating healthcare-capture and survivor selection effects. Only about 24 positive cases are expected in each validation/test partition, so interval estimates will be wide. Synthea sex values contain only female/male mappings, leaving the runtime `unknown` category without training examples. First recorded diagnosis is a documentation event rather than proven biological onset.

Do not use the future model for diagnosis, treatment, emergency decisions, autonomous clinical action, real-world care, or claims of medical reliability. No performance value may be added until Stage 9 measures it under the frozen protocol.
