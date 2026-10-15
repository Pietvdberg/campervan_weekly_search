#!/usr/bin/env python3
"""Best-effort public search-index discovery. Explicitly reports coverage gaps."""
import argparse
from datetime import datetime, timezone
import html
import json
from pathlib import Path
import re
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

SOURCES = {
    "Marktplaats": "marktplaats.nl",
    "AutoScout24": "autoscout24.nl",
    "Gaspedaal": "gaspedaal.nl",
    "AutoTrack": "autotrack.nl",
    "viaBOVAG": "viabovag.nl",
    "AutoWereld": "autowereld.nl",
    "Bedrijfsauto": "bedrijfsauto.nl",
    "TrucksNL": "trucksnl.com",
    "Local dealers": None,
}
MODEL = re.compile(r"\b(boxer|jumper|ducato|transit|master|movano|sprinter|crafter|daily|transporter|nv400)\b",re.I)
ROOF = re.compile(r"\bL[234]H[23]\b|\bhoog ?dak\b",re.I)
AC = re.compile(r"\b(airco|airconditioning|climate control)\b",re.I)
CITIES = ("bergen op zoom","roosendaal","zevenbergen","breda","etten-leur","halsteren","steenbergen","tholen","goes","tilburg","dordrecht","rotterdam","oosterhout","hoogerheide","rucphen")
MAX_BYTES=900000

def fetch(url):
    req=Request(url,headers={"User-Agent":"Mozilla/5.0 CamperVanResearch/1.0","Accept":"text/html,application/rss+xml,application/xml"})
    with urlopen(req,timeout=12) as response:
        raw=response.read(MAX_BYTES+1)
        if len(raw)>MAX_BYTES: raise ValueError("oversized response")
        return raw.decode("utf-8",errors="replace"),response.headers.get("Content-Type","")

def search_links(xml):
    root=ET.fromstring(xml)
    return [(x.findtext("title") or "",x.findtext("link") or "") for x in root.findall(".//item") if x.findtext("link")]

def valid_url(url,source):
    parsed=urlparse(url)
    host=(parsed.hostname or "").lower()
    domain=SOURCES[source]
    if parsed.scheme!="https": return False
    if domain and not (host==domain or host.endswith("."+domain)): return False
    if source=="Local dealers" and not host.endswith(".nl"): return False
    path=parsed.path.lower()
    if source=="Marktplaats": return bool(re.search(r"/v/[^/]+/[^/]+/m\d+",path))
    if source=="AutoScout24": return path.startswith("/aanbod/") and path.count("/")>=2
    if source=="AutoTrack": return "/aanbod/" in path and path.count("/")>=4
    return len([s for s in path.split("/") if s])>=2

def extract(title,url,source,markup):
    no_scripts=re.sub(r"<(?:script|style)\b[^>]*>.*?</(?:script|style)>"," ",markup,flags=re.I|re.S)
    text=" ".join(html.unescape(re.sub(r"<[^>]+>"," ",no_scripts)).split())
    header=title+" "+text[:5000]
    if not MODEL.search(header): return None
    checks={key:None for key in ("high_roof","cab_ac","conversion_suitable","distance_within_100km","price_incl_vat_within_8000")}
    if ROOF.search(header): checks["high_roof"]=True
    if AC.search(header): checks["cab_ac"]=True
    checks["conversion_suitable"]=True  # model-category proxy; payload and dimensions still unknown
    city=next((x for x in CITIES if re.search(r"\b"+re.escape(x)+r"\b",header,re.I)),None)
    # Mention of a nearby town is NOT independent verification of driving distance.
    plate_hit=re.search(r"(?:kenteken|nummerplaat|registratie)\s*[:\-]?\s*([A-Z0-9]{2,3}-[A-Z0-9]{2,3}-[A-Z0-9]{1,3})\b",text,re.I)
    plate=plate_hit.group(1) if plate_hit else None
    price_hit=re.search(r"(?:€|EUR)\s*([\d.]+(?:,\d{2})?)",header,re.I)
    title_match=re.search(r"<title[^>]*>(.*?)</title>",markup,re.I|re.S)
    name=(" ".join(html.unescape(title_match.group(1)).split()) if title_match else title)[:180]
    return {"name":name,"source":source,"listing_url":url,"individual_listing_confirmed":True,
            "checks":checks,"plate":plate,"plate_confirmed_from_listing":bool(plate),
            "city_mentioned":city,"price_advertised":price_hit.group(1) if price_hit else None,
            "price_incl_vat":None,"mechanical_concerns":"Service history, rust, driveline, cab A/C operation and payload unverified.",
            "evidence_note":"Individual page returned HTML; text matches are advertised claims. Status/availability not independently confirmed.",
            "observed_at":datetime.now(timezone.utc).isoformat()}

def discover(fetcher=fetch,max_per_source=4):
    coverage={};candidates=[];seen=set()
    for source,domain in SOURCES.items():
        query=("site:"+domain+" " if domain else "")+'("L2H2" OR "L3H2") (boxer OR jumper OR ducato OR transit OR master) airco bestelbus'
        if source=="Local dealers": query+=' ("Roosendaal" OR "Breda" OR "Bergen op Zoom")'
        rss="https://www.bing.com/search?"+urlencode({"q":query,"format":"rss"})
        try:
            xml,_=fetcher(rss)
            hits=search_links(xml)
            found=0;failures=0
            for title,url in hits[:25]:
                if found>=max_per_source: break
                if url in seen or not valid_url(url,source): continue
                seen.add(url)
                try:
                    markup,ctype=fetcher(url)
                    if "html" not in ctype.lower(): failures+=1;continue
                    item=extract(title,url,source,markup)
                    if item: candidates.append(item);found+=1
                except Exception:
                    failures+=1
            coverage[source]={"status":"partial_index_search","index_hits":len(hits),"individual_pages_fetched":found,
                              "fetch_errors":failures,"method":"public Bing RSS index; NOT complete source inventory"}
        except Exception as exc:
            coverage[source]={"status":"unavailable","error":str(exc)[:160],"individual_pages_fetched":0}
    return {"candidates":candidates,"source_coverage":coverage,
            "discovery_method":"Best-effort public index. No completeness, distance, VAT or availability guarantee."}

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",default="discovered_candidates.json")
    args=parser.parse_args()
    result=discover()
    Path(args.output).write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("Candidate pages:",len(result["candidates"]))
    print(json.dumps(result["source_coverage"],indent=2))
