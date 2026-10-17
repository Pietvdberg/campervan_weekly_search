"""Fictional independent review proof; never used by discovery or production."""
from search_requirements import REVIEW_RULES


def conversion_fields():
    values = {"finished_standing_height_cm": 180, "bed_length_cm": 170, "bed_width_cm": 120,
              "external_length_cm": 550, "maximum_authorised_mass_kg": 3500,
              "completed_loaded_mass_kg": 3000, "available_payload_kg": 500, "belted_seats": 2}
    return {"measurements": {key: {"value": value, "source_url": "https://example.test/fictional-v2-measurement", "independently_checked": True} for key, value in values.items()},
            "conversion_checks": {key: {"confirmed": True, "source_url": "https://example.test/fictional-v2-layout", "independently_checked": True} for key in REVIEW_RULES}}


def add_conversion_fields(row):
    proof = conversion_fields()
    row["measurements"] = {**row.get("measurements", {}), **proof["measurements"]}
    row["conversion_checks"] = proof["conversion_checks"]
    return row
