# Experimental model card

Status: **not trained, not evaluated, not released**. This card records unknowns rather than fabricated results.

| Field | Current evidence / required decision |
|---|---|
| Intended use | Challenge prototype for informational experimental assessment; not autonomous diagnosis |
| Training source | Local Synthea CSVs; 108 patient rows, 68,648 observations |
| Clinical validity | Not established; no claim permitted |
| Model | XGBoost selected as primary; no fitted artifact |
| Baseline | Simple comparison model to be finalized before training |
| Outcome / horizon / index time | Unresolved; HS-010 target gate |
| Eligible population / exclusions | Unresolved; persona UI is not eligibility evidence |
| Labels / features / units | Unresolved; must be feasible and leakage-reviewed |
| Splits / seed / data hashes | Not generated; patient/time separation required |
| Hyperparameters / dependencies / code revision | Not recorded for any training run |
| Metrics / calibration / subgroup results | Not measured; no placeholder numbers |
| Thresholds / score semantics | Unresolved; must be justified, not copied from mockups |
| Explanation method | Unresolved; global importance is not patient-specific causation |
| Model / pipeline / feature-schema / corpus versions | No released versions |
| Artifact / checksum | None |
| Release decision | Blocked on target validation, measured evaluation, serialization parity and contract tests |

## Known limitations

Small synthetic population, repeated observations and potentially sparse outcomes constrain evaluation. Synthetic results cannot establish clinical validity or population generalization. Availability of lifestyle and clinical variables must be checked against real MVP inputs. Missing data, temporal leakage and administrative proxies can invalidate results.

Complete this card with evidence during HS-010/011, including uncertainty, failed experiments relevant to selection, unsupported populations and residual risk. A no-go decision is preferable to an invented assessment.
