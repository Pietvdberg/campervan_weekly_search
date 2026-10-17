"""Audit pipeline invariants and stage outcomes; zero matches is not a failure."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from math import isfinite
from pathlib import Path
from urllib.parse import urlparse

from source_catalog import SOURCE_NAMES, REQUIRED_CHECKS


def code_fingerprint():
    root = Path(__file__).resolve().parent
    digest = hashlib.sha256()
    for path in sorted(list(root.glob("*.py")) + [root / "dealer_registry.json", root / "variant_research.json"]):
        if path.is_file():
            digest.update(path.name.encode() + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()


def record_key(candidate):
    parsed = urlparse(candidate.get("listing_url") or "")
    return candidate.get("source", "Unknown"), (parsed.hostname or "").removeprefix("www."), parsed.path.rstrip("/")


def valid_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)


def compare(before, after):
    a = {record_key(item["candidate"]): item for item in before.get("results", [])}
    b = {record_key(item["candidate"]): item for item in after.get("results", [])}
    common = set(a) & set(b)
    gains = {}
    for field in ("price_incl_vat", "distance_km"):
        gains[field + "_unknown_to_known"] = sum(a[key]["candidate"].get(field) is None and b[key]["candidate"].get(field) is not None for key in common)
    gains["plate_unknown_to_confirmed"] = sum(not a[key].get("plate") and bool(b[key].get("plate")) for key in common)
    return {"common_source_listing_records": len(common), "only_before": len(set(a) - set(b)),
            "only_after": len(set(b) - set(a)), "matched_record_evidence_gains": gains,
            "note": "Changing live samples are not controlled accuracy experiments; gains are paired only on identical source/listing URLs."}


def summarize(discovery, screening, baseline=None):
    from camper_pipeline import screen, candidate_state
    results = screening.get("results", [])
    candidates = discovery.get("candidates", [])
    coverage = discovery.get("source_coverage", {})
    errors = []
    if Counter(record_key(c) for c in candidates) != Counter(record_key(item["candidate"]) for item in results):
        errors.append("Discovery and screening record identities/counts differ")
    source_metrics = {}
    for source in SOURCE_NAMES:
        rows = [item for item in results if item["candidate"].get("source") == source]
        entry = coverage.get(source)
        if not isinstance(entry, dict):
            errors.append("Missing source coverage: " + source)
            entry = {}
        source_metrics[source] = {"records": len(rows), "identity_bound": sum(item["candidate"].get("individual_listing_confirmed") is True for item in rows),
            "verified_gross_prices": sum(item["candidate"].get("price_incl_vat") is not None for item in rows),
            "road_routes": sum(item["candidate"].get("distance_km") is not None for item in rows),
            "confirmed_plates": sum(bool(item.get("plate")) for item in rows),
            "rejected": sum(candidate_state(item) == "REJECTED" for item in rows),
            "research_leads": sum(candidate_state(item) == "POTENTIAL MATCH — UNVERIFIED" for item in rows),
            "index_exclusions": len(entry.get("inventory_prefilter_rejections", [])),
            "budget_filter_confirmed": entry.get("budget_filter_confirmed", False),
            "access_status": entry.get("status", "not_checked"), "access_restriction": entry.get("source_block_reason"),
            "direct_dealers": entry.get("direct_dealers", [])}
    for index, item in enumerate(results):
        candidate = item["candidate"]
        checks = candidate.get("checks", {})
        if not candidate.get("individual_listing_confirmed") and (item.get("plate") or any(value is True for value in checks.values())):
            errors.append(f"Record {index}: unbound lead supplies positive verification")
        if checks.get("price_incl_vat_within_8000") is True:
            amount = candidate.get("price_incl_vat")
            if not valid_number(amount) or not 0 < amount <= 8000:
                errors.append(f"Record {index}: budget pass lacks valid gross price")
        if checks.get("distance_within_100km") is True:
            distance = candidate.get("distance_km")
            if not valid_number(distance) or not 0 < distance <= 100:
                errors.append(f"Record {index}: route pass lacks valid road distance")
        if item.get("search_assessment", {}).get("matched"):
            from search_assessment import assess as assess_search
            if not assess_search(item)["matched"]:
                errors.append(f"Record {index}: search match violates advertised evidence gates")
        if item.get("qualified"):
            if not screen(candidate)["qualified"] or any(checks.get(key) is not True for key in REQUIRED_CHECKS):
                errors.append(f"Record {index}: qualification violates current evidence/review gates")
            rdw = item.get("rdw") or {}
            vehicle = rdw.get("vehicle", {})
            records = vehicle.get("records", [])
            if (vehicle.get("status") != "ok" or not isinstance(records, list) or len(records) != 1
                    or not isinstance(records[0], dict) or records[0].get("kenteken") != item.get("plate")):
                errors.append(f"Record {index}: qualified registration is not matched")
            if rdw.get("status") == "error" or any(risk.get("blocks_qualification") for risk in item.get("rdw_risks", [])):
                errors.append(f"Record {index}: qualified result has incomplete/adverse RDW evidence")
    qualified = sum(item.get("qualified") is True for item in results)
    if screening.get("qualifiers") != qualified:
        errors.append("Qualified total disagrees with result records")
    rss = screening.get("rss_evaluation")
    if rss is not None:
        rss_rows = rss.get("results", [])
        expected = discovery.get("unverified_rss_leads", [])
        if (rss.get("evaluated_records") != len(expected) or len(rss_rows) != len(expected)
                or Counter(row.get("url") for row in rss_rows) != Counter(row.get("url") for row in expected)):
            errors.append("RSS evaluation must preserve every supplied feed record")
        if Counter(row.get("status") for row in rss_rows) != Counter({key:value for key,value in rss.get("counts", {}).items() if value}):
            errors.append("RSS evaluation outcome counts disagree with records")
        if any(row.get("distance_km") is not None for row in rss_rows):
            errors.append("RSS town hints must not create verified road distances")
        eligible = {row.get("url") for row in rss_rows if row.get("status") in ("INTERESTING", "NEEDS_INFO")}
        if any(row.get("url") not in eligible for row in rss.get("shortlist", [])):
            errors.append("RSS shortlist contains an excluded or unevaluated record")
    missing_sources = [source for source, row in source_metrics.items() if row["identity_bound"] == 0]
    pending_review = sum(bool(item.get("reasons")) and candidate_state(item) != "REJECTED" for item in results)
    output = {"generated_at": datetime.now(timezone.utc).isoformat(), "code_fingerprint": discovery.get("run_metadata", {}).get("code_fingerprint"),
              "run_metadata": discovery.get("run_metadata", {}), "validation_passed": not errors, "errors": errors,
              "stages": {"discovery": "partial" if missing_sources else "bounded_samples_available",
                         "screening": "invalid" if errors else "completed", "independent_review": "pending" if pending_review else "no_unrejected_pending_records",
                         "email": "not_requested_by_this_validation"},
              "search_matches": sum(item.get("search_assessment", {}).get("matched", False) for item in results),
              "coverage_health": screening.get("coverage_health"),
              "records": len(results), "qualified": qualified, "sources": source_metrics,
              "source_groups_without_bound_records": missing_sources, "unrejected_records_needing_review": pending_review,
              "production_ready": False,
              "readiness_note": "Functional validation and zero matches do not establish exhaustive coverage, independent physical evidence or approval to activate production."}
    if baseline is not None:
        output["baseline_comparison"] = compare(baseline, screening)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--discovery", required=True)
    parser.add_argument("--screening", required=True)
    parser.add_argument("--baseline")
    parser.add_argument("--output", default="validation_summary.json")
    args = parser.parse_args()
    read = lambda path: json.loads(Path(path).read_text(encoding="utf-8"))
    result = summarize(read(args.discovery), read(args.screening), read(args.baseline) if args.baseline else None)
    Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("validation_passed", "records", "qualified", "stages", "errors")}, indent=2))
    return 0 if result["validation_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
