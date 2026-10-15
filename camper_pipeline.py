#!/usr/bin/env python3
"""Evidence-gated candidate screening and RDW lookup; does NOT discover listings."""
import argparse
from datetime import date
import json
from pathlib import Path
from urllib.parse import urlparse
from rdw_lookup import lookup, normalize_plate

SOURCES = ("Marktplaats","AutoScout24","Gaspedaal","AutoTrack","viaBOVAG","AutoWereld","Bedrijfsauto","TrucksNL","Local dealers")
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
    return {"generated_on":date.today().isoformat(),"source_coverage":data.get("source_coverage",{}),
            "results":results,"qualifiers":sum(x["qualified"] for x in results)}

def report(data):
    rows=["Camper van pipeline verification", "Generated: "+data["generated_on"],
          "Verified >=90% qualifiers: "+str(data["qualifiers"]),
          "LIMITATION: This job does not discover marketplace listings. No source is claimed searched automatically.",
          "", "Source coverage:"]
    rows += ["- "+s+": "+str(data["source_coverage"].get(s,"not checked")) for s in SOURCES]
    rows.append("\nRanked candidates / watchlist / rejections:")
    for item in sorted(data["results"],key=lambda x:x["score"],reverse=True):
        c=item["candidate"]
        rows.extend(["- "+str(c.get("name","Unknown"))+": "+str(item["score"])+"% | "+("QUALIFIER" if item["qualified"] else "WATCHLIST / REJECTED"),
                     "  Price including VAT: "+str(c.get("price_incl_vat","not confirmed")),
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
        rows.append("No independently confirmed candidate input. This is not proof that no matching vans are on sale.")
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
