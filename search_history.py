"""Durable minimal listing observations and per-run coverage; no raw seller HTML."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from urllib.parse import urlsplit, urlunsplit

from rdw_lookup import normalize_plate
from source_catalog import SOURCE_NAMES


def canonical(url):
    p = urlsplit(url or "")
    return urlunsplit((p.scheme.lower(), (p.hostname or "").lower().removeprefix("www."), p.path.rstrip("/"), "", ""))


def empty_state():
    return {"schema_version": 1, "listings": {}, "runs": [], "coverage": []}


def validate(state):
    if not isinstance(state, dict) or state.get("schema_version") != 1 or not isinstance(state.get("listings"), dict) or not isinstance(state.get("runs"), list) or not isinstance(state.get("coverage"), list):
        raise ValueError("Invalid search state; refusing to reset history")
    for key, entry in state["listings"].items():
        if not isinstance(key, str) or not isinstance(entry, dict) or not isinstance(entry.get("urls"), list):
            raise ValueError("Invalid listing history")
    return state


def url_key(url):
    return "url:" + hashlib.sha256(canonical(url).encode()).hexdigest()


def plate_key(item):
    c = item["candidate"]
    if c.get("individual_listing_confirmed") is True and c.get("plate_confirmed_from_listing") is True and item.get("plate"):
        try:
            return "plate:" + normalize_plate(item["plate"])
        except ValueError:
            pass
    return None


def observation(item):
    c = item["candidate"]
    # Compare each seller's listing separately: differing syndication prices are
    # conflicts, not evidence that the market price changed between source rows.
    return {"price_incl_vat": c.get("price_incl_vat"), "advertised_price": c.get("price_advertised"),
            "checks": {key: value for key, value in c.get("checks", {}).items() if key != "conversion_suitable"},
            "reported_mechanical_failure": c.get("reported_mechanical_failure"),
            "variant": c.get("variant", {}), "variant_clues": c.get("variant_clues", []), "source": c.get("source")}


def update(data, state, run_id, observed_at=None):
    validate(state)
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("A stable run ID is required")
    now = observed_at or datetime.now(timezone.utc).isoformat()
    when = datetime.fromisoformat(now)
    if when.tzinfo is None:
        raise ValueError("State observation timestamp must include timezone")
    output = deepcopy(data)
    updated = deepcopy(state)
    prior_run = next((row for row in state["runs"] if row["run_id"] == run_id), None)
    if prior_run:
        # A rerun is not a new market observation or another failed-source day.
        for item in output.get("results", []):
            item["history"] = prior_run.get("changes", {}).get(canonical(item["candidate"].get("listing_url")),
                {"status": "not_observed_in_original_run", "show_in_digest": False})
        output["history_summary"] = {"run_id": run_id, "rerun": True}
        output["coverage_health"] = next((row for row in state["coverage"] if row["run_id"] == run_id), {})
        return output, updated
    aliases = {url: key for key, entry in updated["listings"].items() for url in entry["urls"]}
    historical_plates = {}
    for key, entry in updated["listings"].items():
        if key.startswith("plate:"):
            for url in entry["urls"]:
                historical_plates.setdefault(url, set()).add(key)
    grouped = {}
    current_plates = {}
    for item in output.get("results", []):
        confirmed = plate_key(item)
        if confirmed:
            current_plates.setdefault(canonical(item["candidate"].get("listing_url")), set()).add(confirmed)
    for item in output.get("results", []):
        if item["candidate"].get("individual_listing_confirmed") is not True:
            continue
        url = canonical(item["candidate"].get("listing_url"))
        known_plates = current_plates.get(url, set())
        key = plate_key(item) or (next(iter(known_plates)) if len(known_plates) == 1 else None) or aliases.get(url) or url_key(url)
        # Promote a URL-only history to a confirmed plate without resetting age.
        old_key = aliases.get(url)
        if old_key and old_key != key and old_key.startswith("url:") and key.startswith("plate:"):
            old = updated["listings"].pop(old_key)
            if key not in updated["listings"]:
                updated["listings"][key] = old
            else:
                target = updated["listings"][key]
                target["first_seen"] = min(target["first_seen"], old["first_seen"])
                target["urls"] = sorted(set(target["urls"] + old["urls"]))
                target.setdefault("observations", {}).update(old.get("observations", {}))
            aliases.update({u: key for u in old["urls"]})
        elif old_key and old_key != key and old_key.startswith("plate:") and key.startswith("plate:"):
            item["qualified"] = False
            item.setdefault("reasons", []).append("Listing registration conflicts with persisted vehicle identity")
            item["search_assessment"] = {**item.get("search_assessment", {}), "matched": False, "status": "CONDITIONAL"}
        if len(known_plates | historical_plates.get(url, set())) > 1:
            item["qualified"] = False
            item.setdefault("reasons", []).append("Conflicting registrations on the same listing URL")
            item["search_assessment"] = {**item.get("search_assessment", {}), "matched": False, "status": "CONDITIONAL"}
        grouped.setdefault(key, []).append(item)
    changes = {}
    for key, items in grouped.items():
        old = updated["listings"].get(key)
        entry = deepcopy(old) if old else {"first_seen": now, "urls": [], "observations": {}}
        statuses = []
        reasons = []
        for item in items:
            url = canonical(item["candidate"].get("listing_url"))
            current = observation(item)
            current["extractor_fingerprint"] = data.get("run_metadata", {}).get("code_fingerprint")
            before = entry.get("observations", {}).get(url)
            status = "newly_observed" if old is None else "relisted_or_new_source" if url not in entry["urls"] else "unchanged"
            if before:
                a, b = before.get("price_incl_vat"), current.get("price_incl_vat")
                basis = "Gross"
                if a is None or b is None:
                    from listing_evidence import parse_amount
                    old_amount = parse_amount(before.get("advertised_price"))
                    new_amount = parse_amount(current.get("advertised_price"))
                    a = float(old_amount) if old_amount is not None else None
                    b = float(new_amount) if new_amount is not None else None
                    basis = "Advertised (VAT unverified)"
                if isinstance(a, (int, float)) and isinstance(b, (int, float)) and a - b >= max(250, a * .05):
                    status = "material_price_drop"
                    reasons.append(f"{basis} price decreased from {a} to {b} EUR")
                elif isinstance(a, (int, float)) and isinstance(b, (int, float)) and b - a >= max(250, a * .05):
                    status = "material_details_changed"
                    reasons.append(f"{basis} price increased from {a} to {b} EUR")
                elif any(before.get(field) != current.get(field) for field in ("reported_mechanical_failure", "variant", "variant_clues")):
                    status = "material_details_changed"
                elif before.get("checks") != current.get("checks"):
                    status = "evidence_updated"
            if before and status in ("material_details_changed", "material_price_drop") and before.get("extractor_fingerprint") != current.get("extractor_fingerprint"):
                status = "evidence_updated"
                reasons = ["Extracted evidence changed across code versions; seller-side change not established."]
            statuses.append(status)
            if url not in entry["urls"]:
                entry["urls"].append(url)
            entry.setdefault("observations", {})[url] = current
        priority = ("material_price_drop", "material_details_changed", "evidence_updated", "newly_observed", "relisted_or_new_source", "unchanged")
        status = next(value for value in priority if value in statuses)
        annotation = {"status": status, "first_seen": entry["first_seen"], "last_seen": now,
                      "show_in_digest": status in ("newly_observed", "material_price_drop", "material_details_changed", "evidence_updated"),
                      "reasons": reasons, "note": "Newly observed by this system, not proof of the seller's publication date."}
        # Keep all source prices and expose conflict without overwriting another source.
        prices = {obs["price_incl_vat"] for obs in entry["observations"].values() if obs.get("price_incl_vat") is not None}
        annotation["conflicting_source_prices"] = sorted(prices) if len(prices) > 1 else []
        for item in items:
            item["history"] = annotation
            changes[canonical(item["candidate"].get("listing_url"))] = annotation
        entry["last_seen"] = now
        entry["last_status"] = status
        updated["listings"][key] = entry
    health = coverage_health(output, state.get("coverage", []), run_id, now)
    updated["coverage"] = (updated["coverage"] + [health])[-30:]
    updated["runs"] = (updated["runs"] + [{"run_id": run_id, "observed_at": now, "changes": changes}])[-30:]
    cutoff = when - timedelta(days=275)
    updated["listings"] = {key: row for key, row in updated["listings"].items()
                           if datetime.fromisoformat(row["last_seen"]) >= cutoff}
    output["history_summary"] = {"run_id": run_id, "rerun": False, "newly_observed": sum(row["status"] == "newly_observed" for row in changes.values()),
                                 "digest_eligible_records": sum(row["show_in_digest"] for row in changes.values())}
    output["coverage_health"] = health
    output["qualifiers"] = sum(item.get("qualified") is True for item in output.get("results", []))
    from camper_pipeline import evidence_summary
    output["source_screening"] = evidence_summary(output.get("results", []))
    output["purchase_ready"] = output["qualifiers"]
    output["search_matches"] = sum(item.get("search_assessment", {}).get("matched", False) for item in output.get("results", []))
    return output, updated


def coverage_health(data, previous, run_id, now):
    sources = {}
    alerts = []
    coverage = data.get("source_coverage", {})
    for source in SOURCE_NAMES:
        row = coverage.get(source, {})
        results = [i for i in data.get("results", []) if i["candidate"].get("source") == source and i["candidate"].get("individual_listing_confirmed") is True]
        bound = len(results)
        limit = data.get("run_metadata", {}).get("max_per_source")
        prior = [run.get("sources", {}).get(source, {}) for run in previous[-5:]]
        comparable = [p for p in prior if p.get("sample_limit") == limit]
        streak = 0 if bound else 1 + (prior[-1].get("zero_bound_streak", 0) if prior else 0)
        baseline = max((p.get("bound", 0) for p in comparable), default=0)
        severity = "critical" if not bound and baseline > 0 else "warning" if not bound or (baseline >= 4 and bound < baseline / 2) else "ok"
        if streak >= 3:
            severity = "critical"
        prices = sum(i["candidate"].get("price_incl_vat") is not None for i in results)
        routes = sum(i["candidate"].get("distance_km") is not None for i in results)
        price_rate = prices / bound if bound else 0
        route_rate = routes / bound if bound else 0
        if bound and prior and any(prior[-1].get(k, 0) >= .5 and value < prior[-1][k] / 2 for k, value in (("price_rate", price_rate), ("route_rate", route_rate))):
            severity = "warning" if severity == "ok" else severity
        dealers = row.get("direct_dealers", [])
        sources[source] = {"sample_limit": limit, "bound": bound, "discovered": row.get("detail_urls_discovered", 0),
            "attempts": row.get("attempts", 0), "verified_prices": prices, "verified_routes": routes,
            "price_rate": price_rate, "route_rate": route_rate, "zero_bound_streak": streak,
            "recent_max_bound": baseline, "severity": severity, "source_status": row.get("status", "not_recorded"),
            "access_restriction": row.get("source_block_reason"), "rss_status": row.get("external_rss_snapshot_status"),
            "pending_inventory_pages": row.get("inventory_pages_pending"), "dealers": dealers}
        if severity != "ok":
            alerts.append({"source": source, "severity": severity, "message": "Missing/degraded bound inventory or evidence extraction; inspect source diagnostics. RSS is index-only."})
        for dealer in dealers:
            if dealer.get("errors") or dealer.get("inventory_pages_fetched", 0) == 0:
                alerts.append({"source": dealer.get("name"), "severity": "warning", "message": "Direct dealer inventory fetch failed; inspect maintained registry."})
    total = sum(row["bound"] for row in sources.values())
    return {"run_id": run_id, "observed_at": now, "sources": sources, "alerts": alerts,
            "status": "failed" if total == 0 else "degraded" if alerts else "bounded_coverage_available",
            "exhaustive": False, "observations": len(previous) + 1,
            "note": "Per-run history; repeated runs on one day do not establish weeks of unattended reliability."}
