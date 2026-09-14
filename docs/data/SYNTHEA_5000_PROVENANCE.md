# Synthea 5,000 cohort provenance

- Generator: asset downloaded from the Synthea 4.0.0 GitHub release; its generated metadata reports internal build `v3.4.0-18-ga07a65555`, a release-packaging discrepancy retained explicitly rather than hidden
- Population request: 5,000 living patients (export may also contain deceased patients generated en route)
- Seed: `20260913`
- Clinician seed: `20260914`
- Reference/end date: `20260913`
- Geography: Massachusetts, United States
- Modules: Synthea 4.0.0 defaults; no module override
- Formats: CSV enabled; FHIR, C-CDA, and text disabled
- Generation date: 2026-09-13
- Requirements: Java 17 or newer, Bash, curl, approximately 10 GB free disk space
- Command: `./scripts/generate_synthea_5000.sh`
- Local output: `data/raw/synthea_5000_reproducible/csv/` (ignored by Git)
- Downloaded JAR SHA-256: `ed43c20ad40ba5c3bc724503a5af032715fe3c491620b766148e7c2361e6ecc1`
- Export result: 5,724 patient histories (5,000 alive, 724 deceased), 16 generator threads, 330 seconds
- Deterministic feasibility-report SHA-256: `218c780a655541e814432c152aefa23e61c0a750a1c2c8926e69bf21db01fa8f`

The Phase 0 files remain unchanged at `data/raw/synthea/`. The generated files are deliberately excluded from Git because they are reproducible and too large for normal source control. The script pins the release URL, population, seed, geography, and exporter flags. A future production-quality artifact store should also verify a published release checksum; GitHub does not publish one beside this release asset.
