# Proposed GitHub issues — healthsphere-ai

Status: approved issue-body record, delivered to GitHub on 2026-09-13. The table retains stable project IDs; actual GitHub issue numbers are repository-local. Live issue bodies contain actual dependency and coordination links. Refresh GitHub before creating future issues.

Cross-repository coordination will live in approved GitHub Issues/Project. This file contains only issues proposed for this repository, not a project-wide governance authority. Dependency IDs include their repository below; actual issue links are added only after approved creation. Child membership is not a prerequisite cycle: HS-001 children may start after proposal approval; the coordinator closes after their review/merge evidence. HS-016 preparation may overlap QA, but actual deployment waits for HS-015 and hosting approval.

Labels below already exist; no new labels are proposed. Priority P0 applies to all immediate roadmap items; sizes S/M/L are relative, not delivery-date promises. P1/deferred: medical documents, advanced 7/30-day trend screens, recommendations/progress/timeline expansion, Women's Health, guardian/multi-profile accounts and extended preferences. Guardian/multi-profile remains excluded from MVP and requires a future explicit architecture decision.

| ID | Title | Kind | Dependencies | Labels | Size |
|---|---|---|---|---|---|
| [HS-001-AI](#hs-001-ai) | Repository foundation: ai | implementation | Stage 2 approval | documentation | M |
| [HS-010](#hs-010) | Prediction Target, Preprocessing and XGBoost Prototype | implementation | HS-001-AI | enhancement | L |
| [HS-011](#hs-011) | AI Inference API and Model Provenance | implementation | HS-002, HS-010 | enhancement | M |
| [HS-016-AI](#hs-016-ai) | Deployment readiness: ai | implementation | HS-011 | enhancement | M |

# HS-001-AI

Proposed title: **[HS-001-AI] Repository foundation: ai**

Repository: `HealthSphere-Challenge/healthsphere-ai` · Priority: P0 · Size: M · Labels: `documentation`

## Context

Stage 2 approved the local documentation, skills and support files. Stage 3 created this live issue and authorized the foundation PR; product implementation and PR merge remain outside this stage.

## Objective

Review and deliver the approved Stage 2 foundation in this repository.

## User / Business Value

Keeps approved decisions discoverable and prevents architecture, UX or safety drift.

## Technical Scope

AGENTS, local ADLC, dataset/modeling/inference architecture, untrained model card and testing docs; two skills; update outdated model-selection/current-state README claims and support files.

## Out of Scope

Product runtime/dependencies/endpoints/tables/training/indexing.

## Acceptance Criteria

- [ ] All required repository docs and specialized skills exist with working references.
- [ ] Approved versus proposed/unresolved choices are distinguished; current implementation status is accurate.
- [ ] Existing raw data/design assets preserved byte-for-byte; examples contain no real credentials.
- [ ] Local Stage 2 work is reviewed and merged only through an authorized PR targeting main.

## Testing Requirements

Markdown link audit, skill-creator metadata validation, git diff/whitespace review, ignore/template checks and original-asset checksum preservation.

## Dependencies

- Created under the explicit Stage 3 issue-delivery approval; product implementation still requires a later execution authorization.
- Coordination membership: [HS-001](https://github.com/HealthSphere-Challenge/healthsphere-frontend/issues/2); not a blocking dependency on coordinator closure.

## ADLC Gates

Discovery → Brainstorm → Architecture Check → Plan → Ticket → Development → Unit Tests → Integration / Contract Tests → Self Review → QA → Security / Healthcare Safety → Visual QA when UI → E2E when applicable → PR → CI → Merge decision. Record nonapplicable gates with reasons. Coordination issues gather linked child evidence; they do not duplicate implementation PRs. Documentation-only HS-001 work uses document/skill/hygiene validation rather than nonexistent runtime tests.

## Definition of Done

Acceptance criteria and required checks pass; architecture, scope, documentation and compatibility are reviewed; residual risks are recorded. Applicable lint/typecheck/build and CI pass. Implementation PR targets main and is merged only after an authorized decision. A coordination issue closes only when its linked implementation/release evidence is complete; it needs no artificial code PR. No failing or unrun required check is reported as passed.

# HS-010

Proposed title: **[HS-010] Prediction Target, Preprocessing and XGBoost Prototype**

Repository: `HealthSphere-Challenge/healthsphere-ai` · Priority: P0 · Size: L · Labels: `enhancement`

## Context

Stage 1 found no executable product, tests or CI; Stage 2 authorizes foundation/governance only. This future ticket is not implementation approval.

## Objective

Validate feasibility before creating an experimental reproducible predictive pipeline.

## User / Business Value

Provides a defensible experimental assessment instead of arbitrary health scoring.

## Technical Scope

First establish Python/test/lint/CI foundation and local data audit. Mandatory target gate: outcome/population/index time/horizon/labels/features/evaluation approved before fitting. Then patient/time-safe preprocessing, baseline and XGBoost experiments, model card and limitations. Coordinate target-specific HS-002 schema.

## Out of Scope

Training before target approval, fabricated thresholds/performance, clinical deployment.

## Acceptance Criteria

- [ ] Target feasibility and train/no-go decision recorded before any model fitting.
- [ ] 108-patient limitation, missingness, patient/time leakage and input availability assessed.
- [ ] If feasible, baseline/XGBoost results are measured and reproducible with justified metrics and no clinical-validity claim.
- [ ] If infeasible, report blocked/no-go and seek revised scope; never mark predictive implementation complete using invented labels.

## Testing Requirements

pytest parsing/join/units/missingness and split-leakage tests, deterministic transform checks, measured baseline evaluation, lint/CI and reproducibility audit.

## Dependencies

- `HS-001-AI` — healthsphere-ai

## ADLC Gates

Discovery → Brainstorm → Architecture Check → Plan → Ticket → Development → Unit Tests → Integration / Contract Tests → Self Review → QA → Security / Healthcare Safety → Visual QA when UI → E2E when applicable → PR → CI → Merge decision. Record nonapplicable gates with reasons. Coordination issues gather linked child evidence; they do not duplicate implementation PRs. Documentation-only HS-001 work uses document/skill/hygiene validation rather than nonexistent runtime tests.

## Definition of Done

Acceptance criteria and required checks pass; architecture, scope, documentation and compatibility are reviewed; residual risks are recorded. Applicable lint/typecheck/build and CI pass. Implementation PR targets main and is merged only after an authorized decision. A coordination issue closes only when its linked implementation/release evidence is complete; it needs no artificial code PR. No failing or unrun required check is reported as passed.

# HS-011

Proposed title: **[HS-011] AI Inference API and Model Provenance**

Repository: `HealthSphere-Challenge/healthsphere-ai` · Priority: P0 · Size: M · Labels: `enhancement`

## Context

Stage 1 found no executable product, tests or CI; Stage 2 authorizes foundation/governance only. This future ticket is not implementation approval.

## Objective

Serve only a validated experimental pipeline with traceable semantics.

## User / Business Value

Backend can request reproducible assessments and preserve their meaning over time.

## Technical Scope

Trusted serialized preprocessing+model artifact, digest/version loading, feature/schema validation, lightweight inference API, experimental output and evaluated explanation metadata; serving CI/contracts.

## Out of Scope

Training on requests, clinical claims, arbitrary local explanations or application DB access.

## Acceptance Criteria

- [ ] Artifact reload matches verified pipeline predictions/transforms.
- [ ] Output contains approved target/horizon/model/pipeline/feature provenance and supported explanation semantics.
- [ ] Missing/corrupt/incompatible model and invalid/ineligible inputs fail explicitly without scores.

## Testing Requirements

Serialization/reload parity, schema/contract negative cases, artifact verification, service failure tests, inference smoke and CI.

## Dependencies

- `HS-002` — healthsphere-backend
- `HS-010` — healthsphere-ai

## ADLC Gates

Discovery → Brainstorm → Architecture Check → Plan → Ticket → Development → Unit Tests → Integration / Contract Tests → Self Review → QA → Security / Healthcare Safety → Visual QA when UI → E2E when applicable → PR → CI → Merge decision. Record nonapplicable gates with reasons. Coordination issues gather linked child evidence; they do not duplicate implementation PRs. Documentation-only HS-001 work uses document/skill/hygiene validation rather than nonexistent runtime tests.

## Definition of Done

Acceptance criteria and required checks pass; architecture, scope, documentation and compatibility are reviewed; residual risks are recorded. Applicable lint/typecheck/build and CI pass. Implementation PR targets main and is merged only after an authorized decision. A coordination issue closes only when its linked implementation/release evidence is complete; it needs no artificial code PR. No failing or unrun required check is reported as passed.

# HS-016-AI

Proposed title: **[HS-016-AI] Deployment readiness: ai**

Repository: `HealthSphere-Challenge/healthsphere-ai` · Priority: P0 · Size: M · Labels: `enhancement`

## Context

Stage 1 found no executable product, tests or CI; Stage 2 authorizes foundation/governance only. This future ticket is not implementation approval.

## Objective

Prepare this service for the approved integrated prototype release.

## User / Business Value

The service can be deployed and recovered consistently within its existing boundary.

## Technical Scope

Inference packaging/deployment, trusted artifact distribution/version/digest, internal reachability/auth, health/readiness and rollback notes. Configuration preparation can precede HS-015; actual publication requires passing HS-015 and an explicitly approved hosting/deployment plan.

## Out of Scope

Unapproved publication/spend, new service boundaries or product features.

## Acceptance Criteria

- [ ] Deployed model matches approved artifact/schema; missing/invalid artifact fails safely; no browser-facing bypass.
- [ ] Document verified run/configuration/health/rollback steps with release revisions.
- [ ] Use synthetic demo data and an approved secrets mechanism; no production claims.

## Testing Requirements

Artifact/reload provenance verification, backend inference smoke, failure and rollback check.

## Dependencies

- `HS-011` — healthsphere-ai
- HS-015 (frontend) and approved hosting/publication plan gate actual deployment; configuration preparation may proceed earlier.

## ADLC Gates

Discovery → Brainstorm → Architecture Check → Plan → Ticket → Development → Unit Tests → Integration / Contract Tests → Self Review → QA → Security / Healthcare Safety → Visual QA when UI → E2E when applicable → PR → CI → Merge decision. Record nonapplicable gates with reasons. Coordination issues gather linked child evidence; they do not duplicate implementation PRs. Documentation-only HS-001 work uses document/skill/hygiene validation rather than nonexistent runtime tests.

## Definition of Done

Acceptance criteria and required checks pass; architecture, scope, documentation and compatibility are reviewed; residual risks are recorded. Applicable lint/typecheck/build and CI pass. Implementation PR targets main and is merged only after an authorized decision. A coordination issue closes only when its linked implementation/release evidence is complete; it needs no artificial code PR. No failing or unrun required check is reported as passed.
