# Modeling and reproducibility strategy

Approved scope: experimental health-risk prototype, no clinical-validity claim. XGBoost is primary; a simple baseline such as Logistic Regression is proposed for comparison. No model has been trained.

## Mandatory target gate before training

Record a justified outcome, population/inclusion criteria, index time, prediction horizon, available labels and features, missingness/censoring, prevalence and patient counts. Distinguish prediction of a future event from recognizing an already recorded condition. Validate that required inference inputs are actually obtainable through the MVP. Check target leakage and label construction against the intended use. Clinical references/thresholds require evidence and review; no arbitrary low/moderate/high labels.

Approve the target and evaluation plan in HS-010 before fitting any baseline or XGBoost model. If unsupported by 108 patient records, stop training and present the limitation plus a scoped alternative/data-generation proposal. No synthetic claims of performance or clinical recommendations.

## Preprocessing and training

Create patient-separated train/validation/test partitions with temporal restrictions appropriate to the task. Record IDs/seeds/split manifest securely as synthetic development artifacts. Fit all imputers, encoders, selection and resampling on training only. Represent missingness intentionally; avoid gratuitous scaling or transformations. Keep the exact feature order, categories, units and inference transforms in a scikit-learn-compatible pipeline.

Use validation for tuning and threshold decisions; keep held-out test data out of tuning. Choose tuning budget and metrics according to sample size. Record commands, code revision, dependency lock, seeds, data hashes, feature/target versions, split identifiers and hyperparameters. Report nondeterminism that remains; a fixed seed alone is not full reproducibility.

## Evaluation and explanation

For an approved classification task, consider recall/sensitivity, precision, F1, ROC-AUC/PR-AUC, confusion matrix and calibration where estimable. Report undefined metrics and sample counts. Compare baseline and XGBoost, examine subgroup limitations without claiming reliable fairness estimates from tiny groups. No arbitrary acceptance thresholds; agree them in the target/evaluation plan.

Explain only what the selected method supports. Global feature importance describes model-wide influence, not a specific person's causal drivers. Patient-level explanations need an evaluated local method; SHAP is optional, not an excuse to invent percentages. Predictions/explanations remain experimental and communicate uncertainty.

## Release and serialization

Freeze preprocessing and model as one trusted artifact with metadata/digest. Verify identical transformation and prediction behavior after reload on known fixtures. Record model card, target/horizon, population limitations, measured metrics, versions and feature schema. Serve only approved artifacts; preserve historical model identity so stored assessments remain interpretable. Do not manufacture a fallback score if loading or validation fails.
