"""Deterministic target, index, and feature extraction without model fitting."""

from __future__ import annotations

import csv
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

HORIZON_DAYS = 1825
LOOKBACK_DAYS = 365
TARGET_CODES = {
    "essential_hypertension": frozenset({"59621000"}),
    "obesity_finding": frozenset({"162864005", "408512008"}),
    "type_2_diabetes": frozenset({"44054006"}),
}
FEATURE_CODES = {
    "heart_rate": frozenset({"8867-4"}),
    "systolic_blood_pressure": frozenset({"8480-6"}),
    "diastolic_blood_pressure": frozenset({"8462-4"}),
    "weight": frozenset({"29463-7"}),
    "bmi": frozenset({"39156-5"}),
    "blood_glucose": frozenset({"2339-0", "2345-7"}),
    "smoking_status": frozenset({"72166-2"}),
}
LEAKAGE_BLACKLIST = frozenset(
    {
        "patient_id",
        "encounter_id",
        "claim_id",
        "target_diagnosis_at_or_before_index",
        "post_index_conditions",
        "post_index_observations",
        "post_index_medications",
        "post_index_procedures",
        "future_encounters",
        "future_claims",
        "future_complications",
        "outcome_derived_variables",
        "record_end_date",
        "follow_up_duration",
    }
)


def parse_date(value: str) -> date:
    """Parse a Synthea ISO date or timestamp at calendar-day precision."""
    return datetime.fromisoformat(value[:10]).date()


def adult_date(birth: date) -> date:
    """Return the eighteenth birthday, including leap-day births."""
    try:
        return birth.replace(year=birth.year + 18)
    except ValueError:
        return date(birth.year + 18, 2, 28)


@dataclass(frozen=True)
class Patient:
    patient_id: str
    birth_date: date
    death_date: date | None
    sex: str


@dataclass(frozen=True)
class Encounter:
    encounter_id: str
    patient_id: str
    start: date
    stop: date
    encounter_class: str


@dataclass(frozen=True)
class Observation:
    patient_id: str
    encounter_id: str
    observed_at: date
    feature: str
    value: str
    unit: str


@dataclass
class Dataset:
    patients: dict[str, Patient]
    encounters: dict[str, list[Encounter]]
    observations: dict[str, list[Observation]]
    observation_features_by_encounter: dict[str, set[str]]
    target_dates: dict[str, dict[str, list[date]]]
    target_systems: dict[str, set[str]]


def load_dataset(root: Path) -> Dataset:
    """Load only fields needed by the readiness audit from Synthea CSV."""
    patients = {}
    with (root / "patients.csv").open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            patients[row["Id"]] = Patient(
                row["Id"],
                parse_date(row["BIRTHDATE"]),
                parse_date(row["DEATHDATE"]) if row["DEATHDATE"] else None,
                row["GENDER"],
            )

    encounters: dict[str, list[Encounter]] = defaultdict(list)
    with (root / "encounters.csv").open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            encounters[row["PATIENT"]].append(
                Encounter(
                    row["Id"],
                    row["PATIENT"],
                    parse_date(row["START"]),
                    parse_date(row["STOP"]),
                    row["ENCOUNTERCLASS"],
                )
            )
    for rows in encounters.values():
        rows.sort(key=lambda item: (item.start, item.stop, item.encounter_id))
    encounters_by_id = {
        encounter.encounter_id: encounter
        for patient_encounters in encounters.values()
        for encounter in patient_encounters
    }

    code_to_feature = {code: feature for feature, codes in FEATURE_CODES.items() for code in codes}
    observations: dict[str, list[Observation]] = defaultdict(list)
    by_encounter: dict[str, set[str]] = defaultdict(set)
    with (root / "observations.csv").open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            feature = code_to_feature.get(row["CODE"])
            if feature is None:
                continue
            observation = Observation(
                row["PATIENT"],
                row["ENCOUNTER"],
                parse_date(row["DATE"]),
                feature,
                row["VALUE"],
                row["UNITS"],
            )
            observations[observation.patient_id].append(observation)
            linked_encounter = encounters_by_id.get(observation.encounter_id)
            if (
                linked_encounter is not None
                and linked_encounter.patient_id == observation.patient_id
                and linked_encounter.start <= observation.observed_at <= linked_encounter.stop
            ):
                by_encounter[observation.encounter_id].add(feature)
    for rows in observations.values():
        rows.sort(key=lambda item: (item.observed_at, item.encounter_id, item.feature))

    target_dates = {name: defaultdict(list) for name in TARGET_CODES}
    target_systems = {name: set() for name in TARGET_CODES}
    with (root / "conditions.csv").open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            for name, codes in TARGET_CODES.items():
                if row["CODE"] in codes:
                    target_dates[name][row["PATIENT"]].append(parse_date(row["START"]))
                    target_systems[name].add(row["SYSTEM"])
    for target in target_dates.values():
        for dates in target.values():
            dates.sort()
    return Dataset(
        patients,
        dict(encounters),
        dict(observations),
        dict(by_encounter),
        {name: dict(values) for name, values in target_dates.items()},
        target_systems,
    )


def assign_indexes(dataset: Dataset, strategy: str) -> dict[str, date]:
    """Assign an index using only data allowed by the named strategy."""
    indexes = {}
    required_pair = {"systolic_blood_pressure", "diastolic_blood_pressure"}
    for patient_id, encounters in dataset.encounters.items():
        patient = dataset.patients[patient_id]
        history_cutoff = max(
            adult_date(patient.birth_date), encounters[0].start + timedelta(days=365)
        )
        if strategy == "A":
            latest_allowed = encounters[-1].stop - timedelta(days=HORIZON_DAYS)
            candidates = [
                encounter
                for encounter in encounters
                if encounter.encounter_class == "wellness"
                and history_cutoff <= encounter.start <= latest_allowed
            ]
        elif strategy == "B":
            candidates = [
                encounter for encounter in encounters if encounter.start >= history_cutoff
            ]
        elif strategy == "C":
            candidates = [
                encounter
                for encounter in encounters
                if encounter.start >= history_cutoff
                and required_pair
                <= dataset.observation_features_by_encounter.get(encounter.encounter_id, set())
            ]
        else:
            raise ValueError(f"Unsupported index strategy: {strategy}")
        if candidates:
            # Encounter-stop day allows measurements produced during that index encounter.
            indexes[patient_id] = candidates[0].stop
    return indexes


def label_patients(
    dataset: Dataset, indexes: dict[str, date], target_name: str
) -> tuple[dict[str, int], set[str], set[str]]:
    """Label incident events; censor incomplete negative follow-up."""
    horizon = timedelta(days=HORIZON_DAYS)
    labels = {}
    excluded_prior = set()
    censored = set()
    for patient_id, index_date in indexes.items():
        events = dataset.target_dates[target_name].get(patient_id, [])
        if any(event <= index_date for event in events):
            excluded_prior.add(patient_id)
            continue
        if any(index_date < event <= index_date + horizon for event in events):
            labels[patient_id] = 1
            continue
        record_end = dataset.encounters[patient_id][-1].stop
        death = dataset.patients[patient_id].death_date
        if death is not None and death < record_end:
            record_end = death
        if record_end >= index_date + horizon:
            labels[patient_id] = 0
        else:
            censored.add(patient_id)
    return labels, excluded_prior, censored


def extract_latest_features(
    dataset: Dataset, patient_id: str, index_date: date
) -> dict[str, Observation]:
    """Return latest pre/index observations; future rows are structurally excluded."""
    start = index_date - timedelta(days=LOOKBACK_DAYS)
    latest = {}
    for observation in dataset.observations.get(patient_id, []):
        if start <= observation.observed_at <= index_date:
            current = latest.get(observation.feature)
            if current is None or observation.observed_at >= current.observed_at:
                latest[observation.feature] = observation
    return latest


def audit_strategy(dataset: Dataset, strategy: str, target_name: str) -> dict[str, object]:
    """Summarize one reproducible index/target candidate without fitting anything."""
    indexes = assign_indexes(dataset, strategy)
    labels, prior, censored = label_patients(dataset, indexes, target_name)
    availability = Counter()
    complete = 0
    positive_complete = 0
    all_feature_complete = 0
    positive_all_feature_complete = 0
    units = {feature: Counter() for feature in FEATURE_CODES}
    for patient_id in labels:
        features = extract_latest_features(dataset, patient_id, indexes[patient_id])
        for feature, observation in features.items():
            availability[feature] += 1
            units[feature][observation.unit or "(blank)"] += 1
        has_pair = {
            "systolic_blood_pressure",
            "diastolic_blood_pressure",
        } <= features.keys()
        complete += has_pair
        positive_complete += has_pair and labels[patient_id] == 1
        has_all_proposed = {
            "systolic_blood_pressure",
            "diastolic_blood_pressure",
            "heart_rate",
            "bmi",
            "smoking_status",
        } <= features.keys()
        all_feature_complete += has_all_proposed
        positive_all_feature_complete += has_all_proposed and labels[patient_id] == 1
    follow_up = [
        (dataset.encounters[patient_id][-1].stop - index).days / 365.25
        for patient_id, index in indexes.items()
    ]
    positives = sum(labels.values())
    eligible = len(labels)
    return {
        "strategy": strategy,
        "target": target_name,
        "indexed_n": len(indexes),
        "eligible_n": eligible,
        "positive_n": positives,
        "negative_n": eligible - positives,
        "prevalence": round(positives / eligible, 4) if eligible else None,
        "excluded_prior_n": len(prior),
        "censored_n": len(censored),
        "median_available_follow_up_years": round(statistics.median(follow_up), 2),
        "bp_complete_n": complete,
        "positive_bp_complete_n": positive_complete,
        "all_proposed_feature_complete_n": all_feature_complete,
        "positive_all_proposed_feature_complete_n": positive_all_feature_complete,
        "feature_availability": {
            feature: {
                "available_n": availability[feature],
                "available_pct": round(availability[feature] / eligible * 100, 2)
                if eligible
                else 0,
                "missing_pct": round((1 - availability[feature] / eligible) * 100, 2)
                if eligible
                else 100,
                "units": dict(units[feature]),
            }
            for feature in FEATURE_CODES
        },
    }


def audit_all(root: Path) -> dict[str, object]:
    """Run all required Stage 8 candidate comparisons."""
    dataset = load_dataset(root)
    strategy_results = [
        audit_strategy(dataset, strategy, "essential_hypertension") for strategy in ("A", "B", "C")
    ]
    alternatives = [
        audit_strategy(dataset, "C", target) for target in ("obesity_finding", "type_2_diabetes")
    ]
    strategy_a = assign_indexes(dataset, "A")
    strategy_c = assign_indexes(dataset, "C")
    encounter_classes = Counter()
    same_encounter_bundle = Counter()
    temporal_relation = Counter()
    next_bp_delays = []
    for patient_id, index_date in strategy_c.items():
        index_encounter = next(
            encounter
            for encounter in dataset.encounters[patient_id]
            if encounter.stop == index_date
            and {"systolic_blood_pressure", "diastolic_blood_pressure"}
            <= dataset.observation_features_by_encounter.get(encounter.encounter_id, set())
        )
        encounter_classes[index_encounter.encounter_class] += 1
        for feature in dataset.observation_features_by_encounter[index_encounter.encounter_id]:
            if feature in FEATURE_CODES:
                same_encounter_bundle[feature] += 1
        for observation in dataset.observations[patient_id]:
            if observation.encounter_id != index_encounter.encounter_id:
                continue
            if observation.observed_at < index_encounter.start:
                temporal_relation["before_start"] += 1
            elif observation.observed_at > index_encounter.stop:
                temporal_relation["after_stop"] += 1
            else:
                temporal_relation["within_encounter"] += 1
    for patient_id, index_date in strategy_a.items():
        future_bp = sorted(
            observation.observed_at
            for observation in dataset.observations.get(patient_id, [])
            if observation.feature == "systolic_blood_pressure"
            and observation.observed_at > index_date
        )
        if future_bp:
            next_bp_delays.append((future_bp[0] - index_date).days)
    selected_labels, _, _ = label_patients(dataset, strategy_c, "essential_hypertension")
    event_delays = []
    for patient_id, label in selected_labels.items():
        if label:
            event_delays.append(
                min(
                    (event - strategy_c[patient_id]).days
                    for event in dataset.target_dates["essential_hypertension"][patient_id]
                    if strategy_c[patient_id]
                    < event
                    <= strategy_c[patient_id] + timedelta(days=HORIZON_DAYS)
                )
            )
    return {
        "patient_rows": len(dataset.patients),
        "target_systems": {name: sorted(values) for name, values in dataset.target_systems.items()},
        "strategies": strategy_results,
        "alternatives_at_selected_index": alternatives,
        "index_investigation": {
            "strategy_c_encounter_classes": dict(encounter_classes),
            "strategy_c_same_encounter_availability_pct": {
                feature: round(count / len(strategy_c) * 100, 2)
                for feature, count in same_encounter_bundle.items()
            },
            "strategy_c_observation_temporal_relation": dict(temporal_relation),
            "strategy_a_next_bp_delay_days_median": statistics.median(next_bp_delays),
            "strategy_a_patients_with_later_bp_n": len(next_bp_delays),
            "selected_target_event_delay_days": {
                "minimum": min(event_delays),
                "median": statistics.median(event_delays),
                "within_30_days_n": sum(delay <= 30 for delay in event_delays),
                "within_365_days_n": sum(delay <= 365 for delay in event_delays),
            },
            "duplicate_target_patient_n": {
                target: sum(len(events) > 1 for events in patients.values())
                for target, patients in dataset.target_dates.items()
            },
        },
    }
