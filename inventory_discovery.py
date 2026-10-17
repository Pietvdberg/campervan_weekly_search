"""Inventory traversal and listing URL extraction.

Inventory/category pages do NOT consume the budget for vehicle detail pages.
Supports visible anchors, embedded JSON URLs, and bounded next-page traversal.
No authentication, access-control bypass, or search-page-as-listing shortcuts.
"""
import html
import json
import re
from collections import deque
from html.parser import HTMLParser
from urllib.parse import parse_qs, urljoin, urlparse, urldefrag
from listing_evidence import structured, parse_amount
from discovery_queue import cards as inventory_cards, key as listing_key

from source_catalog import VAN_MODEL as MODELS
NEXT=re.compile(r"\b(volgende|next|volgende pagina|toon meer)\b",re.I)
MAX_INVENTORY_PAGES=24
MAX_VEHICLE_URLS=500

class Anchors(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links=[]
        self.href=None
        self.label=[]
        self.rel=""
    def handle_starttag(self,tag,attrs):
        if tag=="a":
            a=dict(attrs)
            self.href=a.get("href")
            self.rel=a.get("rel","")
            self.label=[]
    def handle_data(self,value):
        if self.href is not None:self.label.append(value)
    def handle_endtag(self,tag):
        if tag=="a" and self.href is not None:
            self.links.append((" ".join(" ".join(self.label).split()),self.href,self.rel))
            self.href=None

def allowed(url,domain):
    p=urlparse(url)
    host=(p.hostname or "").lower()
    return p.scheme=="https" and (host==domain or host.endswith("."+domain))

def classify(url,source):
    """Return 'detail', 'inventory' or None. Never infer detail from text alone."""
    p=urlparse(url)
    path=p.path.lower().rstrip("/")
    parts=[x for x in path.split("/") if x]
    if source=="viaBOVAG":
        if re.fullmatch(r"/auto/aanbod/[a-z0-9-]+-[a-z0-9]{6,}",path):
            return "detail"
        if "/merk-" in path or "/model-" in path:
            return "inventory"
        return None
    return None

def links_on_page(markup,base):
    parser=Anchors()
    parser.feed(markup)
    out=[(label,urldefrag(urljoin(base,href))[0],rel) for label,href,rel in parser.links]
    # Some marketplaces embed card links in application JSON, not anchors.
    # Decode public JSON objects, but do not synthesize imaginary vehicle IDs.
    for obj in structured(markup):
        for key in ("url","href","canonicalUrl","detailUrl","permalink"):
            value=obj.get(key)
            if isinstance(value,str) and value.startswith(("/","https://")):
                out.append((str(obj.get("name") or obj.get("title") or ""),urldefrag(urljoin(base,value))[0],""))
    # JSON-in-script transport, e.g. escaped relative vehicle URLs.
    for value in re.findall(r'(?:\\"|")((?:https?://[^"\\\s]+|/auto/[^"\\\s]+))(?:\\"|")',markup)[:2000]:
        out.append(("",urldefrag(urljoin(base,html.unescape(value)))[0],""))
    return out

def next_inventory(url,label,rel,source,current):
    if not (NEXT.search(label) or "next" in rel.lower()):return False
    if url==current:return False
    return classify(url,source)=="inventory" or urlparse(url).path==urlparse(current).path

def crawl(source,seeds,fetcher,maximum=MAX_INVENTORY_PAGES):
    if source!="viaBOVAG":raise ValueError("unsupported inventory crawler")
    domain="viabovag.nl"
    queue=deque(seeds)
    visited=set()
    details={}
    card_evidence={}
    errors=[]
    diagnostics=[]
    accessible=0
    anchors=0
    while queue and len(visited)<maximum and len(details)<MAX_VEHICLE_URLS:
        url=queue.popleft()
        if url in visited or not allowed(url,domain):continue
        visited.add(url)
        try:
            markup,ctype=fetcher(url)
            if "html" not in ctype.lower():raise ValueError("non-HTML inventory response")
            accessible+=1
            links=links_on_page(markup,url)
            card_evidence.update(inventory_cards(markup, url))
            anchors+=len(links)
            candidate_count=0
            for label,link,rel in links:
                if not allowed(link,domain):continue
                kind=classify(link,source)
                if kind=="detail":
                    if MODELS.search(label+" "+urlparse(link).path.replace("-"," ")):
                        details.setdefault(link,label)
                        prices = [parse_amount(value) for value in re.findall(
                            r"prijs(?:\s+voor\s+zakelijke\s+kopers)?\s*:\s*([0-9.]+(?:,[0-9]{2})?)", label, re.I)]
                        prices = [value for value in prices if value is not None]
                        if prices:
                            # Explicit Dutch site purchase-price label within
                            # this advert's own link; repeated old/new prices use
                            # the lowest bound and never qualify a vehicle.
                            card_evidence[listing_key(link)] = {"url":link,"title":label,
                                "advertised_eur":float(min(prices)),"inventory_url":url,
                                "evidence":"unverified labelled inventory price only"}
                        candidate_count+=1
                elif kind=="inventory" and next_inventory(link,label,rel,source,url) and link not in visited:
                    queue.append(link)
            if not candidate_count and len(diagnostics)<6:
                diagnostics.append({"inventory_url":url,"note":"no identifiable vehicle-detail links; inventory not exhausted"})
        except Exception as exc:
            errors.append({"url":url,"error":str(exc)[:120]})
            if "429" in str(exc) or "403" in str(exc):
                # Respect source access limits; stop this inventory traversal.
                break
    return {"details":details,"cards":card_evidence,"inventory_pages_checked":len(visited),
            "inventory_pages_accessible":accessible,"inventory_links_examined":anchors,
            "inventory_errors":errors[:8],"inventory_pending":len(queue),
            "inventory_diagnostics":diagnostics}
