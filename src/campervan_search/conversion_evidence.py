"""Explicit reviewed measurements; no suitability inferred from a van
model.
"""

from datetime import datetime, timezone
from math import isfinite

from campervan_search.listing_identity import identity
from campervan_search.rdw_lookup import normalize_plate
from campervan_search.search_requirements import (
    evaluate_review,
    evidence_reference,
)

MEASUREMENTS = (
    "available_payload_kg",
    "internal_height_cm",
    "internal_length_cm",
)


def positive_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and isfinite(value)
        and value > 0
    )


def assess(candidate, requirements, assessments, now=None):
    """Match reviewed evidence to this listing and apply
    caller-specified
        minima.

            Available payload must be assessed for the planned
    conversion,
        rather than
            copied from a model's nominal payload. This function
    checks the
        review
            contract, not whether an external measurement is true.
    """

    def unavailable(reason):
        return {"status": "unverified", "suitable": None, "reason": reason}

    requirements = {} if requirements is None else requirements
    if not isinstance(requirements, dict) or (
        requirements
        and not all(
            positive_number(requirements.get(key)) for key in MEASUREMENTS
        )
    ):
        return unavailable(
            "Explicit positive payload, height and length minima are required"
        )
    if not isinstance(assessments, list):
        return unavailable("Assessments must be a list")
    try:
        plate = normalize_plate(candidate.get("plate") or "")
    except ValueError:
        return unavailable("No confirmed listing plate")
    if (
        candidate.get("plate_confirmed_from_listing") is not True
        or candidate.get("individual_listing_confirmed") is not True
    ):
        return unavailable(
            "Listing and plate must be confirmed before conversion review"
        )
    matches = []
    for row in assessments:
        if not isinstance(row, dict):
            continue
        try:
            same_plate = normalize_plate(row.get("plate") or "") == plate
            same_listing = identity(row.get("listing_url") or "") == identity(
                candidate.get("listing_url") or ""
            )
        except (ValueError, TypeError):
            continue
        if same_plate and same_listing:
            matches.append(row)
    if len(matches) != 1:
        return unavailable(
            "Exactly one matching listing-and-plate assessment is required"
        )
    row = matches[0]
    if not isinstance(row.get("reviewer"), str) or not row["reviewer"].strip():
        return unavailable("A named reviewer is required")
    try:
        observed = datetime.fromisoformat(row["observed_at"])
        expires = datetime.fromisoformat(row["expires_at"])
        now = now or datetime.now(timezone.utc)
        if (
            observed.tzinfo is None
            or expires.tzinfo is None
            or not observed <= now <= expires
        ):
            return unavailable(
                "Review is expired, future-dated or lacks timezone information"
            )
    except (ValueError, TypeError, KeyError):
        return unavailable("Review timestamps are invalid")
    measurements = row.get("measurements", {})
    if not isinstance(measurements, dict):
        return unavailable("Measurements must be an object")
    checks = {}
    for key in MEASUREMENTS if requirements else ():
        measurement = measurements.get(key, {})
        checks["custom_minimum_" + key] = None
        if (
            isinstance(measurement, dict)
            and positive_number(measurement.get("value"))
            and evidence_reference(measurement)
        ):
            checks["custom_minimum_" + key] = (
                measurement["value"] >= requirements[key]
            )
    spec = evaluate_review(row)
    checks.update(spec["checks"])
    suitable = (
        False
        if False in checks.values()
        else None if None in checks.values() else True
    )
    return {
        "status": "reviewed" if suitable is not None else "unverified",
        "suitable": suitable,
        "checks": checks,
        "specification_version": spec["specification_version"],
        "preferences_met": spec["preferences_met"],
        "requirements": requirements,
        "assessment": row,
        "reason": (
            "All reviewed hard requirements met"
            if suitable is True
            else (
                "Reviewed hard requirement failed"
                if suitable is False
                else "Missing v2 evidence: "
                + ", ".join(
                    key for key, value in checks.items() if value is None
                )
            )
        ),
    }
