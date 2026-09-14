#!/usr/bin/env python3
# ruff: noqa: E501
"""Run the official frozen HS-010 experiment and write versioned evidence."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
import sklearn
import xgboost
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from healthsphere_ai.cohort import build_hypertension_cohort, load_dataset  # noqa: E402
from healthsphere_ai.training import (  # noqa: E402
    FEATURE_ORDER,
    SPLIT_SEED,
    bootstrap_metrics,
    calibration_bins,
    classification_metrics,
    dump_preprocessor,
    make_preprocessor,
    matrix,
    select_f1_threshold,
    split_patients,
    validate_rows,
    write_json,
    write_split_manifest,
)

MODEL_VERSION = "hypertension_5y_v1.0.0"
ARTIFACT_DIR = Path("artifacts/hypertension_5y/v1")
REPORT_PATH = Path("docs/evaluation/HS_010_MODEL_EVALUATION.md")
EXPECTED = (3224, 159, 3065)


def _git_revision() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _subset(values: np.ndarray, indexes: list[int]) -> np.ndarray:
    return values[np.asarray(indexes)]


def _counts(y: np.ndarray, indexes: list[int]) -> dict[str, int | float]:
    selected = _subset(y, indexes)
    positives = int(selected.sum())
    return {
        "n": len(indexes),
        "positive_n": positives,
        "negative_n": len(indexes) - positives,
        "prevalence": float(selected.mean()),
    }


def _fit_and_score(
    model, x_train, y_train, x_validation, y_validation
) -> tuple[Pipeline, np.ndarray]:
    pipeline = Pipeline([("preprocessing", make_preprocessor()), ("model", model)])
    pipeline.fit(x_train, y_train)
    return pipeline, pipeline.predict_proba(x_validation)[:, 1]


def _subgroups(rows, indexes, y, probabilities, threshold):
    selected_rows = [rows[index] for index in indexes]
    groups = {}
    definitions = {
        "sex_at_birth": lambda row: str(row.features["sex_at_birth"]),
        "age_group": lambda row: "18-39"
        if row.features["age_years"] < 40
        else ("40-64" if row.features["age_years"] < 65 else "65+"),
    }
    for dimension, accessor in definitions.items():
        groups[dimension] = {}
        for value in sorted({accessor(row) for row in selected_rows}):
            positions = np.array(
                [position for position, row in enumerate(selected_rows) if accessor(row) == value]
            )
            group_y = y[positions]
            record = {"n": int(len(positions)), "positive_n": int(group_y.sum())}
            if len(positions) >= 30 and len(np.unique(group_y)) == 2 and group_y.sum() >= 5:
                record["metrics"] = classification_metrics(
                    group_y, probabilities[positions], threshold
                )
                record["evidence"] = "descriptive synthetic subgroup only"
            else:
                record["metrics"] = None
                record["evidence"] = "insufficient evidence"
            groups[dimension][value] = record
    return groups


def main() -> None:
    source = Path(sys.argv[1] if len(sys.argv) > 1 else "data/raw/synthea_5000_reproducible/csv")
    if not source.is_dir():
        raise SystemExit(f"Approved Synthea cohort is absent: {source}")
    rows = build_hypertension_cohort(load_dataset(source))
    validate_rows(rows)
    positives = sum(row.target for row in rows)
    observed = (len(rows), positives, len(rows) - positives)
    if observed != EXPECTED:
        raise SystemExit(f"Cohort changed materially: expected {EXPECTED}, observed {observed}")

    split = split_patients(rows)
    patient_sets = [
        {rows[index].patient_id for index in indexes}
        for indexes in (split.train, split.validation, split.test)
    ]
    if any(patient_sets[left] & patient_sets[right] for left, right in ((0, 1), (0, 2), (1, 2))):
        raise SystemExit("Patient overlap detected")
    x = matrix(rows)
    y = np.asarray([row.target for row in rows])
    x_train, y_train = _subset(x, split.train), _subset(y, split.train)
    x_validation, y_validation = _subset(x, split.validation), _subset(y, split.validation)

    dummy, dummy_probabilities = _fit_and_score(
        DummyClassifier(strategy="prior"), x_train, y_train, x_validation, y_validation
    )
    logistic, logistic_probabilities = _fit_and_score(
        LogisticRegression(class_weight="balanced", C=1.0, max_iter=2000, random_state=SPLIT_SEED),
        x_train,
        y_train,
        x_validation,
        y_validation,
    )
    scale_pos_weight = float((len(y_train) - y_train.sum()) / y_train.sum())
    search_space = [
        {
            "n_estimators": n,
            "max_depth": d,
            "learning_rate": lr,
            "min_child_weight": m,
            "subsample": s,
            "colsample_bytree": c,
            "reg_alpha": a,
            "reg_lambda": 1.0,
        }
        for n, d, lr, m, s, c, a in [
            (100, 2, 0.03, 1, 1.0, 1.0, 0.0),
            (150, 2, 0.05, 1, 0.9, 0.9, 0.0),
            (200, 2, 0.05, 3, 0.9, 1.0, 0.1),
            (100, 3, 0.05, 1, 1.0, 0.9, 0.0),
            (150, 3, 0.03, 3, 0.9, 0.9, 0.1),
            (200, 3, 0.03, 5, 0.8, 0.9, 0.1),
            (100, 4, 0.03, 3, 0.9, 0.8, 0.5),
            (150, 4, 0.02, 5, 0.8, 0.8, 0.5),
        ]
    ]
    search_results = []
    candidates = []
    for parameters in search_space:
        model = XGBClassifier(
            **parameters,
            objective="binary:logistic",
            eval_metric="logloss",
            scale_pos_weight=scale_pos_weight,
            random_state=SPLIT_SEED,
            n_jobs=1,
            tree_method="hist",
        )
        pipeline, probabilities = _fit_and_score(
            model, x_train, y_train, x_validation, y_validation
        )
        threshold = select_f1_threshold(y_validation, probabilities)
        metrics = classification_metrics(y_validation, probabilities, threshold)
        search_results.append({"parameters": parameters, "validation": metrics})
        candidates.append((metrics["pr_auc"], parameters, pipeline, probabilities))
    candidates.sort(key=lambda item: item[0], reverse=True)
    _, xgb_parameters, xgb_pipeline, xgb_probabilities = candidates[0]

    validation_probabilities = {
        "dummy": dummy_probabilities,
        "logistic_regression": logistic_probabilities,
        "xgboost": xgb_probabilities,
    }
    validation = {}
    for name, probabilities in validation_probabilities.items():
        candidate_threshold = select_f1_threshold(y_validation, probabilities)
        validation[name] = classification_metrics(y_validation, probabilities, candidate_threshold)
        validation[name]["calibration_curve"] = calibration_bins(y_validation, probabilities)

    # Predeclared parsimony rule: XGBoost must improve validation PR-AUC by >0.02.
    selected_name = (
        "xgboost"
        if validation["xgboost"]["pr_auc"] > validation["logistic_regression"]["pr_auc"] + 0.02
        else "logistic_regression"
    )
    selected_pipeline = xgb_pipeline if selected_name == "xgboost" else logistic
    selected_probabilities = validation_probabilities[selected_name]
    threshold = select_f1_threshold(y_validation, selected_probabilities)
    calibration_policy = (
        "none; validation evidence did not justify fitting a calibrator with only 24 positives"
    )

    # The untouched test partition is accessed for the first and only model evaluation here.
    x_test, y_test = _subset(x, split.test), _subset(y, split.test)
    test_probabilities = selected_pipeline.predict_proba(x_test)[:, 1]
    test_metrics = classification_metrics(y_test, test_probabilities, threshold)
    test_metrics["calibration_curve"] = calibration_bins(y_test, test_probabilities)
    uncertainty = bootstrap_metrics(y_test, test_probabilities, threshold)
    subgroup = _subgroups(rows, split.test, y_test, test_probabilities, threshold)

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    preprocessor = selected_pipeline.named_steps["preprocessing"]
    model = selected_pipeline.named_steps["model"]
    dump_preprocessor(ARTIFACT_DIR / "preprocessing.joblib", preprocessor)
    model_path = ARTIFACT_DIR / ("model.json" if selected_name == "xgboost" else "model.joblib")
    if selected_name == "xgboost":
        model.save_model(model_path)
    else:
        joblib.dump(model, model_path)
    write_split_manifest(ARTIFACT_DIR / "split_manifest.json", rows, split)

    transformed = preprocessor.transform(x_test)
    reloaded_preprocessor = joblib.load(ARTIFACT_DIR / "preprocessing.joblib")
    if selected_name == "xgboost":
        reloaded_model = XGBClassifier()
        reloaded_model.load_model(model_path)
    else:
        reloaded_model = joblib.load(model_path)
    reloaded_probabilities = reloaded_model.predict_proba(reloaded_preprocessor.transform(x_test))[
        :, 1
    ]
    if not np.allclose(test_probabilities, reloaded_probabilities, rtol=1e-12, atol=1e-12):
        raise SystemExit("Artifact reload parity failed")
    if transformed.shape[0] != len(y_test):
        raise SystemExit("Preprocessing output cardinality changed")

    if selected_name == "xgboost":
        names = preprocessor.get_feature_names_out().tolist()
        explainability = {
            "method": "native XGBoost gain importance",
            "scope": "global model influence; neither causal nor patient-specific",
            "feature_importance": dict(
                sorted(
                    zip(names, model.feature_importances_.tolist(), strict=True),
                    key=lambda item: item[1],
                    reverse=True,
                )
            ),
        }
        hyperparameters = xgb_parameters | {
            "scale_pos_weight": scale_pos_weight,
            "random_state": SPLIT_SEED,
        }
    else:
        names = preprocessor.get_feature_names_out().tolist()
        explainability = {
            "method": "logistic regression coefficients on the transformed feature scale",
            "scope": "model associations; neither causal nor patient-specific",
            "coefficients": dict(zip(names, model.coef_[0].tolist(), strict=True)),
        }
        hyperparameters = {
            "class_weight": "balanced",
            "C": 1.0,
            "max_iter": 2000,
            "random_state": SPLIT_SEED,
        }

    metrics = {
        "dataset": {
            "n": len(rows),
            "positive_n": positives,
            "negative_n": len(rows) - positives,
            "prevalence": positives / len(rows),
        },
        "split": {
            name: _counts(y, indexes)
            for name, indexes in (
                ("train", split.train),
                ("validation", split.validation),
                ("test", split.test),
            )
        },
        "validation": validation,
        "hyperparameter_search": search_results,
        "selection": {
            "model": selected_name,
            "rule": "highest validation PR-AUC; prefer logistic unless XGBoost improves by more than 0.02",
            "threshold_objective": "maximum validation F1",
            "threshold": threshold,
            "calibration_policy": calibration_policy,
        },
        "test": test_metrics,
        "bootstrap": uncertainty,
        "subgroups": subgroup,
        "explainability": explainability,
    }
    write_json(ARTIFACT_DIR / "metrics.json", metrics)
    metadata = {
        "model_version": MODEL_VERSION,
        "target_id": "incident_essential_hypertension_5y_v1",
        "feature_schema_version": "hypertension_features_v1",
        "feature_order": list(FEATURE_ORDER),
        "training_date_utc": datetime.now(UTC).date().isoformat(),
        "code_commit": _git_revision(),
        "dataset": {
            "kind": "Synthea synthetic Massachusetts CSV",
            "requested_living_population": 5000,
            "exported_histories": 5724,
            "deceased": 724,
            "patient_seed": 20260913,
            "clinician_seed": 20260914,
            "reference_date": 20260913,
            "release_asset": "Synthea 4.0.0",
            "internal_version": "v3.4.0-18-ga07a65555",
        },
        "split_seed": SPLIT_SEED,
        "split_counts": metrics["split"],
        "model_class": type(model).__name__,
        "hyperparameters": hyperparameters,
        "preprocessing_version": "hypertension_preprocessing_v1",
        "threshold": threshold,
        "threshold_purpose": "experimental evaluation only; not a clinical cutoff",
        "calibration_status": calibration_policy,
        "primary_metrics": {
            "validation_pr_auc": validation[selected_name]["pr_auc"],
            "test_pr_auc": test_metrics["pr_auc"],
            "test_roc_auc": test_metrics["roc_auc"],
        },
        "dependencies": {
            "python": sys.version.split()[0],
            "scikit_learn": sklearn.__version__,
            "xgboost": xgboost.__version__,
            "numpy": np.__version__,
        },
        "output": "experimental probability of a first recorded essential-hypertension event within 1825 days after the eligible index encounter",
    }
    write_json(ARTIFACT_DIR / "metadata.json", metadata)
    metadata["artifact_sha256"] = {
        path.name: _sha256(path)
        for path in ARTIFACT_DIR.iterdir()
        if path.is_file() and path.name != "metadata.json"
    }
    write_json(ARTIFACT_DIR / "metadata.json", metadata)

    report = f"""# HS-010 Stage 9 model evaluation

**Decision: MODEL SELECTED — {selected_name}, version `{MODEL_VERSION}`.** This experimental model was trained and evaluated only on synthetic Synthea data. It has no clinical validation.

## Reproduction

`uv run python scripts/train_hypertension_model.py data/raw/synthea_5000_reproducible/csv`

The command reconstructs the frozen cohort, checks leakage, creates the deterministic patient split, fits preprocessing on train, compares the approved models on validation, freezes model/threshold/calibration, evaluates test once, bootstraps uncertainty, and writes artifacts.

## Frozen question and data

The model estimates the probability of a first recorded essential-hypertension event within 1,825 days after the first eligible adult paired-BP encounter, from information available by encounter stop. The cohort contains {len(rows)} patients ({positives} positive; {len(rows) - positives} negative). Split counts are `{json.dumps(metrics["split"], sort_keys=True)}`.

## Validation and selection

Validation results are `{json.dumps(validation, sort_keys=True)}`. The predeclared parsimony rule selected {selected_name}: use validation PR-AUC, and require XGBoost to exceed logistic regression by more than 0.02. The evaluation threshold {threshold:.8f} maximized validation F1 and is not a clinical cutoff. No probability calibrator was fitted because the validation set has only 24 positives.

## Untouched test evidence

The test results are `{json.dumps(test_metrics, sort_keys=True)}`. Bootstrap uncertainty is `{json.dumps(uncertainty, sort_keys=True)}`. Test was evaluated once after all development choices were frozen; no retraining or tuning followed.

## Explainability and subgroup limits

Explainability is `{json.dumps(explainability, sort_keys=True)}`. It describes model association/influence and does not establish causality. Subgroup evidence is `{json.dumps(subgroup, sort_keys=True)}` and is descriptive of synthetic data, not real-world fairness validation.

## Runtime preparation and limits

Flow: HealthSphere backend → structured `hypertension_features_v1` → frozen preprocessing → selected predictive model → experimental probability → backend assessment. `healthsphere-agent` does not calculate this probability. Required age and paired BP inputs must be present. Optional numeric inputs use train medians plus missing indicators; categorical inputs use explicit unknown values and tolerate valid unseen categories.

BP-conditioned indexing selects measured patients and creates healthcare-capture selection effects. Labels represent first *recorded* diagnoses; censoring depends on synthetic record coverage. Synthea generator artifacts may not reflect human biology, care, prevalence, calibration, or subgroup behavior.

This model must not be used for diagnosis, treatment decisions, emergency triage, or clinical decision-making.
"""
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(
        json.dumps(
            {
                "model": selected_name,
                "validation_pr_auc": validation[selected_name]["pr_auc"],
                "test": test_metrics,
                "artifacts": str(ARTIFACT_DIR),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
