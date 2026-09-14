# HS-010 ML readiness and frozen training specification

**Decision: HS-010 = APPROVED FOR TRAINING.** This authorizes Stage 9 experimentation under the frozen specification; it does not approve clinical use, deployment, or any model artifact. No model or preprocessor was fitted in Stage 8.

## Prediction question and target

Given information legitimately available about an eligible adult at the index encounter, estimate the experimental probability of a first recorded essential-hypertension event within the following five years. This predicts a future recorded event. It does not diagnose hypertension or classify the patient's current state.

Target `incident_essential_hypertension_5y_v1` is the first SNOMED-CT `59621000` condition record strictly after index and no later than index + 1,825 days. Records at or before index exclude the patient. Duplicate qualifying rows reduce to the earliest date; the generated cohort contains no hypertension duplicates. Event-free patients are negative only with complete encounter capture through the horizon. Death/record end before the horizon is censored unless a qualifying event was already observed. The index uses encounter stop, correcting four prior same-encounter records that the earlier start-day audit counted as incident.

## Why the prior index failed

Strategy A selected the earliest adult wellness encounter after a year of history while also looking ahead five years to require follow-up. Synthea's vital bundle generally occurs much later: all 4,162 Strategy-A patients had a later BP, with a median delay of 7,808.5 days. The sparse fields were not independent: BP, heart rate, weight, BMI, and smoking appeared for the same 337 eligible people.

Every relevant observation is encounter-linked. Under Strategy C, 29,822 audited feature rows occurred within the linked index encounter and none fell outside its start/stop dates. Qualifying encounter classes were 4,167 wellness, 276 outpatient, 130 urgent-care, 31 emergency, and 7 ambulatory. This supports encounter-aware indexing rather than a code-extraction correction. The root cause is an inappropriate early index combined with encounter-bundled Synthea measurements; it is not genuine independent missingness.

## Index comparison

All strategies require age 18 and 365 days since first encounter. The fixed lookback is `[index − 365 days, index]`, selecting the latest eligible observation. Same-encounter observations are allowed only because index is encounter stop and all audited observations occur within that encounter.

| Strategy | Definition | Eligible | Positive | Negative | Prevalence | Median follow-up | Complete cases | Positive complete | Assessment |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| A | First adult wellness after history, with future five-year capture | 4,072 | 92 | 3,980 | 2.26% | 29.92 y | 337 | 7 | Reject: future-conditioned index and obsolete pre-vital timing |
| B | First adult encounter after history; censor incomplete negatives | 4,125 | 89 | 4,036 | 2.16% | 28.73 y | 301 | 6 | Reject: valid timing, unusably sparse features |
| C | First adult encounter after history containing paired BP | 3,224 | 159 | 3,065 | 4.93% | 9.14 y | 3,213 | 159 | Select: prospective current-encounter trigger; narrower measured cohort |

Strategy C indexes 4,611 patients before target/prior/censor filters. For hypertension, 939 have target at/before index and 448 event-free histories are censored. Only one positive occurs within 30 days, four within one year, and the median event delay is 1,099 days, reducing concern that the label captures immediate same-encounter coding.

## Feature availability and runtime mapping

Availability uses the 3,224 labeled Strategy-C hypertension patients.

| Feature | Training source/code | Unit | Available | Missing | Runtime mapping | Status / risk |
|---|---|---|---:|---:|---|---|
| Age | `patients.BIRTHDATE` | years | 100% | 0% | Profile DOB → elapsed years | Required; low risk |
| Sex at birth | `patients.GENDER` | category | 100% | 0% | Profile; F/M → female/male, other/null → unknown | Optional; unknown distribution gap |
| Systolic BP | LOINC `8480-6` | `mm[Hg]` → mmHg | 100% | 0% | Latest paired BP | Required; index-defining |
| Diastolic BP | LOINC `8462-4` | `mm[Hg]` → mmHg | 100% | 0% | Same paired BP | Required; index-defining |
| Heart rate | LOINC `8867-4` | `/min` → bpm | 99.94% | 0.06% | Latest heart rate | Optional; low risk |
| BMI | LOINC `39156-5` | kg/m2 | 99.66% | 0.34% | Backend-derived height + weight | Optional/derivable |
| Smoking | LOINC `72166-2` | category | 99.66% | 0.34% | Profile never/former/current/unknown | Optional; low risk |
| Weight | LOINC `29463-7` | kg | 99.66% | 0.34% | Runtime available | Excluded as redundant with BMI |
| Blood glucose | LOINC `2339-0`, `2345-7` | mg/dL | 41.28% | 58.72% | Latest glucose | Excluded for sparse capture |
| Sleep/activity | No matching rows | minutes | 0% | 100% | Runtime fields exist | Excluded; unavailable in training |
| Prior conditions | `conditions.csv` | codes | Not frozen | Not frozen | Structured history | Excluded; crosswalk/leakage unresolved |

No clinical range filter is frozen. Parsing requires numeric types and canonical units; clinical plausibility needs separate review.

## Missingness, leakage, and split

Age and paired BP are eligibility requirements and are never imputed. Optional numeric fields use training-fold median imputation plus missing indicators. Optional categories use an explicit `unknown` category. Missing never means zero, no value is invented in Stage 8, and complete-case deletion is prohibited. All learned transformations fit on training only.

The machine-readable blacklist excludes patient/encounter/claim IDs, target at/before index, every post-index observation/condition/medication/procedure/encounter/claim/complication, outcome-derived fields, record end, and follow-up duration. Extraction enforces `feature_timestamp <= index`.

Split once by patient with seed `20260915`, stratified 70/15/15. Expected positive allocation is approximately 111/24/24. Row-level splits and patient overlap are forbidden. Validation selects settings and threshold; test remains untouched until final evaluation.

## Evaluation and uncertainty

Compare `DummyClassifier(strategy=prior)`, class-weighted logistic regression, and XGBoost. Derive `scale_pos_weight` from training only; do not use SMOTE by default. PR-AUC is primary. Also report prevalence, confusion matrix, sensitivity, specificity, precision, F1, ROC-AUC, Brier score, and calibration curve. Select any operating threshold on validation under a predeclared sensitivity/precision utility.

With only about 24 positives in validation and test, estimates will be unstable. Stage 9 must report patient-level stratified bootstrap 95% confidence intervals, undefined metrics, and interval width rather than treating point estimates as definitive.

## Alternative targets

At Strategy C, obesity has 1,950 eligible patients, 277 positives (14.21%), and 1,935 complete cases. Its stronger count is outweighed by circularity: Synthea obesity findings are closely tied to BMI/weight, so a model risks recognizing current obesity awaiting documentation. Hypertension retains better product alignment and only 1/159 events within 30 days. Type 2 diabetes rises to 64/3,883 (1.65%) but yields only about ten test positives and remains rejected.

## Readiness gates

| Gate | Status | Evidence |
|---|---|---|
| A Target | PASS | Versioned SNOMED event, prior exclusion, horizon, censoring |
| B Cohort | PASS | Deterministic prospective Strategy C |
| C Positive count | PASS | 159 experimental events; mandatory uncertainty plan |
| D Features | PASS | Required 100%; optional ≥99.66% |
| E Runtime compatibility | PASS | Every v1 feature maps to profile/measurements |
| F Missingness | PASS | Required/optional policy and train-only transforms |
| G Leakage | PASS | Explicit blacklist and temporal extraction |
| H Split | PASS | Deterministic stratified patient 70/15/15 |
| I Evaluation | PASS | Imbalance, calibration, uncertainty protocol frozen |
| J Reproducibility | PASS | Generator, module, evidence JSON, tests, lockfile |

## Reproduction and artifact plan

Run `uv run python scripts/analyze_ml_readiness.py data/raw/synthea_5000_reproducible/csv`. The pipeline performs raw load → eligibility/index → target labeling/censoring → feature availability → leakage-safe evidence. The JSON is evidence only; no split, preprocessing, or model is fitted.

Stage 9 artifacts belong under `artifacts/hypertension_5y/v1/` as `model.json`, `preprocessing.joblib`, `metadata.json`, and `metrics.json`. Metadata binds target, feature schema, split, data/code/dependencies, provenance discrepancy, and digests. Do not create them until Stage 9.

The authoritative structured specification is [`specs/hypertension_5y_v1.json`](../../specs/hypertension_5y_v1.json). Generated raw cohorts remain ignored by Git.
