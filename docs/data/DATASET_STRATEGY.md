# Synthea dataset strategy

Status: local CSV inventory verified 2026-09-13; no feature dataset or training exists. Raw files remain unchanged. Source role is Synthea-generated structured synthetic EHR for development/experimental prediction; not a medically validated population sample.

## Verified local inventory

CSV record counts exclude the header (quoted/multiline fields parsed with CSV reader).

| File | Rows |
|---|---:|
| `allergies.csv` | 105 |
| `careplans.csv` | 349 |
| `claims.csv` | 9,421 |
| `claims_transactions.csv` | 85,047 |
| `conditions.csv` | 3,517 |
| `devices.csv` | 524 |
| `encounters.csv` | 5,571 |
| `imaging_studies.csv` | 478 |
| `immunizations.csv` | 1,549 |
| `medications.csv` | 3,850 |
| `observations.csv` | 68,648 |
| `organizations.csv` | 278 |
| `patients.csv` | 108 |
| `payer_transitions.csv` | 3,815 |
| `payers.csv` | 10 |
| `procedures.csv` | 15,884 |
| `providers.csv` | 278 |
| `supplies.csv` | 2,225 |

The 108 patient rows are the relevant starting population size; 68,648 observations are repeated records, not 68,648 independent patients. Verify unique IDs, join cardinality, longitudinal coverage, missingness and label prevalence during HS-010 before any modeling. Small subgroups may be unevaluable; report this rather than invent confidence.

## Provenance and preservation

Raw: `data/raw/synthea/`; derived: `data/processed/`. Preserve raw bytes. Record generation version, seed, modules, population parameters, export time, source URL/revision, permitted use and per-file hashes before creating new data. These generation/source details are not established by the local README and remain unresolved. Do not label a new generation equivalent to this sample without evidence. Existing synthetic identifier-like columns must not become inference features or appear in application logs.

## Feature construction requirements

Join patient/encounter/observation/condition data using verified keys. Document each clinical code, unit, timestamp, aggregation window, missingness and inference availability. Exclude identifiers, administrative proxies without justification, target-defining variables and observations after the prediction index time. Separate technical cleaning from target/medical assumptions. Missing data is not a negative outcome or zero.

Split by patient; use temporal constraints appropriate to the outcome horizon. Fit imputation/encoding and any resampling on training partitions only. Prevent the same person's repeated encounters or target events leaking into evaluation. Not every source table belongs in a model. Lifestyle fields shown in the UI must not be assumed available in this data.

## Gate

HS-010 must first approve a feasible outcome, eligible population, index time, horizon, labels and evaluation plan. If the sample cannot support the task, report a no-go and a justified data-generation/reduced-task proposal. No fabricated labels, arbitrary risk bins or clinical-validity claim.
