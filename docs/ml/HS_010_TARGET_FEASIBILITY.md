# HS-010 target and feature feasibility decision

**Historical Stage 6 status: BLOCKED.** This report preserves the earlier evidence and is superseded by the approved Stage 8 readiness specification in [HS-010 ML readiness](HS_010_ML_READINESS.md).

## Method

The reproducible Synthea release cohort contains 5,724 exported patient histories (5,000 alive at generation end and 724 deceased). The audit selects the first adult wellness encounter after at least one year of observable history and requires five years of subsequent encounter history. Measurements on that wellness date are eligible; later data is forbidden. Patients with the target recorded on or before index are excluded. This produces 4,162 indexed adults. The rule is useful for feasibility, but selecting patients by known future follow-up introduces a research-cohort selection effect that must be replaced by a censoring-aware policy before modeling.

## Candidate definitions and results

| Target | Code/event set | Eligible N | Positive | Negative | Prevalence | Decision |
|---|---|---:|---:|---:|---:|---|
| Incident essential hypertension | SNOMED CT `59621000` after index and within five years | 4,076 | 96 | 3,980 | 2.36% | Preferred product target; label split is feasible but features gate training |
| Incident obesity finding | SNOMED CT `162864005` or `408512008` after index and within five years | 3,831 | 424 | 3,407 | 11.07% | Second-best; easier label balance but vulnerable to BMI circularity |
| Incident type 2 diabetes | SNOMED CT `44054006` after index and within five years | 4,146 | 10 | 4,136 | 0.24% | Rejected for this cohort due to too few positives |

For every candidate, a negative has no target event through the full five-year horizon. Earlier target events exclude the patient. Patients without the required horizon are censored out. A future implementation must test whether death, record termination, and healthcare capture make this exclusion systematically biased.

## Feature quality before index

Demographics are available for all 4,162 indexed adults. A prior condition record exists for 3,927 (94.35%), although no record cannot distinguish absence from missing capture. In the one-year lookback including the index wellness date, heart rate, systolic/diastolic blood pressure, weight, BMI, and smoking are available for 337 (8.10%); glucose for 7 (0.17%); activity and sleep for none. Units are internally consistent in observed rows: `/min`, `mm[Hg]`, `kg`, `kg/m2`, and `mg/dL`. No values fell outside the audit's broad technical ranges. Smoking is categorical with a blank unit. These ranges are data-quality screens, not clinical thresholds.

The leakage blacklist contains target diagnoses on/before index, all post-index encounters and measurements, target-derived codes, target complications, medications started after the target, future claims, patient identifiers, and administrative IDs. For obesity, index BMI and weight can turn prediction into near-recognition; they require a clinically reviewed exclusion or distance-from-threshold policy. No imputation is performed.

## Recommendation and split design

Essential hypertension is preferred because it matches HealthSphere's longitudinal measurement product and has enough events for an exploratory patient-level split, despite lower prevalence than obesity. A provisional stratified 70/15/15 split would contain roughly 67/14/15 positive patients; exact split generation waits for target approval. Obesity is second because it has stronger statistical support, but its label is generated from BMI and risks circularity with the most relevant features. Type 2 diabetes is rejected for this generation.

Training remains a no-go. Only 8% of indexed adults have core vitals under this index policy, while glucose, activity, and sleep are effectively absent. Before training, approve the hypertension target and either revise the operational index/capture rules without using future information, configure a Synthea generation that provides realistic pre-index vitals, or narrow the MVP feature contract. No XGBoost, preprocessing fit, split artifact, model metric, or serialized model was created.
