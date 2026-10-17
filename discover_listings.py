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
from listing_evidence import enrich, structured, PLATE
from listing_identity import bind_evidence, require_same_listing
from source_access import SourceFetch, host_key
from vehicle_risks import auction_evidence, mechanical_failure
from rdw_lookup import normalize_plate
from discovery_queue import cards as inventory_cards, select as select_queue, budget_applied
from dealer_sources import dealer_for_url, crawl_dealers, load_registry
from validate_search import code_fingerprint
from marketplace_links import extract as extract_marketplace_links, diagnostics as marketplace_diagnostics
from autowereld_html import html_to_xml, response_identity
from autowereld_snapshot import read_snapshot_records
from inventory_discovery import crawl as crawl_inventory, classify as classify_inventory
from browser_render import render as browser_render
from html.parser import HTMLParser
from urllib.parse import urljoin,urldefrag

from source_catalog import SOURCE_DOMAINS as SOURCES, SEED_PAGES, VAN_MODEL as MODEL, INVENTORY_SEEDS, BUDGET_PAGES

ROOF = re.compile(r"\bL[234][ .-]*H[23]\b|\bhoog ?dak\b",re.I)
AC = re.compile(r"\b(airco|airconditioning|climate control)\b",re.I)
CITIES = ("bergen op zoom","roosendaal","zevenbergen","breda","etten-leur","halsteren","steenbergen","tholen","goes","tilburg","dordrecht","rotterdam","oosterhout","hoogerheide","rucphen")
MAX_BYTES=2600000
MAX_FETCH_ATTEMPTS=50
AUTOWERELD_RSS = [
    "https://www.autowereld.nl/rss/peugeot/boxer/",
    "https://www.autowereld.nl/rss/ford/transit/",
    "https://www.autowereld.nl/rss/citroen/jumper/",
    "https://www.autowereld.nl/rss/fiat/ducato/",
    "https://www.autowereld.nl/rss/renault/master/",
]

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
        require_same_listing(url, response.geturl(), inventory=url in INVENTORY_SEEDS or any(url == dealer["inventory_url"] for dealer in load_registry()))
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
    if source=="Local dealers" and dealer_for_url(url, detail=True): return True
    if source=="Local dealers" and not any(host == d or host.endswith("."+d) for d in ("autowereld.nl","vanmossel.nl")): return False
    path=parsed.path.lower()
    if source=="Marktplaats": return bool(re.search(r"/v/[^/]+/[^/]+/m\d+",path))
    if source=="AutoScout24": return bool(re.fullmatch(r"/aanbod/[a-z0-9_-]+-[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}/?",path))
    if source=="AutoTrack": return bool(re.fullmatch(r"/a/[a-z0-9_-]+-(?:\d{6,}|[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12})/?",path))
    if source=="AutoWereld": return bool(re.fullmatch(r"/[a-z0-9-]+/[a-z0-9-]+/[a-z0-9-]+-\d+/details\.html",path))
    if source=="viaBOVAG": return classify_inventory(url,source)=="detail"
    if source in ("Local dealers","AutoWereld") and "/aanbieder/" in path: return False
    if source=="Local dealers" and ("/regio/" in path or "/blog/" in path): return False
    if source=="Local dealers" and host.endswith("autowereld.nl"):
        return bool(re.fullmatch(r"/[a-z0-9-]+/[a-z0-9-]+/[a-z0-9-]+-\d+/details\.html",path))
    if source=="Local dealers" and host.endswith("vanmossel.nl"):
        # Dealer stock URLs must be vehicle-specific; branch and inventory pages are not listings.
        return bool(re.fullmatch(r"/[a-z0-9-]+/(?:voorraad|occasions)/\d{6,}-[a-z0-9-]+/?",path))
    if source in ("Local dealers","AutoWereld") and "/aanbieder/" in path: return False

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
    if not valid_url(url, source):
        return False
    if source in ("Marktplaats","AutoTrack","AutoScout24","AutoWereld","Local dealers"):
        # These strict vehicle-specific URLs identify an individual advert.
        return valid_url(url,source)
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
    return bool(PLATE.search(plain))

def advertised_feature(text, pattern):
    """Interpret explicit seller denials before positive feature mentions.

    Conflicting mentions stay unknown. This describes the advert, not a
    functional inspection of the equipment.
    """
    states = []
    for match in pattern.finditer(text):
        before = text[max(0, match.start() - 45):match.start()]
        after = text[match.end():match.end() + 45]
        negative = (
            re.search(r"\b(?:geen|zonder|niet|no|without)\s+(?:(?:werkende|functionerende|een|a|working)\s+){0,2}$", before, re.I)
            or re.match(r"\s*(?:[:=—–-]\s*)?(?:nee|no|niet\s+(?:aanwezig|werkend|functionerend)|werkt\s+niet|defect|kapot|ontbreekt)\b", after, re.I)
        )
        states.append(not bool(negative))
    if not states or len(set(states)) > 1:
        return None
    return states[0]


def extract(title,url,source,markup):
    if re.search(r"<title[^>]*>\s*(?:access denied|forbidden|just a moment|captcha|verify you are human|toegang geweigerd)[^<]*</title>",markup[:10000],re.I):
        return None
    no_scripts=re.sub(r"<(?:script|style)\b[^>]*>.*?</(?:script|style)>"," ",markup,flags=re.I|re.S)
    text=" ".join(html.unescape(re.sub(r"<[^>]+>"," ",no_scripts)).split())
    header=title+" "+text[:5000]
    # A title supplied by a directory is not proof that the response is a listing.
    if not MODEL.search(text[:5000]):
        return None
    if not is_vehicle_detail(url,source,markup): return None
    try:
        scoped_markup, provenance = bind_evidence(markup, url)
    except ValueError:
        return None
    scoped_text = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", re.sub(
        r"<script\b[^>]*>.*?</script>", " ", scoped_markup, flags=re.I|re.S))).split())
    checks={key:None for key in ("high_roof","cab_ac","conversion_suitable","distance_within_100km","price_incl_vat_within_8000")}
    checks["high_roof"] = advertised_feature(scoped_text, ROOF)
    page_title = re.search(r"<title[^>]*>(.*?)</title>", markup, re.I|re.S)
    primary_title = html.unescape(page_title.group(1)) if page_title else ""
    if re.search(r"\bL[1-4]\s*H1\b", primary_title, re.I):
        checks["high_roof"] = False
    checks["cab_ac"] = advertised_feature(scoped_text, AC)
    # Conversion suitability requires independently checked payload and dimensions.
    city=next((x for x in CITIES if re.search(r"\b"+re.escape(x)+r"\b",header,re.I)),None)
    # Mention of a nearby town is NOT independent verification of driving distance.
    plate_values = PLATE.findall(scoped_text)
    scoped_objects = structured(scoped_markup)
    plate_values.extend(node["licensePlate"] for node in scoped_objects if isinstance(node.get("licensePlate"), str))
    normalized_plates = {}
    for value in plate_values:
        try:
            normalized_plates.setdefault(normalize_plate(value), value)
        except ValueError:
            continue
    plate = next(iter(normalized_plates.values())) if len(normalized_plates) == 1 else None
    price_hit=re.search(r"(?:€|EUR)\s*([\d.]+(?:,\d{2})?)",scoped_text,re.I)
    title_match=re.search(r"<title[^>]*>(.*?)</title>",markup,re.I|re.S)
    name=(" ".join(html.unescape(title_match.group(1)).split()) if title_match else title)[:180]
    evidence=enrich(scoped_markup)
    checks.update(evidence["checks"])
    return {"name":name,"source":source,"listing_url":url,"individual_listing_confirmed":provenance["status"] == "bound",
            "evidence_provenance":provenance,
            "sale_method":"auction" if auction_evidence(primary_title + " " + scoped_text) else "unverified",
            "reported_mechanical_failure":mechanical_failure(primary_title + " " + scoped_text),
            "checks":checks,"plate":plate,"plate_confirmed_from_listing":bool(plate),
            "plate_conflicts":list(normalized_plates) if len(normalized_plates) > 1 else [],
            "field_evidence":{ "price":evidence["vat"], "location_source":evidence.get("location_source"),
                "plate_source":"same_listing_label_or_vehicle_record" if plate else None,
                "seller_reported": [{key: node.get(key) for key in ("source_record_id", "listing_url", "net_price_reported", "seller_reported_availability", "seller_reported_dimensions", "seller_reported_service_history")}
                                     for node in scoped_objects if node.get("@type") == "VehicleEvidence"]},
            "city_mentioned":city,"price_advertised":price_hit.group(1) if price_hit else None,
            "price_incl_vat":evidence["vat"]["amount_incl_vat"],"vat_basis":evidence["vat"]["basis"],
            "distance_km":evidence["distance_km"],"location_coordinates":evidence["location_coordinates"],
            "mechanical_concerns":"Service history, rust, driveline, cab A/C operation and payload unverified.",
            "evidence_note":"Fields require URL-linked primary vehicle or canonical main evidence; unbound HTML remains an unverified lead. Seller claims and actual condition remain unverified.",
            "observed_at":datetime.now(timezone.utc).isoformat()}

def discover(fetcher=fetch,max_per_source=50):
    run_metadata = {"started_at": datetime.now(timezone.utc).isoformat(), "max_per_source": max_per_source,
                    "code_fingerprint": code_fingerprint()}
    fetcher = SourceFetch(fetcher)
    coverage={};candidates=[];seen=set();rss_leads=[]
    for source,domain in SOURCES.items():
        direct_urls = {}
        card_evidence = {}
        filter_confirmed = False
        inventory_stats = None
        dealer_stats = None
        if source == "Local dealers":
            dealer_stats = crawl_dealers(fetcher)
            direct_urls.update(dealer_stats["details"])
            card_evidence.update(dealer_stats["cards"])
        seed_success = sum(row["inventory_pages_fetched"] for row in dealer_stats["coverage"]) if dealer_stats else 0
        seed_errors = []
        anchor_count = 0
        response_diagnostics=[]
        source_blocked=False
        source_block_reason=None
        if source=="viaBOVAG":
            inventory_stats=crawl_inventory(source,SEED_PAGES[source],fetcher)
            direct_urls.update(inventory_stats["details"])
            card_evidence.update(inventory_stats.get("cards", {}))
            seed_success=inventory_stats["inventory_pages_accessible"]
            seed_errors=[x["error"] for x in inventory_stats["inventory_errors"]]
            anchor_count=inventory_stats["inventory_links_examined"]
        for seed in ([] if inventory_stats is not None else BUDGET_PAGES.get(source, []) + SEED_PAGES[source]):
            if source == "Local dealers" and dealer_for_url(seed):
                continue
            if filter_confirmed and seed not in BUDGET_PAGES.get(source, []):
                continue
            if host_key(seed) in fetcher.stops:
                continue
            if valid_url(seed,source) and relevant_link("",seed,source):
                direct_urls.setdefault(seed,"")
            try:
                page, typ = fetcher(seed)
                if "html" not in typ.lower(): raise ValueError("non-HTML inventory page")
                seed_success += 1
                card_evidence.update(inventory_cards(page, seed))
                filter_confirmed = filter_confirmed or budget_applied(page)
                for card in card_evidence.values():
                    if valid_url(card["url"], source):
                        direct_urls.setdefault(card["url"], card["title"])
                parser = LinkCollector()
                parser.feed(page)
                if not parser.links and os.environ.get("ENABLE_BROWSER_RENDER")=="1":
                    page,typ=browser_render(seed)
                    parser=LinkCollector()
                    parser.feed(page)
                anchor_count += len(parser.links)
                if source in ("AutoScout24","AutoWereld"):
                    extra=extract_marketplace_links(page,seed,source)
                    for label,url in extra:
                        direct_urls.setdefault(url,label)
                extra_diagnostics=(marketplace_diagnostics(page,seed,source)
                    if source=="AutoScout24" else {})
                response_diagnostics.append({"seed":seed,"bytes":len(page),"content_type":typ[:70],
                    "autowereld_response_identity":response_identity(page,typ) if source=="AutoWereld" else None,
                    "auto_scout_structure":extra_diagnostics,
                    "anchors":len(parser.links),"new_vehicle_urls":len(direct_urls),
                    "suspected_interstitial":bool(re.search(r"captcha|access denied|toegang geweigerd|verify you are human|bot detection|javascript required",page[:18000],re.I))})
                for label, href in parser.links:
                    url = urldefrag(urljoin(seed, href))[0]
                    if valid_url(url,source) and relevant_link(label,url,source): direct_urls.setdefault(url,label)
                if source in ("AutoScout24","AutoTrack","AutoWereld"):
                    # Public application state can include advert URLs absent from anchors.
                    # Only accept source-specific detail URL shapes, never search URLs.
                    for raw in re.findall(r"(?:https?://[^\"\s<>]+|/(?:aanbod|a)/[^\"\s<>]+)",page)[:2500]:
                        url=urldefrag(urljoin(seed,html.unescape(raw).replace("\\/","/")))[0]
                        url=url.split("?")[0]
                        if valid_url(url,source) and relevant_link("",url,source):
                            direct_urls.setdefault(url,"")
            except Exception as exc:
                if len(seed_errors)<4: seed_errors.append(str(exc)[:140])
        feed_diagnostics=[]
        snapshot_status="not_applicable"
        snapshot_urls=0
        if source=="AutoWereld":
            snapshot, snapshot_status=read_snapshot_records(os.environ.get("AUTOWERELD_RSS_SNAPSHOT","data/autowereld_rss_snapshot.json"))
            rss_leads=list(snapshot)
            for row in snapshot:
                url,title=row["url"],row["title"]
                if valid_url(url,source) and relevant_link(title,url,source):
                    direct_urls.setdefault(url,title)
                    snapshot_urls+=1
            advert_pattern=re.compile(
                r"https://(?:www\.)?autowereld\.nl/[a-z0-9-]+/[a-z0-9-]+/[a-z0-9-]+-\d+/details\.html",
                re.I)
            for feed_url in AUTOWERELD_RSS:
                if host_key(feed_url) in fetcher.stops:
                    continue
                try:
                    rss_xml,feed_content_type=fetcher(feed_url)
                    xml_error=None
                    html_recovery={"html_anchors":0,"verified_advert_links":0,"conversion_usable":False}
                    if "html" in feed_content_type.lower():
                        normalized_xml,html_recovery=html_to_xml(rss_xml,feed_url)
                        feed_items=search_links(normalized_xml)
                    else:
                        try:
                            feed_items=search_links(rss_xml)
                        except ET.ParseError as exc:
                            feed_items=[]
                            xml_error=str(exc)[:120]
                    # A source may return a nominally valid document without
                    # conventional <item> elements. Recover literal advert URLs
                    # in BOTH cases, with first-party /details.html validation.
                    recovered=advert_pattern.findall(html.unescape(rss_xml).replace("\\\\/","/"))
                    before=len(direct_urls)
                    for title,url in feed_items+[( "",u) for u in recovered]:
                        url=html.unescape(url).strip()
                        if valid_url(url,source) and relevant_link(title,url,source):
                            direct_urls.setdefault(url,title)
                    feed_diagnostics.append({"feed":feed_url,"bytes":len(rss_xml),
                        "content_type":feed_content_type[:80],
                        "response_prefix":re.sub(r"\s+"," ",rss_xml[:220])[:180],
                        "xml_items":len(feed_items),"recovered_urls":len(recovered),
                        "accepted_new_urls":len(direct_urls)-before,
                        "xml_error":xml_error,
                        "response_identity":response_identity(rss_xml,feed_content_type),
                        "html_conversion":html_recovery,
                        "unexpected_html":("html" in feed_content_type.lower()),
                        "feed_usable":bool(feed_items or recovered)})
                except Exception as exc:
                    feed_diagnostics.append({"feed":feed_url,"error":str(exc)[:120]})
                    if len(seed_errors)<4: seed_errors.append("RSS: "+str(exc)[:120])
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
            found=0;failures=0;rejected=0;matched=0;samples=[];attempts=0;rate_limited=source_blocked
            queue, inventory_rejections = select_queue(
                [(title, url) for url, title in direct_urls.items()] + hits[:25],
                card_evidence, lambda url: valid_url(url, source))
            for title,url in queue:
                if found>=max_per_source or attempts>=MAX_FETCH_ATTEMPTS or rate_limited: break
                if url in seen or host_key(url) in fetcher.stops: continue
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
                    if item:
                        if source == "Local dealers":
                            dealer = dealer_for_url(url)
                            if dealer:
                                item["dealer_id"] = dealer["id"]
                        candidates.append(item);found+=1
                    elif len(samples)<3: samples.append({"reason":"individual vehicle evidence missing or wrong model","url":url[:250]})
                except Exception as exc:
                    failures+=1
                    if len(samples)<3: samples.append({"reason":str(exc)[:90],"url":url[:250]})
            bound_count = sum(c.get("source") == source and c.get("individual_listing_confirmed") is True for c in candidates)
            dealer_seed_urls = [row["inventory_url"] for row in dealer_stats["coverage"]] if dealer_stats else []
            restrictions = fetcher.restrictions(SEED_PAGES[source] + dealer_seed_urls)
            source_hosts = {host_key(seed) for seed in SEED_PAGES[source] + dealer_seed_urls}
            source_blocked = bool(source_hosts) and source_hosts.issubset(restrictions)
            source_block_reason = "; ".join(host + ": " + state["reason"] for host, state in restrictions.items()) or None
            rate_limited = any(state["http_status"] == 429 for state in restrictions.values())
            status=("individual_pages_found" if found else
                    "source_unavailable" if source_blocked or seed_success==0 else
                    "inventory_only_unverified" if inventory_stats is not None else
                    "no_verified_individual_pages")
            if dealer_stats:
                for row in dealer_stats["coverage"]:
                    row["identity_bound_candidates"] = sum(c.get("dealer_id") == row["dealer_id"] and c.get("individual_listing_confirmed") is True for c in candidates)
                    row["index_exclusions"] = sum(dealer_for_url(rejected["url"], detail=True) is not None and host_key(rejected["url"]) == row["domain"] for rejected in inventory_rejections)
            coverage[source]={"status":status,
                              "direct_dealers":dealer_stats["coverage"] if dealer_stats else [],
                              "inventory_pages":len(SEED_PAGES[source]),"inventory_pages_fetched":seed_success,
                              "inventory_pages_checked":inventory_stats["inventory_pages_checked"] if inventory_stats else seed_success,
                              "inventory_pages_pending":inventory_stats["inventory_pending"] if inventory_stats else None,
                              "inventory_diagnostics":inventory_stats["inventory_diagnostics"] if inventory_stats else [],
                              "inventory_links":anchor_count,"response_diagnostics":response_diagnostics,
                              "direct_eligible_urls":len(direct_urls),
                              "budget_filter_confirmed":filter_confirmed,
                              "inventory_cards":len(card_evidence),
                              "inventory_prefilter_rejections":inventory_rejections,
                              "detail_queue_size":len(queue),
                              "inventory_errors":seed_errors,"source_block_reason":source_block_reason,
                              "host_restrictions":restrictions,
                              "host_request_counts":{host:fetcher.counts.get(host,0) for host in sorted(source_hosts)},
                              "coverage_note":("Source access or request budget stopped; no claim of zero inventory." if restrictions else
                                               "AutoWereld inventory/RSS returned HTML without discoverable advert links; content could be fallback or access page." if source=="AutoWereld" and not found else None),
                              "feed_diagnostics":feed_diagnostics,
                              "external_rss_snapshot_status":snapshot_status,
                              "external_rss_urls_accepted":snapshot_urls,
                              "external_rss_evidence":"index-only; individual listing page still must be independently fetched and validated" if snapshot_urls else None,
                              "index_error":index_error,
                              "index_hits":len(hits),"detail_urls_discovered":len(direct_urls),"eligible_urls":matched,
                              "attempts":attempts,"rate_limited":rate_limited,"rejected_index_urls":rejected,
                              "individual_pages_fetched":found,"identity_bound_candidates":bound_count,"fetch_errors":failures,"diagnostic_samples":samples,
                              "method":"bounded inventory traversal, individual-detail validation, untrusted Bing fallback"}
        except Exception as exc:
            coverage[source]={"status":"unavailable","error":str(exc)[:160],"individual_pages_fetched":0,
                              "inventory_pages_fetched":seed_success,"direct_eligible_urls":len(direct_urls),"inventory_errors":seed_errors}
    run_metadata["completed_at"] = datetime.now(timezone.utc).isoformat()
    return {"run_metadata":run_metadata,"candidates":candidates,"source_coverage":coverage,
            "unverified_rss_leads":rss_leads,
            "discovery_method":"Inventory pages are traversed separately from individual vehicle URLs. Sources with no validated vehicles are not presumed to have no stock; no completeness, VAT, distance or availability guarantee."}

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",default="discovered_candidates.json")
    parser.add_argument("--max-per-source", type=int, choices=range(1, 51), default=50, metavar="1..50")
    args=parser.parse_args()
    result=discover(max_per_source=args.max_per_source)
    Path(args.output).write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("Candidate pages:",len(result["candidates"]))
    print(json.dumps(result["source_coverage"],indent=2))
