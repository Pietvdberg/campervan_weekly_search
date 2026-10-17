"""Explicit reviewed measurements; no suitability inferred from a van model."""
from datetime import datetime, timezone
from math import isfinite
from urllib.parse import urlparse

from listing_identity import identity
from rdw_lookup import normalize_plate

MEASUREMENTS = ("available_payload_kg", "internal_height_cm", "internal_length_cm")


def positive_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value) and value > 0


def assess(candidate, requirements, assessments, now=None):
    """Match reviewed evidence to this listing and apply caller-specified minima.

    Available payload must be assessed for the planned conversion, rather than
    copied from a model's nominal payload. This function checks the review
    contract, not whether an external measurement is true.
    """
    unavailable = lambda reason: {"status": "unverified", "suitable": None, "reason": reason}
    if not isinstance(requirements, dict) or not all(positive_number(requirements.get(key)) for key in MEASUREMENTS):
        return unavailable("Explicit positive payload, height and length minima are required")
    if not isinstance(assessments, list):
        return unavailable("Assessments must be a list")
    try:
        plate = normalize_plate(candidate.get("plate") or "")
    except ValueError:
        return unavailable("No confirmed listing plate")
    if candidate.get("plate_confirmed_from_listing") is not True or candidate.get("individual_listing_confirmed") is not True:
        return unavailable("Listing and plate must be confirmed before conversion review")
    matches = []
    for row in assessments:
        if not isinstance(row, dict):
            continue
        try:
            same_plate = normalize_plate(row.get("plate") or "") == plate
            same_listing = identity(row.get("listing_url") or "") == identity(candidate.get("listing_url") or "")
        except (ValueError, TypeError):
            continue
        if same_plate and same_listing:
            matches.append(row)
    if len(matches) != 1:
        return unavailable("Exactly one matching listing-and-plate assessment is required")
    row = matches[0]
    if not isinstance(row.get("reviewer"), str) or not row["reviewer"].strip():
        return unavailable("A named reviewer is required")
    try:
        observed = datetime.fromisoformat(row["observed_at"])
        expires = datetime.fromisoformat(row["expires_at"])
        now = now or datetime.now(timezone.utc)
        if observed.tzinfo is None or expires.tzinfo is None or not observed <= now <= expires:
            return unavailable("Review is expired, future-dated or lacks timezone information")
    except (ValueError, TypeError, KeyError):
        return unavailable("Review timestamps are invalid")
    measurements = row.get("measurements", {})
    if not isinstance(measurements, dict):
        return unavailable("Measurements must be an object")
    checks = {}
    for key in MEASUREMENTS:
        measurement = measurements.get(key, {})
        if not isinstance(measurement, dict) or not positive_number(measurement.get("value")):
            return unavailable("Missing reviewed measurement: " + key)
        source = measurement.get("source_url", "")
        if not isinstance(source, str) or urlparse(source).scheme != "https" or not urlparse(source).hostname:
            return unavailable("HTTPS evidence reference required for " + key)
        if measurement.get("independently_checked") is not True:
            return unavailable("Independent measurement review required for " + key)
        checks[key] = measurement["value"] >= requirements[key]
    return {"status": "reviewed", "suitable": all(checks.values()), "checks": checks,
            "requirements": requirements, "assessment": row,
            "reason": "All reviewed minima met" if all(checks.values()) else "Reviewed conversion minimum failed"}
