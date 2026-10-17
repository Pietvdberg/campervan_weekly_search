"""Turn *actual* AutoWereld HTML advert links into normalized XML items.

HTML-to-XML is a local representation change, not a way around access restrictions.
Never fabricate entries when a response has no source-specific advert URLs.
"""
import html
import hashlib
import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse, urldefrag
from xml.etree.ElementTree import Element, SubElement, tostring

AD_PATH = re.compile(r"/[a-z0-9-]+/[a-z0-9-]+/[a-z0-9-]+-\d+/details\.html", re.I)
from source_catalog import VAN_MODEL as VEHICLES

class Anchors(HTMLParser):
    def __init__(self):
        super().__init__()
        self.items=[]
        self.href=None
        self.label=[]
    def handle_starttag(self,tag,attrs):
        if tag=="a":
            self.href=dict(attrs).get("href")
            self.label=[]
    def handle_data(self,data):
        if self.href is not None:self.label.append(data)
    def handle_endtag(self,tag):
        if tag=="a" and self.href is not None:
            self.items.append((" ".join(" ".join(self.label).split()),self.href))
            self.href=None

def html_to_xml(markup,base_url):
    """Return (normalized XML feed, diagnostics) for genuine first-party advert links.

    Handles broken HTML and ordinary relative anchors, plus absolute advert URLs
    embedded in scripts. Does not parse advertisements from generic text or
    unrelated domains, and cannot recover listings absent from the response.
    """
    parser=Anchors()
    parser.feed(markup)
    pairs=list(parser.items)
    pairs.extend(("",m.group(0)) for m in re.finditer(
        r"https://(?:www\.)?autowereld\.nl/[a-z0-9-]+/[a-z0-9-]+/[a-z0-9-]+-\d+/details\.html",
        html.unescape(markup).replace(r"\/","/"),re.I))
    selected={}
    for label,raw_url in pairs:
        url=urldefrag(urljoin(base_url,html.unescape(raw_url).strip()))[0].split("?")[0]
        parsed=urlparse(url)
        host=(parsed.hostname or "").lower()
        if (parsed.scheme!="https" or host not in ("autowereld.nl","www.autowereld.nl")
                or not AD_PATH.fullmatch(parsed.path)
                or not VEHICLES.search(parsed.path.replace("-"," "))):
            continue
        selected.setdefault(url,label)
    rss=Element("rss",{"version":"2.0"})
    channel=SubElement(rss,"channel")
    SubElement(channel,"title").text="AutoWereld recovered HTML vehicle links"
    for url,label in selected.items():
        item=SubElement(channel,"item")
        SubElement(item,"title").text=label
        SubElement(item,"link").text=url
    return tostring(rss,encoding="unicode"),{"html_anchors":len(parser.items),
                                         "verified_advert_links":len(selected),
                                         "conversion_usable":bool(selected)}


def response_identity(markup,content_type):
    """Summarize received document without persisting HTML, cookies or tokens.

    The same short error document returned for category, RSS and detail pages
    indicates a delivery/access discrepancy, not an HTML parsing defect.
    """
    p=Anchors()
    p.feed(markup)
    titles=re.findall(r"<title\b[^>]*>(.*?)</title\s*>",markup,re.I|re.S)
    text_title=" ".join(html.unescape(re.sub(r"<[^>]+>"," ",titles[0])).split())[:120] if titles else None
    # Hash only stable structural indicators; avoid propagating page content.
    body=re.sub(r"\s+"," ",markup).strip()
    classification=("actual_rss" if re.search(r"<rss\b",markup[:2000],re.I) else
                    "html_no_links" if not p.items else "html_has_links")
    return {"response_class":classification,
            "content_type":content_type[:90],
            "bytes":len(markup.encode("utf-8")),
            "sha256_prefix":hashlib.sha256(body.encode("utf-8")).hexdigest()[:16],
            "html_title":text_title,
            "anchor_count":len(p.items),
            "has_rss_items":bool(re.search(r"<item\b",markup,re.I)),
            "contains_vehicle_detail_url":bool(re.search(
                r"(?:https://(?:www\.)?autowereld\.nl)?/[a-z0-9-]+/[a-z0-9-]+/[a-z0-9-]+-\d+/details\.html",
                html.unescape(markup).replace(r"\/","/"),re.I))}
