#!/usr/bin/env python3
"""Append a strictly evidence-based live RDW probe summary to the dev report."""
import json
from pathlib import Path
import sys

def summary(data):
    entries=data.get("results",[])
    if len(entries)!=1:
        return "RDW probe incomplete: expected exactly one historical plate result."
    record=entries[0]
    vehicle=record.get("vehicle",{})
    defects=record.get("defects",{})
    if vehicle.get("status")!="ok" or not vehicle.get("records"):
        return "RDW probe incomplete: no actual vehicle registration record returned."
    fields=vehicle["records"][0]
    lines=["RDW live API verification (HISTORICAL TEST PLATE, NOT CURRENT LISTING):",
           "Registration: "+str(record.get("kenteken")),
           "Vehicle endpoint: record returned; defects endpoint: "+str(defects.get("status","unavailable"))]
    for key in ("vervaldatum_apk","tellerstandoordeel","toegestane_maximum_massa_voertuig","massa_ledig_voertuig"):
        lines.append(key+": "+str(fields.get(key,"not available")))
    if defects.get("status")=="ok":
        for entry in record.get("apk_defect_summary",{}).get("entries",[]):
            lines.append("Historic APK defect code: "+str(entry.get("defect_code"))+
                         " description: "+str(entry.get("description") or "not verified"))
    else:
        lines.append("APK defect history unavailable; no inference made.")
    return "\n".join(lines)

if __name__=="__main__":
    path=Path(sys.argv[1] if len(sys.argv)>1 else "rdw_probe.json")
    text=summary(json.loads(path.read_text(encoding="utf-8"))) if path.is_file() else "RDW probe unavailable; no JSON output."
    with open("report.txt","a",encoding="utf-8") as out:
        out.write("\n"+text+"\n")
    print(text)
