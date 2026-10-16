#!/usr/bin/env python3
"""Best-effort public search-index discovery. Explicitly reports coverage gaps."""
import argparse
from datetime import datetime, timezone
import html
import os
import json
from pathlib import Path
import re
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET
from listing_evidence import enrich, structured
from inventory_discovery import crawl as crawl_inventory, classify as classify_inventory
from browser_render import render as browser_render
from html.parser import HTMLParser
from urllib.parse import urljoin,urldefrag

SOURCES = {
    "Marktplaats": "marktplaats.nl",
    "AutoScout24": "autoscout24.nl",
    "wijkopenautos": "wijkopenautos.nl",
    "AutoTrack": "autotrack.nl",
    "viaBOVAG": "viabovag.nl",
    "AutoWereld": "autowereld.nl",
    "Bedrijfsauto": "bedrijfsauto.nl",
    "TrucksNL": "trucksnl.com",
    "Local dealers": None,
}
# Direct category/dealer entry points. A returned page is not proof of complete inventory.
SEED_PAGES = {
    "Marktplaats": ["https://www.marktplaats.nl/l/auto-s/bestelauto-s/q/boxer+l2h2/","https://www.marktplaats.nl/l/auto-s/bestelauto-s/q/transit+l2h2/"],
    "wijkopenautos": ["https://www.wijkopenautos.nl/auto-kopen/"],
    "AutoScout24": ["https://www.autoscout24.nl/lst/peugeot/boxer","https://www.autoscout24.nl/lst/ford/transit"],
    "AutoTrack": ["https://www.autotrack.nl/"],
    "viaBOVAG": ["https://www.viabovag.nl/auto/merk-peugeot/model-boxer/occasion","https://www.viabovag.nl/auto/merk-ford/model-transit/occasion","https://www.viabovag.nl/"],
    "AutoWereld": ["https://www.autowereld.nl/aanbieder/bedrijfswagencentrum-roosendaal-b-v-6035/auto.html","https://www.autowereld.nl/aanbieder/mana-bedrijfswagens-910447/auto.html"],
    "Bedrijfsauto": ["https://www.bedrijfsauto.nl/"],
    "TrucksNL": ["https://www.trucksnl.com/"],
    "Local dealers": [
        "https://www.autowereld.nl/aanbieder/bedrijfswagencentrum-roosendaal-b-v-6035/auto.html",
        "https://www.autowereld.nl/aanbieder/mana-bedrijfswagens-910447/auto.html",
        "https://www.autowereld.nl/aanbieder/louwman-mercedes-benz-bedrijfswagens-roosendaal-1306925/auto.html",
        "https://www.autowereld.nl/aanbieder/volkswagen-breda-10209/auto.html",
        "https://www.autowereld.nl/aanbieder/louwman-mercedes-benz-bedrijfswagens-goes-1306923/auto.html",
        "https://www.autowereld.nl/aanbieder/van-mossel-breda-1013023/auto.html",
        "https://www.autowereld.nl/aanbieder/auto-goes-5455/auto.html",
        "https://www.vanmossel.nl/vestigingen/van-mossel-renault-dacia-roosendaal"],
}

MODEL = re.compile(r"\b(boxer|jumper|ducato|transit|master|movano|sprinter|crafter|daily|transporter|nv400)\b",re.I)
ROOF = re.compile(r"\bL[234]H[23]\b|\bhoog ?dak\b",re.I)
AC = re.compile(r"\b(airco|airconditioning|climate control)\b",re.I)
CITIES = ("bergen op zoom","roosendaal","zevenbergen","breda","etten-leur","halsteren","steenbergen","tholen","goes","tilburg","dordrecht","rotterdam","oosterhout","hoogerheide","rucphen")
MAX_BYTES=2600000
MAX_FETCH_ATTEMPTS=50

class LinkCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.href = None
        self.label = []
    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.href = dict(attrs).get("href")
            self.label = []
    def handle_data(self, data):
        if self.href is not None:
            self.label.append(data)
    def handle_endtag(self, tag):
        if tag == "a" and self.href is not None:
            self.links.append((" ".join(" ".join(self.label).split()), self.href))
            self.href = None

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
    if source=="Local dealers" and not any(host == d or host.endswith("."+d) for d in ("autowereld.nl","vanmossel.nl")): return False
    path=parsed.path.lower()
    if source=="Marktplaats": return bool(re.search(r"/v/[^/]+/[^/]+/m\d+",path))
    if source=="AutoScout24": return path.startswith("/aanbod/") and path.count("/")>=2
    if source=="AutoTrack": return "/aanbod/" in path and not any(x in path for x in ("/brandstofsoort/","/carrosserievorm/","/merk/","/prijs/","/bouwjaar/")) and path.count("/")>=3
    if source=="viaBOVAG": return classify_inventory(url,source)=="detail"
    if source in ("Local dealers","AutoWereld") and "/aanbieder/" in path: return False
    if source=="Local dealers" and ("/regio/" in path or "/blog/" in path): return False
    if source=="Local dealers" and host.endswith("vanmossel.nl") and "/vestigingen/" in path: return False
        if source=="wijkopenautos": return "/auto-kopen/" in path and path.rstrip("/") not in ("/auto-kopen","/auto-kopen/favorieten")
    if source in ("Local dealers","AutoWereld") and "/aanbieder/" in path: return False
    if source=="Bedrijfsauto" and ("/lease/" in path or path.rstrip("/") in ("/aanbod","/aanbod/volkswagen","/aanbod/mercedes-benz")): return False

    return len([s for s in path.split("/") if s])>=2

def relevant_link(title,url,source):
    """Prioritize van-specific individual links over vehicle taxonomies and generic pages."""
    if source=="Marktplaats": return True
    return bool(MODEL.search(title+" "+urlparse(url).path.replace("-"," ")))

def is_vehicle_detail(url, source, markup):
    """Reject category/search pages that mention many vehicles.

    For non-Marktplaats domains require a vehicle's page-level identity:
    structured Car/Vehicle object or an explicitly labeled registration plate.
    Search-result grids and model directories do not satisfy this gate.
    """
    if source=="Marktplaats":
        return True  # Marktplaats /v/.../m<ID> is a specific advert URL.
    types={"vehicle","car","product"}
    nodes=structured(markup)
    vehicles=[]
    for node in nodes:
        raw_type=node.get("@type",[])
        names=[raw_type] if isinstance(raw_type,str) else raw_type if isinstance(raw_type,list) else []
        if any(str(x).lower() in types for x in names):
            vehicles.append(node)
    if len(vehicles)==1:
        node=vehicles[0]
        if node.get("name") and (node.get("offers") or node.get("vehicleIdentificationNumber") or node.get("sku")):
            return True
    # Explicit plate is useful when a site omits structured vehicle data.
    plain=" ".join(html.unescape(re.sub(r"<[^>]+>"," ",markup)).split())
    return bool(re.search(r"\\b(?:kenteken|nummerplaat)\\s*[:\\-]?\\s*[A-Z0-9]{1,3}-[A-Z0-9]{1,3}-[A-Z0-9]{1,3}\\b",plain,re.I))

def extract(title,url,source,markup):
    no_scripts=re.sub(r"<(?:script|style)\b[^>]*>.*?</(?:script|style)>"," ",markup,flags=re.I|re.S)
    text=" ".join(html.unescape(re.sub(r"<[^>]+>"," ",no_scripts)).split())
    header=title+" "+text[:5000]
    if not MODEL.search(header) or not is_vehicle_detail(url,source,markup): return None
    checks={key:None for key in ("high_roof","cab_ac","conversion_suitable","distance_within_100km","price_incl_vat_within_8000")}
    if ROOF.search(header): checks["high_roof"]=True
    if AC.search(header): checks["cab_ac"]=True
    # Conversion suitability requires independently checked payload and dimensions.
    city=next((x for x in CITIES if re.search(r"\b"+re.escape(x)+r"\b",header,re.I)),None)
    # Mention of a nearby town is NOT independent verification of driving distance.
    plate_hit=re.search(r"(?:kenteken|nummerplaat|registratie)\s*[:\-]?\s*([A-Z0-9]{1,3}-[A-Z0-9]{1,3}-[A-Z0-9]{1,3})\b",text,re.I)
    plate=plate_hit.group(1) if plate_hit else None
    price_hit=re.search(r"(?:€|EUR)\s*([\d.]+(?:,\d{2})?)",header,re.I)
    title_match=re.search(r"<title[^>]*>(.*?)</title>",markup,re.I|re.S)
    name=(" ".join(html.unescape(title_match.group(1)).split()) if title_match else title)[:180]
    evidence=enrich(markup)
    checks.update(evidence["checks"])
    return {"name":name,"source":source,"listing_url":url,"individual_listing_confirmed":True,
            "checks":checks,"plate":plate,"plate_confirmed_from_listing":bool(plate),
            "city_mentioned":city,"price_advertised":price_hit.group(1) if price_hit else None,
            "price_incl_vat":evidence["vat"]["amount_incl_vat"],"vat_basis":evidence["vat"]["basis"],
            "distance_km":evidence["distance_km"],"location_coordinates":evidence["location_coordinates"],
            "mechanical_concerns":"Service history, rust, driveline, cab A/C operation and payload unverified.",
            "evidence_note":"Individual page returned HTML; structured price and GPS evidence can be checked, but seller claims and actual condition remain unverified.",
            "observed_at":datetime.now(timezone.utc).isoformat()}

def discover(fetcher=fetch,max_per_source=50):
    coverage={};candidates=[];seen=set()
    for source,domain in SOURCES.items():
        direct_urls = {}
        inventory_stats = None
        seed_success = 0
        seed_errors = []
        anchor_count = 0
        if source in ("Gaspedaal","viaBOVAG"):
            inventory_stats=crawl_inventory(source,SEED_PAGES[source],fetcher)
            direct_urls.update(inventory_stats["details"])
            seed_success=inventory_stats["inventory_pages_accessible"]
            seed_errors=[x["error"] for x in inventory_stats["inventory_errors"]]
            anchor_count=inventory_stats["inventory_links_examined"]
        for seed in ([] if inventory_stats is not None else SEED_PAGES[source]):
            try:
                page, typ = fetcher(seed)
                if "html" not in typ.lower(): raise ValueError("non-HTML inventory page")
                seed_success += 1
                parser = LinkCollector()
                parser.feed(page)
                if not parser.links and os.environ.get("ENABLE_BROWSER_RENDER")=="1":
                    page,typ=browser_render(seed)
                    parser=LinkCollector()
                    parser.feed(page)
                anchor_count += len(parser.links)
                for label, href in parser.links:
                    url = urldefrag(urljoin(seed, href))[0]
                    if valid_url(url,source) and relevant_link(label,url,source): direct_urls.setdefault(url,label)
            except Exception as exc:
                if len(seed_errors)<4: seed_errors.append(str(exc)[:140])
        query=("site:"+domain+" " if domain else "")+'("L2H2" OR "L3H2") (boxer OR jumper OR ducato OR transit OR master) airco bestelbus'
        if source=="Local dealers": query+=' ("Roosendaal" OR "Breda" OR "Bergen op Zoom")'
        rss="https://www.bing.com/search?"+urlencode({"q":query,"format":"rss"})
        try:
            try:
                xml,_=fetcher(rss)
                hits=search_links(xml)
                index_error=None
            except Exception as exc:
                hits=[]
                index_error=str(exc)[:140]
            found=0;failures=0;rejected=0;matched=0;samples=[];attempts=0;rate_limited=False
            for title,url in [(title,url) for url,title in direct_urls.items()] + hits[:25]:
                if found>=max_per_source or attempts>=MAX_FETCH_ATTEMPTS or rate_limited: break
                if url in seen: continue
                if not valid_url(url,source) or not relevant_link(title,url,source):
                    rejected+=1
                    if len(samples)<3: samples.append({"reason":"not an eligible individual listing URL","url":url[:250]})
                    continue
                matched+=1
                attempts+=1
                seen.add(url)
                try:
                    markup,ctype=fetcher(url)
                    if "html" not in ctype.lower():
                        failures+=1
                        if len(samples)<3: samples.append({"reason":"non-HTML listing response","url":url[:250]})
                        continue
                    item=extract(title,url,source,markup)
                    if item is None and os.environ.get("ENABLE_BROWSER_RENDER")=="1" and "__NEXT_DATA__" in markup:
                        rendered,_=browser_render(url)
                        item=extract(title,url,source,rendered)
                    if item: candidates.append(item);found+=1
                    elif len(samples)<3: samples.append({"reason":"individual vehicle evidence missing or wrong model","url":url[:250]})
                except Exception as exc:
                    failures+=1
                    if "429" in str(exc): rate_limited=True
                    if len(samples)<3: samples.append({"reason":str(exc)[:90],"url":url[:250]})
            status=("individual_pages_found" if found else
                    "source_unavailable" if seed_success==0 else
                    "inventory_only_unverified" if inventory_stats is not None else
                    "no_verified_individual_pages")
            coverage[source]={"status":status,
                              "inventory_pages":len(SEED_PAGES[source]),"inventory_pages_fetched":seed_success,
                              "inventory_pages_checked":inventory_stats["inventory_pages_checked"] if inventory_stats else seed_success,
                              "inventory_pages_pending":inventory_stats["inventory_pending"] if inventory_stats else None,
                              "inventory_diagnostics":inventory_stats["inventory_diagnostics"] if inventory_stats else [],
                              "inventory_links":anchor_count,"direct_eligible_urls":len(direct_urls),
                              "inventory_errors":seed_errors,"index_error":index_error,
                              "index_hits":len(hits),"detail_urls_discovered":len(direct_urls),"eligible_urls":matched,
                              "attempts":attempts,"rate_limited":rate_limited,"rejected_index_urls":rejected,
                              "individual_pages_fetched":found,"fetch_errors":failures,"diagnostic_samples":samples,
                              "method":"bounded inventory traversal, individual-detail validation, untrusted Bing fallback"}
        except Exception as exc:
            coverage[source]={"status":"unavailable","error":str(exc)[:160],"individual_pages_fetched":0,
                              "inventory_pages_fetched":seed_success,"direct_eligible_urls":len(direct_urls),"inventory_errors":seed_errors}
    return {"candidates":candidates,"source_coverage":coverage,
            "discovery_method":"Inventory pages are traversed separately from individual vehicle URLs. Sources with no validated vehicles are not presumed to have no stock; no completeness, VAT, distance or availability guarantee."}

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",default="discovered_candidates.json")
    args=parser.parse_args()
    result=discover()
    Path(args.output).write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("Candidate pages:",len(result["candidates"]))
    print(json.dumps(result["source_coverage"],indent=2))
