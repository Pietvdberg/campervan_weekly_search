"""Dated independent vehicle checks; seller-advertised equipment is not a test."""
from datetime import datetime, timezone
from urllib.parse import urlparse

from listing_identity import identity
from rdw_lookup import normalize_plate

REVIEW_CHECKS = {
    "cab_ac_working": {"physical_test", "independent_inspection"},
    "available_for_sale": {"seller_confirmation", "independent_inspection"},
    "condition_acceptable": {"independent_inspection"},
}


def matching_review(candidate, rows):
    found = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        try:
            if (normalize_plate(row.get("plate") or "") == normalize_plate(candidate.get("plate") or "")
                    and identity(row.get("listing_url") or "") == identity(candidate.get("listing_url") or "")):
                found.append(row)
        except (ValueError, TypeError):
            continue
    return found[0] if len(found) == 1 else None


def assess(candidate, now=None):
    checks = {key: None for key in REVIEW_CHECKS}
    reasons = []
    review = candidate.get("independent_review")
    header_valid = isinstance(review, dict) and matching_review(candidate, [review]) is not None
    if header_valid:
        try:
            observed = datetime.fromisoformat(review["observed_at"])
            expires = datetime.fromisoformat(review["expires_at"])
            header_valid = (isinstance(review.get("reviewer"), str) and bool(review["reviewer"].strip())
                            and observed.tzinfo is not None and expires.tzinfo is not None
                            and observed <= (now or datetime.now(timezone.utc)) <= expires)
        except (ValueError, TypeError, KeyError):
            header_valid = False
    if header_valid:
        evidence = review.get("checks", {})
        for key, methods in REVIEW_CHECKS.items():
            fact = evidence.get(key) if isinstance(evidence, dict) else None
            if not isinstance(fact, dict):
                continue
            source = fact.get("source_url")
            try:
                if not isinstance(source, str) or urlparse(source).scheme != "https" or not urlparse(source).hostname:
                    continue
            except ValueError:
                continue
            if fact.get("method") not in methods or not isinstance(fact.get("confirmed"), bool):
                continue
            checks[key] = fact["confirmed"]
    for key, value in checks.items():
        if value is False or (key != "cab_ac_working" and value is not True):
            reasons.append("independent " + key + ": " + ("failed" if value is False else "unverified"))
    return {"status": "reviewed" if all(value is not None for key, value in checks.items() if key != "cab_ac_working") else "unverified",
            "checks": checks, "failed": any(value is False for value in checks.values()), "reasons": reasons}
