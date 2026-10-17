"""Advertised search fit is separate from inspected purchase
readiness.
"""

from math import isfinite

SEARCH_CHECKS = (
    "high_roof",
    "cab_ac",
    "distance_within_100km",
    "price_incl_vat_within_8000",
)


def assess(item):
    from campervan_search.camper_pipeline import (
        candidate_state,
        clearly_over_budget_title,
    )

    c = item["candidate"]
    checks = {key: c.get("checks", {}).get(key) for key in SEARCH_CHECKS}
    for field, key, limit in (
        ("price_incl_vat", "price_incl_vat_within_8000", 8000),
        ("distance_km", "distance_within_100km", 100),
    ):
        value = c.get(field)
        valid = (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and isfinite(value)
            and value > 0
        )
        if valid and value > limit:
            checks[key] = False
        elif not valid:
            checks[key] = None
    rejected = (
        candidate_state(item) == "REJECTED"
        or clearly_over_budget_title(c)
        or False in checks.values()
    )
    bound = c.get("individual_listing_confirmed") is True
    supported = sum(value is True for value in checks.values())
    matched = bound and not rejected and supported == len(checks)
    # An incomplete price/route/roof can be worth research, but is never
    # a
    # pass.
    useful = (
        bound and not rejected and supported >= 2 and checks["cab_ac"] is True
    )
    status = (
        "REJECTED"
        if rejected
        else (
            "INDEX_ONLY"
            if not bound
            else (
                "SEARCH_MATCH"
                if matched
                else "CONDITIONAL" if useful else "INSUFFICIENT_EVIDENCE"
            )
        )
    )
    return {
        "status": status,
        "matched": matched,
        "checklist_coverage_percent": 100 * supported / len(checks),
        "checks": checks,
        "missing": [key for key, value in checks.items() if value is None],
        "purchase_ready": bool(item.get("qualified")) and not rejected,
        "note": (
            "Advertised search fit; not a mechanical-safety score. Inspection,"
            " layout, mass and availability remain pre-purchase checks."
        ),
    }
