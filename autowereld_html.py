"""Turn *actual* AutoWereld HTML advert links into normalized XML items.

HTML-to-XML is a local representation change, not a way around access restrictions.
Never fabricate entries when a response has no source-specific advert URLs.
"""
import html
import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse, urldefrag
from xml.etree.ElementTree import Element, SubElement, tostring

AD_PATH = re.compile(r"/[a-z0-9-]+/[a-z0-9-]+/[a-z0-9-]+-\d+/details\.html", re.I)
VEHICLES = re.compile(r"\b(boxer|jumper|ducato|transit|master|movano|sprinter|crafter|daily|transporter|nv400)\b",re.I)

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
