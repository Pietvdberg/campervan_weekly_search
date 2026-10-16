#!/usr/bin/env python3
"""Evidence-gated candidate screening and RDW lookup for discovered listings."""
import argparse
from datetime import date
import json
from pathlib import Path
from urllib.parse import urlparse
from rdw_lookup import lookup, normalize_plate

SOURCES = ("Marktplaats","AutoScout24","AutoTrack","viaBOVAG","AutoWereld","Local dealers")
REQUIRED = ("high_roof","cab_ac","conversion_suitable","distance_within_100km","price_incl_vat_within_8000")

def screen(candidate):
    checks = candidate.get("checks", {})
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
    return {"candidate":candidate, "score":score, "plate":plate, "reasons":reasons, "qualified":score >= 90 and not reasons, "rdw":None}

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

def evaluate(data, rdw_lookup=lookup):
    results=[screen(c) for c in data.get("candidates",[])]
    for item in results:
        if not item["plate"]: continue
        try: item["rdw"]=rdw_lookup(item["plate"])
        except Exception as exc: item["rdw"]={"error":str(exc)}
        vehicle=item["rdw"].get("vehicle",{})
        if vehicle.get("status") != "ok" or not vehicle.get("records"):
            item["qualified"]=False
            item["reasons"].append("RDW registration not verified")
    return {"generated_on":date.today().isoformat(),"source_screening":evidence_summary(results),
            "source_coverage":data.get("source_coverage",{}),"discovery_method":data.get("discovery_method","no live discovery performed"),
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
    rows=["Camper van pipeline verification", "Generated: "+data["generated_on"],
          "Verified >=90% qualifiers: "+str(data["qualifiers"]),
          "Discovery: "+data.get("discovery_method","not performed"),
          "CAUTION: index results are incomplete; listing and location claims are unverified.",
          "", "Source coverage:"]
    for source in SOURCES:
        entry=data["source_coverage"].get(source,{})
        if not isinstance(entry,dict):
            rows.append("- "+source+": not checked")
            continue
        rows.append("- "+source+": "+str(entry.get("status","unknown"))+
                    " | inventory pages checked: "+str(entry.get("inventory_pages_checked","unknown"))+
                    " | individual URLs discovered: "+str(entry.get("detail_urls_discovered","unknown"))+
                    " | actual vehicle pages validated: "+str(entry.get("individual_pages_fetched",0)))
        if entry.get("coverage_note"):
            rows.append("  Coverage note: "+str(entry["coverage_note"]))
        if entry.get("source_block_reason"):
            rows.append("  Source access restriction: "+str(entry["source_block_reason"]))
        if entry.get("status") != "individual_pages_found":
            rows.append("  No verified individual adverts from this source is NOT proof of zero inventory.")
    rows.append("\\nScreening evidence by source:")
    for source,stats in data.get("source_screening",{}).items():
        rows.append("- "+source+": "+str(stats["total"])+" candidates; "+
            str(stats["verified_prices"])+" VAT-inclusive prices verified; "+
            str(stats["verified_distances"])+" driving routes verified; "+
            str(stats["confirmed_plates"])+" registration plates confirmed")
        for name,counts in stats["checks"].items():
            rows.append("  "+name+": passed "+str(counts["passed"])+
                ", failed "+str(counts["failed"])+", unknown "+str(counts["unknown"]))
    rows.append("\nRanked candidates / watchlist / rejections:")
    for item in sorted(data["results"],key=lambda x:x["score"],reverse=True):
        c=item["candidate"]
        rows.extend(["- "+str(c.get("name","Unknown"))+": "+str(item["score"])+"% | "+("QUALIFIER" if item["qualified"] else "WATCHLIST / REJECTED"),
                     "  Price including VAT: "+str(c.get("price_incl_vat") if c.get("price_incl_vat") is not None else "not confirmed")+" (basis: "+str(c.get("vat_basis","unknown"))+")",
                     "  Location: "+str(c.get("city_mentioned") or "unknown")+"; verified driving distance: "+str(c.get("distance_km") if c.get("distance_km") is not None else "unknown")+" km",
                     "  Listing: "+str(c.get("listing_url","unavailable")),
                     "  Reasons: "+("; ".join(item["reasons"]) or "none"),
                     "  Mechanical concerns: "+str(c.get("mechanical_concerns","not assessed"))])
        if item["plate"]:
            rows.append("  Plate independently confirmed: "+item["plate"])
            rdw=item["rdw"] or {}
            vehicle=rdw.get("vehicle",{})
            rows.append("  RDW status: "+str(vehicle.get("status","unavailable")))
            if vehicle.get("status")=="ok" and vehicle.get("records"):
                for field in ("vervaldatum_apk","tellerstandoordeel","toegestane_maximum_massa_voertuig","massa_ledig_voertuig"):
                    rows.append("  RDW "+field+": "+str(vehicle["records"][0].get(field,"not reported")))
            for defect in rdw.get("apk_defect_summary",{}).get("entries",[]):
                rows.append("  APK defect: "+str(defect.get("defect_code"))+" / "+str(defect.get("description") or "description unavailable"))
    if not data["results"]:
        rows.append("No candidate listing pages could be validated by this run. This is not proof that no matching vans are on sale.")
    rows.append("\nAPK approval is not a mechanical inspection; seller claims are not verified facts.")
    return "\n".join(rows)+"\n"

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",default="candidates.json")
    args=ap.parse_args()
    result=evaluate(json.loads(Path(args.input).read_text(encoding="utf8")))
    Path("screening_results.json").write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding="utf8")
    Path("report.txt").write_text(report(result),encoding="utf8")
    print("Candidates:",len(result["results"]),"qualifiers:",result["qualifiers"])
    print("Local dealer vehicle screening:",json.dumps(dealer_audit_rows(result),ensure_ascii=False))
