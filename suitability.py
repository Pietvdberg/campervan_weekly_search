"""Specification §44 weighted suitability; unknowns never receive invented scores."""
import json
from datetime import date
from math import isfinite
from pathlib import Path
from urllib.parse import urlparse

WEIGHTS = dict(zip(("reliability", "european_repairability", "performance", "parts_availability",
    "low_running_costs", "kitchen_suitability", "storage", "purchase_price", "maintenance_cost",
    "vehicle_availability", "interior_space", "payload", "driving_comfort", "off_grid_capability",
    "conversion_ease", "water_capability", "winter_capability", "rough_road_capability", "fuel_economy",
    "electrical_capability", "emissions", "toilet_integration", "exterior_compactness", "safety",
    "camper_aftermarket", "stealth", "road_tax", "insurance", "modern_technology", "resale_value",
    "appearance", "automatic_transmission"),
    (10,9,8,8,8,8,7.5,7,7,7,7,7,7,7,7,7,7,7,6,6,6,6,5,5,5,5,5,5,4,4,3,2)))
CRITICAL = ("reliability", "european_repairability", "parts_availability")
RESEARCH = Path(__file__).with_name("variant_research.json")


def valid_reference(value):
    try:
        p = urlparse(value) if isinstance(value, str) else None
        return bool(p and p.scheme == "https" and p.hostname and not p.username and not p.password)
    except ValueError:
        return False


def variant_research(candidate, registry=None, today=None):
    registry = json.loads(RESEARCH.read_text()) if registry is None else registry
    variant = candidate.get("variant", {})
    variant = variant if isinstance(variant, dict) else {}
    inferred = []
    if not variant and len(candidate.get("variant_clues", [])) == 1:
        import re
        clue = candidate["variant_clues"][0]
        variant = {key: clue[key] for key in ("make", "model") if isinstance(clue.get(key), str)}
        description = str(clue.get("modelVersionInput") or "")
        year = str(clue.get("productionYear") or clue.get("firstRegistrationDateRaw") or "")[:4]
        if variant.get("model") == "Boxer" and year.isdigit() and 2007 <= int(year) <= 2013:
            variant["generation"] = "II 2006-2014"
            inferred.append("generation")
        model_year = int(year) if year.isdigit() else None
        generations = {("Volkswagen", "Transporter"): (2004, 2008, "T5 pre-facelift"),
                       ("Ford", "Transit"): (2007, 2012, "Mk7 2006-2013")}
        scope = generations.get((variant.get("make"), variant.get("model")))
        if scope and model_year and scope[0] <= model_year <= scope[1]:
            variant["generation"] = scope[2]
            inferred.append("generation")
        registration_year = str(clue.get("firstRegistrationDateRaw") or "")[:4]
        if registration_year.isdigit():
            variant["first_registration_year"] = registration_year
        engine_pattern = r"\b([123][.,][0-9])\s*(BlueHDi|HDi|MultiJet|TDCi|TDI)\b"
        engine = re.search(engine_pattern, description, re.I) or re.search(engine_pattern, str(clue.get("motorTypeName") or ""), re.I)
        if engine:
            labels = {s.casefold(): s for s in ("BlueHDi", "HDi", "MultiJet", "TDCi", "TDI")}
            variant["engine"] = engine.group(1).replace(",", ".") + " " + labels[engine.group(2).casefold()]
        transmission = str(clue.get("transmissionType")).casefold()
        gearbox = "manual" if transmission in ("manual", "handgeschakeld", "schaltgetriebe") else "automatic" if transmission in ("automatic", "automatisch", "automatik") else None
        if gearbox and str(clue.get("gears")) in ("4", "5", "6", "7", "8", "9", "10"):
            variant["gearbox"] = str(clue["gears"]) + "-speed " + gearbox
        if isinstance(clue.get("powerInHp"), str):
            variant["advertised_power"] = clue["powerInHp"]
        body = re.search(r"\bL[1-4][ .-]*H[1-3]\b", description, re.I)
        if body:
            variant["body"] = re.sub(r"[ .-]", "", body.group()).upper()
        elif clue.get("advertisedBody"):
            variant["body"] = clue["advertisedBody"]

    fields = ("make", "model", "generation", "engine", "gearbox", "body")
    matches = []
    for entry in registry:
        selector = entry.get("applies_to", {})
        if not selector or not all(variant.get(key) == value for key, value in selector.items()):
            continue
        try:
            current = date.fromisoformat(entry["reviewed_on"]) <= (today or date.today()) <= date.fromisoformat(entry["review_by"])
        except (KeyError, ValueError, TypeError):
            current = False
        if current and all(valid_reference(source.get("url")) for source in entry.get("sources", [])) and entry.get("sources"):
            matches.append(entry)
    exact = not inferred and all(isinstance(variant.get(key), str) and variant[key].strip() for key in fields)
    return {"variant": variant, "inferred_identity_fields": inferred, "exact_variant_identified": exact, "missing_identity": [key for key in fields if not variant.get(key)],
            "notes": matches, "status": "sourced" if matches else "not_researched",
            "note": "Sources describe variant risks, not current faults or population failure rates. Unmatched variants remain unresearched."}


def rank(item, registry=None):
    c = item["candidate"]
    research = variant_research(c, registry)
    facts = {}
    # Explicitly reproducible preference mapping: target <=5k gets 10; ceiling 8k gets 4.
    price = c.get("price_incl_vat")
    if isinstance(price, (int, float)) and not isinstance(price, bool) and isfinite(price) and 0 < price <= 8000:
        facts["purchase_price"] = {"score": max(4, 10 - max(0, price - 5000) / 500),
                                    "confidence": "high", "source_url": c.get("listing_url"),
                                    "reason": "User target EUR 5,000; ceiling EUR 8,000 (linear preference mapping)."}
    supplied = c.get("suitability_evidence", {})
    supplied = supplied if isinstance(supplied, dict) else {}
    for key, fact in supplied.items():
        if key not in WEIGHTS or not isinstance(fact, dict):
            continue
        value = fact.get("score")
        if (isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value) and 0 <= value <= 10
                and valid_reference(fact.get("source_url")) and fact.get("confidence") in ("medium", "high")
                and isinstance(fact.get("reason"), str) and fact["reason"].strip()):
            # Drivetrain judgements need exact identity and cited variant research.
            if key in CRITICAL + ("performance", "maintenance_cost") and (not research["exact_variant_identified"] or not research["notes"]):
                continue
            facts[key] = fact
    known_weight = sum(WEIGHTS[key] for key in facts)
    score = 10 * sum(WEIGHTS[key] * fact["score"] for key, fact in facts.items()) / known_weight if known_weight else None
    coverage = 100 * known_weight / sum(WEIGHTS.values())
    critical = all(key in facts for key in CRITICAL)
    # A high price score alone never earns A/B or a full reliability ranking.
    category = "D" if item.get("search_assessment", {}).get("status") == "REJECTED" else "C"
    if item.get("search_assessment", {}).get("matched") and critical:
        if coverage >= 70 and score >= 80:
            category = "A"
        elif coverage >= 50 and score >= 65:
            category = "B"
    return {"category": category, "weighted_score_known_criteria": round(score, 1) if score is not None else None,
            "weighted_coverage_percent": round(coverage, 1), "critical_research_supported": critical,
            "criteria": facts, "unknown_criteria": [key for key in WEIGHTS if key not in facts],
            "research": research, "note": "Weighted suitability over supported criteria only; coverage is separate from the search checklist and purchase readiness."}
