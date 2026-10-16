"""Extract discoverable, first-party vehicle URLs from public marketplace HTML.

No HTTP calls, javascript execution, authentication or access-control bypass.
The caller must still independently validate every fetched vehicle page.
"""
import html
import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse, urldefrag

TARGETS = re.compile(r"\b(boxer|jumper|ducato|transit|master|movano|sprinter|crafter|daily|transporter|nv400)\b", re.I)
UUID = r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}"
AUTO_SCOUT = re.compile(r"/aanbod/[a-z0-9-]+-" + UUID + r"/?$", re.I)
BEDRIJFSAUTO = re.compile(r"/[a-z0-9-]+-\d{7,}/?$", re.I)
AUTOWERELD = re.compile(r"/[a-z0-9-]+/[a-z0-9-]+/[a-z0-9-]+-\d+/details\.html$", re.I)

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links=[]
        self.href=None
        self.label=[]
    def handle_starttag(self,tag,attrs):
        if tag=="a":
            self.href=dict(attrs).get("href")
            self.label=[]
    def handle_data(self,data):
        if self.href is not None:
            self.label.append(data)
    def handle_endtag(self,tag):
        if tag=="a" and self.href is not None:
            self.links.append((" ".join(self.label),self.href))
            self.href=None

def decode(value):
    """Unescape common inline JSON encodings without executing application code."""
    value=html.unescape(value)
    value=value.replace(r"\/","/").replace(r"\u002F","/").replace(r"\u002f","/")
    value=value.replace(r"\u0026","&").replace(r"\u003d","=")
    return value

def source_detail(url,source):
    p=urlparse(url)
    host=(p.hostname or "").lower()
    if p.scheme!="https":
        return False
    domains={"AutoScout24":"autoscout24.nl","Bedrijfsauto":"bedrijfsauto.nl",
             "AutoWereld":"autowereld.nl"}
    domain=domains.get(source)
    if not domain or not (host==domain or host.endswith("."+domain)):
        return False
    path=p.path.lower()
    matcher={"AutoScout24":AUTO_SCOUT,"Bedrijfsauto":BEDRIJFSAUTO,
             "AutoWereld":AUTOWERELD}[source]
    return bool(matcher.fullmatch(path))

def extract(markup,base,source,limit=1000):
    """Return distinct (label, URL) detail candidates, including JSON-escaped anchors."""
    if source not in ("AutoScout24","Bedrijfsauto","AutoWereld"):
        return []
    markup=decode(markup)
    parser=Links()
    parser.feed(markup)
    pairs=list(parser.links)
    # Links inside Next.js/JSON responses may not be HTML anchors.
    for m in re.finditer(r'https?://[^\s"<>\\]+|/(?:aanbod|peugeot|ford|citroen|fiat|renault|opel|mercedes|volkswagen|iveco)/[^\s"<>\\]+',markup,re.I):
        pairs.append(("",m.group()))
    results={}
    for label,raw in pairs:
        url=urldefrag(urljoin(base,decode(raw).strip()))[0].split("?")[0].rstrip(".,;)")
        if source_detail(url,source) and TARGETS.search(label+" "+urlparse(url).path.replace("-"," ")):
            results.setdefault(url,label)
            if len(results)>=limit:break
    return [(label,url) for url,label in results.items()]

def inspect_autoscout(markup):
    """Bounded, non-sensitive diagnostics for observed AutoScout24 URL shapes."""
    from collections import Counter
    from urllib.parse import urlparse
    normalized=decode(markup)
    hrefs=Links()
    hrefs.feed(normalized)
    candidates=[]
    for _,href in hrefs.links:
        p=urlparse(urljoin("https://www.autoscout24.nl/",href))
        if p.hostname and p.hostname.endswith("autoscout24.nl"):
            candidates.append(p.path)
    # Embedded link values often occur without a literal href attribute.
    for hit in re.finditer(r'/(?:aanbod|lst|offers|details?)/[a-zA-Z0-9_/%.-]{4,220}',normalized,re.I):
        candidates.append(hit.group().split("?")[0])
    prefixes=Counter("/"+"/".join(p.strip("/").split("/")[:2]) for p in candidates)
    return {
        "anchor_count":len(hrefs.links),
        "observed_path_prefixes":dict(prefixes.most_common(8)),
        "contains_aanbod_literal":"/aanbod/" in normalized,
        "contains_listing_uuid":bool(re.search(UUID,normalized,re.I)),
        "extracted_detail_urls":len(extract(markup,"https://www.autoscout24.nl/","AutoScout24")),
    }
