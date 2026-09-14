#!/usr/bin/env python3
"""Audit target and pre-index feature feasibility without fitting a model."""

import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

TARGETS = {
    "essential_hypertension": {"59621000"},
    "type_2_diabetes": {"44054006"},
    "obesity_finding": {"162864005", "408512008"},
}
FEATURE_CODES = {
    "heart_rate": {"8867-4"},
    "systolic_blood_pressure": {"8480-6"},
    "diastolic_blood_pressure": {"8462-4"},
    "weight": {"29463-7"},
    "bmi": {"39156-5"},
    "blood_glucose": {"2339-0", "2345-7"},
    "smoking": {"72166-2"},
    "physical_activity": {"89555-7"},
    "sleep": {"93832-4"},
}
RANGES = {
    "heart_rate": (20, 250),
    "systolic_blood_pressure": (50, 300),
    "diastolic_blood_pressure": (30, 200),
    "weight": (2, 400),
    "bmi": (8, 80),
    "blood_glucose": (20, 1000),
}


def day(value: str) -> date:
    return datetime.fromisoformat(value[:10]).date()


def main(root: Path) -> dict:
    births = {}
    with (root / "patients.csv").open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            births[row["Id"]] = day(row["BIRTHDATE"])

    encounters = defaultdict(list)
    wellness_encounters = defaultdict(list)
    with (root / "encounters.csv").open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            event = day(row["START"])
            encounters[row["PATIENT"]].append(event)
            if row["ENCOUNTERCLASS"] == "wellness":
                wellness_encounters[row["PATIENT"]].append(event)

    indexes = {}
    for patient, dates in encounters.items():
        dates.sort()
        try:
            adult = births[patient].replace(year=births[patient].year + 18)
        except ValueError:
            adult = date(births[patient].year + 18, 2, 28)
        candidates = [
            value
            for value in wellness_encounters[patient]
            if value >= adult
            and value >= dates[0] + timedelta(days=365)
            and value <= dates[-1] - timedelta(days=1825)
        ]
        if candidates:
            indexes[patient] = candidates[0]

    target_dates = {name: defaultdict(list) for name in TARGETS}
    prior_condition = set()
    with (root / "conditions.csv").open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            patient, event = row["PATIENT"], day(row["START"])
            if patient in indexes and event < indexes[patient]:
                prior_condition.add(patient)
            for name, codes in TARGETS.items():
                if row["CODE"] in codes:
                    target_dates[name][patient].append(event)

    feature_patients = {name: set() for name in FEATURE_CODES}
    units = {name: Counter() for name in FEATURE_CODES}
    outliers = Counter()
    with (root / "observations.csv").open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            patient = row["PATIENT"]
            if patient not in indexes:
                continue
            observed = day(row["DATE"])
            if not (indexes[patient] - timedelta(days=365) <= observed <= indexes[patient]):
                continue
            for name, codes in FEATURE_CODES.items():
                if row["CODE"] not in codes:
                    continue
                feature_patients[name].add(patient)
                units[name][row["UNITS"] or "(blank)"] += 1
                if name in RANGES:
                    try:
                        value = float(row["VALUE"])
                        low, high = RANGES[name]
                        if value < low or value > high:
                            outliers[name] += 1
                    except ValueError:
                        outliers[name] += 1

    candidates = {}
    horizon = timedelta(days=1825)
    for name in TARGETS:
        eligible = []
        positives = 0
        for patient, index in indexes.items():
            dates = target_dates[name].get(patient, [])
            if any(event <= index for event in dates):
                continue
            eligible.append(patient)
            positives += any(index < event <= index + horizon for event in dates)
        candidates[name] = {
            "eligible_n": len(eligible),
            "positive_n": positives,
            "negative_n": len(eligible) - positives,
            "prevalence": round(positives / len(eligible), 4) if eligible else None,
            "follow_up_years": 5,
            "patient_split_feasible": positives >= 30,
        }

    feature_base = set(indexes)
    features = {
        "demographics": {
            "available_n": len(feature_base),
            "missingness": 0.0,
            "representation": "patient table",
        },
        "prior_conditions": {
            "available_n": len(prior_condition),
            "missingness": round(1 - len(prior_condition) / len(feature_base), 4),
            "representation": (
                "pre-index condition codes; absence may reflect no event or missing capture"
            ),
        },
    }
    for name in FEATURE_CODES:
        available = len(feature_patients[name])
        features[name] = {
            "available_n": available,
            "missingness": round(1 - available / len(feature_base), 4),
            "units": dict(units[name]),
            "outlier_rows": outliers[name],
            "lookback_days": 365,
        }

    return {
        "population_rows": len(births),
        "indexed_adult_patients": len(indexes),
        "index_rule": (
            "first adult wellness encounter after >=1 year observed history and with >=5 years "
            "subsequent encounters; same-visit measurements may be used"
        ),
        "candidates": candidates,
        "features": features,
    }


if __name__ == "__main__":
    source = Path(sys.argv[1] if len(sys.argv) > 1 else "data/raw/synthea_5000/csv")
    print(json.dumps(main(source), indent=2, sort_keys=True))
