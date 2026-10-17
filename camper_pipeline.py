#!/usr/bin/env python3
"""Evidence-gated candidate screening and RDW lookup for discovered listings."""
import argparse
from datetime import date
import json
from pathlib import Path
from math import isfinite
from urllib.parse import urlparse, urlunparse
import re
from html import unescape
from rdw_lookup import lookup, normalize_plate
from search_requirements import SPEC_VERSION
from conversion_evidence import assess as assess_conversion
from vehicle_review import assess as assess_vehicle, matching_review
from vehicle_risks import sale_exclusion, auction_evidence, rdw_risks

from source_catalog import SOURCE_NAMES as SOURCES, REQUIRED_CHECKS as REQUIRED

def normalized_url(url):
    """Strip tracking/query fragments without changing a listing's identity."""
    p = urlparse(url or "")
    host = (p.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = p.path.rstrip("/") or "/"
    return urlunparse((p.scheme.lower(), host, path, "", "", ""))


def candidate_state(item):
    """Hard failures take precedence over evidence-based ranking."""
    if item.get("independent_review_assessment", {}).get("failed"):
        return "REJECTED"
    if any(risk.get("code") == "licence_mass_review" and risk.get("blocks_qualification")
           for risk in item.get("rdw_risks", [])):
        return "REJECTED"
    if sale_exclusion(item["candidate"]):
        return "REJECTED"
    if any(item["candidate"].get("checks", {}).get(k) is False for k in REQUIRED):
        return "REJECTED"
    if item["qualified"]:
        return "QUALIFIED"
    return "POTENTIAL MATCH — UNVERIFIED"


def report_identity(item):
    c = item["candidate"]
    if item.get("plate"):
        # Plate confirmation is listing-derived; group identical vehicles without
        # changing source-level counts or the independently retained audit records.
        return "confirmed-plate:" + item["plate"]
    return "url:" + normalized_url(c.get("listing_url", ""))


def report_priority(item):
    c = item["candidate"]
    checks = c.get("checks", {})
    suitability = item.get("suitability", {})
    return (int(item.get("search_assessment", {}).get("matched", False)),
            -sum(risk.get("code") == "odometer_inconsistent" for risk in item.get("rdw_risks", [])),
            int(checks.get("price_incl_vat_within_8000") is True and checks.get("distance_within_100km") is True),
            int(checks.get("distance_within_100km") is True),
            int(checks.get("price_incl_vat_within_8000") is True),
            int(checks.get("high_roof") is True and checks.get("cab_ac") is True),
            -sum(bool(risk.get("blocks_qualification")) for risk in item.get("rdw_risks", [])),
            int(suitability.get("critical_research_supported", False)),
            suitability.get("weighted_score_known_criteria") or 0 if suitability.get("critical_research_supported") else 0,
            int(bool(item.get("plate"))), item["score"])


def unique_report_items(items):
    selected = {}
    for item in items:
        key = report_identity(item)
        previous = selected.get(key)
        rank = lambda value: (value["qualified"], report_priority(value))
        if previous is None or rank(item) > rank(previous):
            selected[key] = item
    yield from selected.values()


def report_selection(data):
    """One presentation model for text and HTML; the raw audit stays intact."""
    results = data.get("results", [])
    grouped = list(unique_report_items(results))
    # An explicit development review can revisit known stock without mutating
    # durable history or claiming it is newly advertised. Weekly suppression stays on.
    visible = lambda x: data.get("report_context") == "development_review" or x.get("history", {}).get("show_in_digest", True)
    qualified = sorted((x for x in grouped if candidate_state(x) == "QUALIFIED" and visible(x)),
                       key=report_priority, reverse=True)
    potential = [x for x in grouped if candidate_state(x) == "POTENTIAL MATCH — UNVERIFIED"
                 and x.get("search_assessment", {}).get("status") in ("SEARCH_MATCH", "CONDITIONAL")
                 and visible(x)]
    potential.sort(key=report_priority, reverse=True)
    search_matches = [x for x in grouped if x.get("search_assessment", {}).get("matched") and visible(x)]
    return {"qualified": qualified, "potential": potential[:5], "search_matches": search_matches,
            "unchanged_suppressed": sum(not visible(x) for x in grouped),
            "screened_records": len(results),
            "rejected_records": sum(candidate_state(x) == "REJECTED" for x in results)}


def rss_price(description):
    text = unescape(re.sub(r"<[^>]*>", " ", str(description or "")))
    match = re.search(r"vraagprijs\s*:\s*€\s*([\d.]+)(?:,\d{1,2})?", text, re.I)
    return int(match.group(1).replace(".", "")) if match else None


def rss_shortlist(leads, verified_urls=(), limit=5):
    """RSS is first-party index evidence only; never treat it as a verified advert."""
    seen = set(normalized_url(u) for u in verified_urls)
    eligible = []
    for lead in leads:
        url = str(lead.get("url") or "")
        identity = normalized_url(url)
        title = unescape(str(lead.get("title") or ""))
        text = title.lower()
        if not url.startswith("https://www.autowereld.nl/") or identity in seen or auction_evidence(title):
            continue
        seen.add(identity)
        if not re.search(r"\bl[23]\s*[- ]?h2\b", text, re.I):
            continue
        if re.search(r"\b(open laadbak|pick[ -]?up|pr[iy]tsche|chassis cabine|bakwagen|laadklep|kipper|schade|motor niet|defect|hoogwerker)\b", text, re.I):
            continue
        price = rss_price(lead.get("description"))
        # Any stated advertised price above the absolute VAT-inclusive limit
        # is already disqualifying, regardless of whether VAT is included.
        if price is not None and price > 8000:
            continue
        eligible.append((price is None, -(price or 0), lead))
    eligible.sort(key=lambda x: (x[0], x[1]))
    return [entry[2] for entry in eligible[:limit]]


def clearly_over_budget_title(candidate):
    """A displayed title price over €8,000 rules out a shortlist lead even if VAT is unknown.

    Only use a currency-labelled amount from the listing title; page-wide price
    extraction can select an unrelated amount. Keep full audit and unknown VAT.
    """
    title = unescape(str(candidate.get("name") or ""))
    matches = re.findall(r"(?:€|EUR)\s*([\d.]+(?:,\d{2})?)", title, re.I)
    return any(rss_price("Vraagprijs: €" + amount) > 8000 for amount in matches
               if rss_price("Vraagprijs: €" + amount) is not None)


def screen(candidate):
    checks = dict(candidate.get("checks", {}))
    if checks.get("conversion_suitable") is True:
        prior = candidate.get("conversion_assessment", {})
        prior = prior if isinstance(prior, dict) else {}
        review = assess_conversion(candidate, prior.get("requirements"), [prior.get("assessment")])
        checks["conversion_suitable"] = review["suitable"]
        candidate = {**candidate, "checks": checks, "conversion_assessment": review}
    score = 20 * sum(checks.get(key) is True for key in REQUIRED)
    reasons = [key+": "+("failed" if checks.get(key) is False else "unverified") for key in REQUIRED if checks.get(key) is not True]
    u = urlparse(candidate.get("listing_url",""))
    if not (u.scheme == "https" and u.netloc and candidate.get("individual_listing_confirmed") is True):
        reasons.append("individual current listing not independently confirmed")
    plate = candidate.get("plate")
    if plate and candidate.get("plate_confirmed_from_listing") is True:
        try: plate = normalize_plate(plate)
        except ValueError: plate = None
    else: plate = None
    if not plate: reasons.append("plate not confirmed from individual listing")
    exclusion = sale_exclusion(candidate)
    if exclusion:
        reasons.append(exclusion)
    independent_review = assess_vehicle(candidate)
    reasons.extend(independent_review["reasons"])
    return {"candidate":candidate, "score":score, "plate":plate, "reasons":reasons, "qualified":score >= 90 and not reasons, "rdw":None, "independent_review_assessment":independent_review}

def evidence_summary(results):
    """Per-source assessment: explicit failures differ from missing evidence."""
    summary={}
    for item in results:
        candidate=item["candidate"]
        source=candidate.get("source","Unknown")
        entry=summary.setdefault(source,{"total":0,"qualified":0,
            "checks":{name:{"passed":0,"failed":0,"unknown":0} for name in REQUIRED},
            "verified_prices":0,"verified_distances":0,"confirmed_plates":0})
        entry["total"]+=1
        entry["qualified"]+=int(item["qualified"])
        entry["verified_prices"]+=int(candidate.get("price_incl_vat") is not None)
        entry["verified_distances"]+=int(candidate.get("distance_km") is not None)
        entry["confirmed_plates"]+=int(bool(item.get("plate")))
        for name in REQUIRED:
            status=candidate.get("checks",{}).get(name)
            entry["checks"][name]["passed" if status is True else
                                 "failed" if status is False else "unknown"]+=1
    return summary

def validate_input(data):
    """Reject malformed batches before any external lookup is attempted."""
    if not isinstance(data, dict) or not isinstance(data.get("candidates", []), list):
        raise ValueError("Input must be an object containing a candidates list")
    for index, candidate in enumerate(data.get("candidates", [])):
        if not isinstance(candidate, dict):
            raise ValueError(f"Candidate {index} must be an object")
        checks = candidate.get("checks", {})
        if not isinstance(checks, dict) or any(value is not None and not isinstance(value, bool) for value in checks.values()):
            raise ValueError(f"Candidate {index} checks must contain only true, false or null")
        for field in ("listing_url", "name", "plate", "source"):
            if candidate.get(field) is not None and not isinstance(candidate[field], str):
                raise ValueError(f"Candidate {index} {field} must be text")
        for field in ("price_incl_vat", "distance_km"):
            value = candidate.get(field)
            if value is not None and (not isinstance(value, (int, float)) or isinstance(value, bool) or not isfinite(value) or value < 0):
                raise ValueError(f"Candidate {index} {field} must be a finite nonnegative number")


def evaluate(data, rdw_lookup=lookup):
    validate_input(data)
    candidates = data.get("candidates", [])
    if "conversion_evidence" in data:
        contract = data["conversion_evidence"]
        if not isinstance(contract, dict):
            raise ValueError("conversion_evidence must be an object")
        reviewed = []
        for candidate in candidates:
            assessment = assess_conversion(candidate, contract.get("requirements"), contract.get("assessments"))
            candidate = {**candidate, "checks": {**candidate.get("checks", {}),
                         "conversion_suitable": assessment["suitable"],
                         "high_roof": True if assessment["suitable"] is True else candidate.get("checks", {}).get("high_roof")}, "conversion_assessment": assessment}
            vehicle_review = matching_review(candidate, contract.get("assessments"))
            if vehicle_review and "checks" in vehicle_review:
                candidate["independent_review"] = vehicle_review
            reviewed.append(candidate)
        candidates = reviewed
    results=[screen(c) for c in candidates]
    for item in results:
        if not item["plate"] or candidate_state(item) == "REJECTED": continue
        try: item["rdw"]=rdw_lookup(item["plate"])
        except Exception as exc: item["rdw"]={"error":str(exc)}
        vehicle=item["rdw"].get("vehicle",{})
        records = vehicle.get("records", [])
        if (vehicle.get("status") != "ok" or len(records) != 1
                or records[0].get("kenteken") != item["plate"]):
            item["qualified"]=False
            item["reasons"].append("RDW registration not verified")
        if (item["rdw"].get("status") == "error"
                or item["rdw"].get("defects", {}).get("status") == "error"
                or item["rdw"].get("defect_catalogue_errors")):
            item["qualified"] = False
            item["reasons"].append("RDW/APK lookup incomplete")
        if vehicle.get("status") == "ok" and len(records) == 1 and records[0].get("kenteken") == item["plate"]:
            item["rdw_risks"] = rdw_risks(records[0])
            for concern in item["rdw_risks"]:
                if concern["blocks_qualification"]:
                    item["qualified"] = False
                    item["reasons"].append(concern["message"])
    from search_assessment import assess as assess_search
    from suitability import rank
    for item in results:
        item["search_assessment"] = assess_search(item)
        item["suitability"] = rank(item)
    return {"run_metadata": data.get("run_metadata", {}), "search_matches": sum(item["search_assessment"]["matched"] for item in results),
            "purchase_ready": sum(item["qualified"] for item in results),
            "specification_version": SPEC_VERSION, "generated_on":date.today().isoformat(),"source_screening":evidence_summary(results),
            "source_coverage":data.get("source_coverage",{}),"discovery_method":data.get("discovery_method","no live discovery performed"),
            "unverified_rss_leads":data.get("unverified_rss_leads",[]),
            "results":results,"qualifiers":sum(x["qualified"] for x in results)}


def dealer_audit_rows(data):
    """One concise, evidence-preserving row per local-dealer vehicle."""
    rows=[]
    for item in data.get("results",[]):
        c=item["candidate"]
        if c.get("source")!="Local dealers":
            continue
        rows.append({
            "url":c.get("listing_url"),
            "name":c.get("name"),
            "score":item["score"],
            "price_advertised":c.get("price_advertised"),
            "price_incl_vat":c.get("price_incl_vat"),
            "vat_basis":c.get("vat_basis","unknown"),
            "city_mentioned_not_verified":c.get("city_mentioned"),
            "verified_driving_distance_km":c.get("distance_km"),
            "checks":{k:c.get("checks",{}).get(k) for k in REQUIRED},
            "plate_confirmed_from_listing":bool(item.get("plate")),
            "blockers":list(item["reasons"]),
        })
    return rows

def report(data):
    """Concise email. Full rejected candidates and RDW evidence stay in JSON audit."""
    results = data.get("results", [])
    selection = report_selection(data)
    qualified = selection["qualified"]
    potential = selection["potential"]
    rejected = selection["rejected_records"]
    rows = ["Camper van search — concise development report",
            "DEVELOPMENT REVIEW: known stock revisited; not newly advertised." if data.get("report_context") == "development_review" else "Weekly selection: new or materially updated evidence.",
            "Generated: " + str(data.get("generated_on", "unknown")),
            "Advertised search matches: " + str(len(selection["search_matches"])),
            "Verified >=90% qualifiers: " + str(len(qualified)) + " (purchase readiness; separate from search fit)",
            "Unchanged/relisted records suppressed: " + str(selection["unchanged_suppressed"]),
            "Individual vehicle records screened: " + str(len(results)),
            "Explicitly rejected: " + str(rejected),
            "CAUTION: discovery is incomplete; unknown VAT, route, availability and mechanical condition are not confirmations.",
            "", "QUALIFIED vehicles:"]
    def render_item(item):
        c = item["candidate"]
        from digest_details import details
        editorial = details(item)
        research_text = " | ".join(" ".join(note.get("findings", [])) + " Sources: " + ", ".join(source["url"] for source in note.get("sources", [])) for note in editorial["research_notes"][:2]) or "Exact drivetrain not sufficiently researched; no generic reliability claim."
        rows.extend(["- " + unescape(str(c.get("name", "Unknown"))),
                     "  Search status: " + item.get("search_assessment", {}).get("status", "unverified") + "; category " + editorial["category"],
                     "  Why investigate: " + editorial["why"],
                     "  Seller cautions: " + ("; ".join(c.get("advertised_cautions", [])) or "No specific seller caution extracted; condition remains unverified"),
                     "  Drivetrain research: " + research_text,
                     "  Weighted suitability: " + editorial["ranking"],
                     "  History: " + editorial["history"],
                     "  Seller questions: " + " | ".join(editorial["questions"]),
                     "  Pre-purchase: " + editorial["purchase_actions"],
                     "  Evidence score: " + str(item["score"]) + "%; " + candidate_state(item),
                     "  VAT-inclusive price: " + str(c.get("price_incl_vat") if c.get("price_incl_vat") is not None else "unverified"),
                     "  Driving route from Bergen op Zoom: " + str(c.get("distance_km") if c.get("distance_km") is not None else "unverified") + " km",
                     "  Listing: " + str(c.get("listing_url", "unavailable")),
                     "  Outstanding checks: " + ("; ".join(item["reasons"]) or "none"),
                     "  RDW concerns: " + ("; ".join(risk["message"] for risk in item.get("rdw_risks", [])) or "none reported; condition still unverified")])
    if qualified:
        for item in qualified:
            render_item(item)
    else:
        rows.append("None verified. This is not proof that none are for sale.")
    rows.extend(["", "SEARCH SHORTLIST — inspection pending (up to 5; conditional leads labeled separately):"])
    if potential:
        for item in potential:
            render_item(item)
    else:
        rows.append("No individual listing had enough relevant evidence for this shortlist.")
    health = data.get("coverage_health", {})
    rows.extend(["", "Coverage health: " + str(health.get("status", "no persisted monitoring history"))])
    for alert in health.get("alerts", []):
        rows.append("- " + alert["source"] + ": " + alert["severity"] + " — " + alert["message"])
    rows.extend(["", "Source coverage (individual vehicle pages):"])
    coverage = data.get("source_coverage", {})
    for source in SOURCES:
        entry = coverage.get(source, {})
        if not isinstance(entry, dict):
            rows.append("- " + source + ": not checked")
            continue
        rows.append("- " + source + ": " + str(entry.get("individual_pages_fetched", 0)) +
                    " fetched; " + str(entry.get("identity_bound_candidates", "unknown")) +
                    " identity-bound / " + str(entry.get("detail_urls_discovered", "?")) +
                    " discovered | " + str(entry.get("status", "unknown")))
        if source == "Local dealers":
            for dealer in entry.get("direct_dealers", []):
                rows.append("  Direct dealer " + str(dealer.get("name")) + ": " +
                            str(dealer.get("inventory_pages_fetched", 0)) + " inventory pages; " +
                            str(dealer.get("identity_bound_candidates", 0)) + " bound adverts; " +
                            str(dealer.get("index_exclusions", 0)) + " index exclusions; " +
                            str(dealer.get("status", "unknown")))
        if source == "AutoWereld":
            rows.append("  Direct GitHub-hosted page validation is separate from external Raspberry Pi RSS collection.")
            if entry.get("coverage_note") and not entry.get("external_rss_urls_accepted"):
                rows.append("  Coverage note: " + str(entry["coverage_note"]))
            rows.append("  External RSS status: " + str(entry.get("external_rss_snapshot_status", "unknown")) +
                        "; index URLs accepted: " + str(entry.get("external_rss_urls_accepted", 0)) +
                        "; these are NOT verified individual pages.")
        elif entry.get("coverage_note"):
            rows.append("  Coverage note: " + str(entry["coverage_note"]))
        if entry.get("source_block_reason"):
            rows.append("  Access restriction: " + str(entry["source_block_reason"]))
    rows.extend(["", "Screening summary by source:"])
    for source, stats in data.get("source_screening", {}).items():
        rows.append("- " + source + ": " + str(stats["total"]) + " examined; " +
                    str(stats["verified_prices"]) + " prices and " +
                    str(stats["verified_distances"]) + " routes verified; " +
                    str(stats["confirmed_plates"]) + " confirmed plates")
    rows.extend(["", "AutoWereld public RSS — UNVERIFIED leads (up to 5; not scored or recommended):"])
    rss_leads = data.get("unverified_rss_leads", [])
    selected = rss_shortlist(rss_leads, (x["candidate"].get("listing_url") for x in results))
    if not selected:
        rows.append("No RSS lead with a stated L2H2/L3H2 body and no obvious budget/body exclusion.")
    for lead in selected:
        title = unescape(" ".join(str(lead.get("title", ""))[:220].split()))
        rows.extend(["- " + title,
                     "  Seller's advertised price (VAT basis unknown): " +
                     (("€" + str(rss_price(lead.get("description")))) if rss_price(lead.get("description")) is not None else "unknown"),
                     "  Listing: " + str(lead.get("url", "")),
                     "  Status: RSS-only; VAT, distance, registration, availability and conversion suitability unverified."])
    rows.extend(["RSS leads are excluded from the verified >=90% qualification count.",
                 "", "Rejected listings and full RDW / APK evidence are retained in screening_results.json (GitHub Actions audit artifact).",
                 "APK approval is not a mechanical inspection; seller claims are not verified facts."])
    return "\n".join(rows) + "\n"

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",default="candidates.json")
    ap.add_argument("--history", help="Durable state file restored before this run")
    ap.add_argument("--run-id", help="Stable identity for idempotent reruns")
    ap.add_argument("--conversion-evidence", "--reviewed-evidence", dest="conversion_evidence", help="JSON containing explicit conversion requirements and reviewed assessments")
    args=ap.parse_args()
    data = json.loads(Path(args.input).read_text(encoding="utf8"))
    if args.conversion_evidence:
        data["conversion_evidence"] = json.loads(Path(args.conversion_evidence).read_text(encoding="utf8"))
    result=evaluate(data)
    if args.history:
        from search_history import update, validate
        if not args.run_id:
            ap.error("--history requires --run-id")
        history_path = Path(args.history)
        result, state = update(result, validate(json.loads(history_path.read_text())), args.run_id)
        history_path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n")
        Path("coverage_health.json").write_text(json.dumps(result["coverage_health"], indent=2, ensure_ascii=False) + "\n")
    Path("screening_results.json").write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding="utf8")
    Path("report.txt").write_text(report(result),encoding="utf8")
    from research_pack import build as build_research
    research = build_research(result, data.get("conversion_evidence", {}).get("requirements"))
    Path("research_pack.json").write_text(json.dumps(research, indent=2, ensure_ascii=False), encoding="utf8")
    Path("reviewed_evidence_template.json").write_text(json.dumps(research["review_template"], indent=2, ensure_ascii=False), encoding="utf8")
    print("Candidates:",len(result["results"]),"qualifiers:",result["qualifiers"])
    print("Local dealer vehicle screening:",json.dumps(dealer_audit_rows(result),ensure_ascii=False))
