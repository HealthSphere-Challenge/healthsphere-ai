from datetime import date, timedelta

import joblib
import numpy as np
import pytest
from sklearn.linear_model import LogisticRegression

from healthsphere_ai.cohort import CohortRow
from healthsphere_ai.training import (
    FEATURE_ORDER,
    make_preprocessor,
    matrix,
    select_f1_threshold,
    split_patients,
    validate_rows,
)


def row(number: int, target: int, *, heart_rate=70.0, sex="female") -> CohortRow:
    index = date(2020, 1, 1)
    return CohortRow(
        patient_id=f"patient-{number}",
        index_date=index,
        target=target,
        features={
            "age_years": 30.0 + number,
            "systolic_blood_pressure": 110.0 + target,
            "diastolic_blood_pressure": 70.0 + target,
            "heart_rate": heart_rate,
            "bmi": None if number % 2 else 24.0,
            "sex_at_birth": sex,
            "smoking_status": "unknown",
        },
        feature_dates={"systolic_blood_pressure": index, "heart_rate": index},
    )


def fixture_rows() -> list[CohortRow]:
    return [row(number, number % 2) for number in range(100)]


def test_split_is_deterministic_stratified_and_disjoint():
    rows = fixture_rows()
    first = split_patients(rows)
    second = split_patients(rows)
    assert first == second
    assert [len(first.train), len(first.validation), len(first.test)] == [70, 15, 15]
    partitions = [set(value) for value in (first.train, first.validation, first.test)]
    assert not partitions[0] & partitions[1]
    assert not partitions[0] & partitions[2]
    assert not partitions[1] & partitions[2]
    assert [sum(rows[index].target for index in part) for part in partitions] == [35, 8, 7]


def test_validation_rejects_required_missing_leakage_and_future_values():
    valid = row(1, 0)
    features = valid.features | {"patient_id": "leak"}
    with pytest.raises(ValueError, match="Invalid feature"):
        validate_rows([CohortRow("x", valid.index_date, 0, features, {})])
    missing = valid.features | {"age_years": None}
    with pytest.raises(ValueError, match="Required"):
        validate_rows([CohortRow("x", valid.index_date, 0, missing, {})])
    with pytest.raises(ValueError, match="Post-index"):
        validate_rows(
            [
                CohortRow(
                    "x",
                    valid.index_date,
                    0,
                    valid.features,
                    {"bmi": valid.index_date + timedelta(days=1)},
                )
            ]
        )


def test_preprocessor_learns_optional_median_from_train_and_handles_unknown_category():
    train = [row(1, 0, heart_rate=60.0), row(2, 1, heart_rate=80.0)]
    preprocessing = make_preprocessor().fit(matrix(train))
    optional = preprocessing.named_transformers_["optional"].named_steps["impute"]
    assert optional.statistics_[0] == 70.0
    transformed = preprocessing.transform(matrix([row(3, 0, heart_rate=None, sex="intersex")]))
    assert transformed.shape[0] == 1
    assert np.isfinite(transformed.astype(float)).all()
    assert list(FEATURE_ORDER) == [
        "age_years",
        "systolic_blood_pressure",
        "diastolic_blood_pressure",
        "heart_rate",
        "bmi",
        "sex_at_birth",
        "smoking_status",
    ]


def test_model_and_preprocessor_reload_preserve_probabilities(tmp_path):
    rows = fixture_rows()
    raw = matrix(rows)
    labels = np.asarray([item.target for item in rows])
    preprocessing = make_preprocessor().fit(raw)
    transformed = preprocessing.transform(raw)
    model = LogisticRegression(random_state=1).fit(transformed, labels)
    before = model.predict_proba(transformed)[:, 1]
    preprocessing_path = tmp_path / "preprocessing.joblib"
    model_path = tmp_path / "model.joblib"
    joblib.dump(preprocessing, preprocessing_path)
    joblib.dump(model, model_path)
    after = joblib.load(model_path).predict_proba(joblib.load(preprocessing_path).transform(raw))[
        :, 1
    ]
    assert np.allclose(before, after)
    assert np.logical_and(after >= 0, after <= 1).all()


def test_threshold_is_selected_from_given_validation_values():
    labels = np.asarray([0, 0, 1, 1])
    probabilities = np.asarray([0.1, 0.4, 0.5, 0.9])
    assert select_f1_threshold(labels, probabilities) == 0.5
