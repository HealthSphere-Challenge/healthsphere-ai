# AI testing and evaluation strategy

Status: no runner, model or CI exists. HS-010 includes the AI environment/testing/CI foundation before modeling; HS-011 adds serving checks.

- pytest unit tests: parsing and join cardinality, units, missingness, unsupported categories, feature ordering, deterministic transforms and schema validation.
- Leakage tests: no patient overlap across splits, no prohibited future/outcome features, fitted preprocessing derived only from training partitions.
- Pipeline integration: serialization/reload parity, metadata/digest verification, supported dependency/feature versions, clear failure on absent/corrupt/untrusted artifacts.
- Inference contracts: AI owns Pydantic producer/consumer schemas and backend checks synthetic consumer fixtures. Cover schema version, UUID/request correlation, valid/missing/invalid/ineligible/unavailable states, provenance, nullability, canonical errors, timeout, and malformed responses. No fifth contract repository and no fabricated completed-result fixture before HS-010.
- Evaluation: approved target-specific metrics, sample counts, calibration where feasible, baseline comparison, small-subgroup limitations, reproducible run record and release decision.
- Security: no raw sensitive identifiers in logs, bounded inference requests, controlled artifact deserialization, dependency/secret scanning when CI tooling exists.

CI minimum: reproducible Python 3.13 install with `uv`, lint, pytest, preprocessing/schema checks and lightweight artifact/contract tests. Large training runs are explicit experiments, not mandatory on every PR. Store small approved synthetic fixtures; generated datasets/model binaries are ignored by default and versioned with a deliberate artifact strategy. Exact commands, packages and workflow versions are unresolved until HS-010.

Passing schema tests is not model validity. HS-015 reviews release evidence across the actual backend integration. Stage 2 runs only documentation/skill/inventory preservation checks.
