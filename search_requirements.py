"""Operational interpretation of user specification v2; no observed vehicle facts."""
from math import isfinite
from urllib.parse import urlparse

SPECIFICATION = "docs/camper_van_search_specification_v2.md"
SPEC_VERSION = "2.0"
# 186 cm and 250 kg are desired targets, not rejection thresholds (§5–6).
PREFERENCES = {"purchase_price_eur": 5000, "finished_standing_height_cm": 186,
               "available_payload_kg": 250, "external_length_cm": [530, 560]}
MEASUREMENT_RULES = {
    "finished_standing_height_cm": (176, None),
    "bed_length_cm": (170, None), "bed_width_cm": (120, None),
    "external_length_cm": (None, 640),  # Upper boundary excluded (§40).
    "maximum_authorised_mass_kg": (None, 3500),
    "completed_loaded_mass_kg": (None, 3500),
    "available_payload_kg": (0, None), "belted_seats": (2, None),
}
# A number alone cannot prove a viable conversion or adequate drivetrain.
REVIEW_RULES = {
    "practical_standing_room": "Practical standing room for the 176 cm occupant, using a fixed roof or viable pop-top.",
    "two_person_layout": "Two adults can sit, cook and move inside; storage and a real mattress remain usable without unloading luggage.",
    "indoor_kitchen_and_toilet": "Permanent sink, two-burner cooking, worktop and 30–50 L fridge plus an indoor portable toilet are feasible.",
    "year_round_systems": "Insulation, heating, freeze protection, powered roof ventilation, water and initial off-grid systems are feasible.",
    "drivetrain_and_support": "Exact generation, engine, gearbox and body reviewed: adequate loaded mountain performance, acceptable major-failure risk, European parts and independent-garage support.",
    "fuel_eligible": "The vehicle is not LPG-only; an electric van has evidenced range and charging suitability for the specified touring use.",
    "netherlands_purchase": "This vehicle can be purchased and inspected in the Netherlands; no foreign-purchase import is required.",
}


def evidence_reference(fact):
    if not isinstance(fact, dict) or fact.get("independently_checked") is not True:
        return False
    reference = fact.get("source_url")
    if not isinstance(reference, str):
        return False
    try:
        source = urlparse(reference)
        return source.scheme == "https" and bool(source.hostname) and not source.username and not source.password
    except (ValueError, TypeError):
        return False


def evaluate_review(row):
    """The caller verifies reviewer, date and exact vehicle identity first."""
    measurements = row.get("measurements", {})
    measurements = measurements if isinstance(measurements, dict) else {}
    checks = {}
    values = {}
    for key, (minimum, maximum) in MEASUREMENT_RULES.items():
        fact = measurements.get(key)
        value = fact.get("value") if isinstance(fact, dict) else None
        valid = (evidence_reference(fact) and isinstance(value, (int, float))
                 and not isinstance(value, bool) and isfinite(value)
                 and (value >= 0 if key == "available_payload_kg" else value > 0))
        checks[key] = None
        if valid:
            values[key] = value
            checks[key] = ((minimum is None or value >= minimum)
                           and (maximum is None or (value < maximum if key == "external_length_cm" else value <= maximum)))
            if key == "belted_seats" and not float(value).is_integer():
                checks[key] = None
    for key in REVIEW_RULES:
        facts = row.get("conversion_checks", {})
        fact = facts.get(key) if isinstance(facts, dict) else None
        checks[key] = fact["confirmed"] if evidence_reference(fact) and isinstance(fact.get("confirmed"), bool) else None
    if all(key in values for key in ("completed_loaded_mass_kg", "maximum_authorised_mass_kg", "available_payload_kg")):
        checks["legal_loaded_mass"] = values["completed_loaded_mass_kg"] + values["available_payload_kg"] <= values["maximum_authorised_mass_kg"]
    else:
        checks["legal_loaded_mass"] = None
    # Known failure wins over incomplete evidence elsewhere.
    suitable = False if False in checks.values() else None if None in checks.values() else True
    preferences = {key: values[key] >= PREFERENCES[key] for key in ("finished_standing_height_cm", "available_payload_kg") if key in values}
    return {"specification_version": SPEC_VERSION, "checks": checks, "suitable": suitable,
            "preferences_met": preferences, "missing": [key for key, value in checks.items() if value is None]}
