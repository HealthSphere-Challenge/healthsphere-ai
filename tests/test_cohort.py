import csv
from datetime import date
from pathlib import Path

import pytest

from healthsphere_ai.cohort import (
    LEAKAGE_BLACKLIST,
    adult_date,
    assign_indexes,
    extract_latest_features,
    label_patients,
    load_dataset,
)


def write_csv(root: Path, name: str, fields: list[str], rows: list[dict[str, str]]) -> None:
    with (root / name).open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


@pytest.fixture
def dataset_root(tmp_path: Path) -> Path:
    write_csv(
        tmp_path,
        "patients.csv",
        ["Id", "BIRTHDATE", "DEATHDATE", "GENDER"],
        [
            {"Id": "p1", "BIRTHDATE": "1980-01-01", "DEATHDATE": "", "GENDER": "M"},
            {"Id": "p2", "BIRTHDATE": "2005-06-01", "DEATHDATE": "", "GENDER": "F"},
        ],
    )
    write_csv(
        tmp_path,
        "encounters.csv",
        ["Id", "START", "STOP", "PATIENT", "ENCOUNTERCLASS"],
        [
            {
                "Id": "p1-start",
                "START": "2018-01-01",
                "STOP": "2018-01-01",
                "PATIENT": "p1",
                "ENCOUNTERCLASS": "ambulatory",
            },
            {
                "Id": "p1-index",
                "START": "2019-02-01",
                "STOP": "2019-02-01",
                "PATIENT": "p1",
                "ENCOUNTERCLASS": "wellness",
            },
            {
                "Id": "p1-end",
                "START": "2025-02-02",
                "STOP": "2025-02-02",
                "PATIENT": "p1",
                "ENCOUNTERCLASS": "ambulatory",
            },
            {
                "Id": "p2-start",
                "START": "2020-01-01",
                "STOP": "2020-01-01",
                "PATIENT": "p2",
                "ENCOUNTERCLASS": "ambulatory",
            },
            {
                "Id": "p2-index",
                "START": "2024-01-01",
                "STOP": "2024-01-01",
                "PATIENT": "p2",
                "ENCOUNTERCLASS": "wellness",
            },
        ],
    )
    write_csv(
        tmp_path,
        "observations.csv",
        ["DATE", "PATIENT", "ENCOUNTER", "CODE", "VALUE", "UNITS"],
        [
            {
                "DATE": "2019-02-01",
                "PATIENT": "p1",
                "ENCOUNTER": "p1-index",
                "CODE": "8480-6",
                "VALUE": "120",
                "UNITS": "mm[Hg]",
            },
            {
                "DATE": "2019-02-01",
                "PATIENT": "p1",
                "ENCOUNTER": "p1-index",
                "CODE": "8462-4",
                "VALUE": "80",
                "UNITS": "mm[Hg]",
            },
            {
                "DATE": "2020-02-01",
                "PATIENT": "p1",
                "ENCOUNTER": "p1-end",
                "CODE": "8867-4",
                "VALUE": "70",
                "UNITS": "/min",
            },
            {
                "DATE": "2024-01-01",
                "PATIENT": "p2",
                "ENCOUNTER": "p2-index",
                "CODE": "8480-6",
                "VALUE": "115",
                "UNITS": "mm[Hg]",
            },
            {
                "DATE": "2024-01-02",
                "PATIENT": "p2",
                "ENCOUNTER": "p2-index",
                "CODE": "8462-4",
                "VALUE": "75",
                "UNITS": "mm[Hg]",
            },
        ],
    )
    write_csv(
        tmp_path,
        "conditions.csv",
        ["START", "PATIENT", "SYSTEM", "CODE"],
        [{"START": "2021-01-01", "PATIENT": "p1", "SYSTEM": "SNOMED-CT", "CODE": "59621000"}],
    )
    return tmp_path


def test_adult_date_handles_age_and_leap_day() -> None:
    assert adult_date(date(2005, 6, 1)) == date(2023, 6, 1)
    assert adult_date(date(2004, 2, 29)) == date(2022, 2, 28)


def test_strategy_c_requires_deterministic_paired_bp(dataset_root: Path) -> None:
    dataset = load_dataset(dataset_root)
    assert assign_indexes(dataset, "C") == {"p1": date(2019, 2, 1)}
    assert assign_indexes(dataset, "C") == assign_indexes(dataset, "C")


def test_incident_target_and_prior_exclusion(dataset_root: Path) -> None:
    dataset = load_dataset(dataset_root)
    labels, prior, censored = label_patients(
        dataset, {"p1": date(2019, 2, 1)}, "essential_hypertension"
    )
    assert labels == {"p1": 1}
    assert not prior and not censored
    labels, prior, _ = label_patients(dataset, {"p1": date(2021, 1, 1)}, "essential_hypertension")
    assert not labels and prior == {"p1"}


def test_event_after_horizon_needs_complete_follow_up(dataset_root: Path) -> None:
    dataset = load_dataset(dataset_root)
    dataset.target_dates["essential_hypertension"]["p1"] = [date(2025, 1, 1)]
    labels, _, _ = label_patients(dataset, {"p1": date(2019, 2, 1)}, "essential_hypertension")
    assert labels == {"p1": 0}


def test_insufficient_negative_follow_up_is_censored(dataset_root: Path) -> None:
    dataset = load_dataset(dataset_root)
    labels, _, censored = label_patients(
        dataset, {"p2": date(2024, 1, 1)}, "essential_hypertension"
    )
    assert not labels and censored == {"p2"}


def test_feature_extraction_preserves_missing_and_blocks_future(dataset_root: Path) -> None:
    dataset = load_dataset(dataset_root)
    features = extract_latest_features(dataset, "p1", date(2019, 2, 1))
    assert features["systolic_blood_pressure"].unit == "mm[Hg]"
    assert features["diastolic_blood_pressure"].value == "80"
    assert "heart_rate" not in features
    assert "weight" not in features


def test_leakage_blacklist_covers_identity_and_future_data() -> None:
    assert {
        "patient_id",
        "encounter_id",
        "post_index_observations",
        "future_claims",
    } <= LEAKAGE_BLACKLIST
