"""Extract discoverable, first-party vehicle URLs from public
marketplace HTML.

No HTTP calls, javascript execution, authentication or
access-control bypass.
The caller must still independently validate every fetched vehicle
page.
"""

import html
import re
from html.parser import HTMLParser
from urllib.parse import urldefrag, urljoin, urlparse

from campervan_search.source_catalog import VAN_MODEL as TARGETS

UUID = r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}"
AUTO_SCOUT = re.compile(r"/aanbod/[a-z0-9_-]+-" + UUID + r"/?$", re.I)
BEDRIJFSAUTO = re.compile(r"/[a-z0-9-]+-\d{7,}/?$", re.I)
AUTOWERELD = re.compile(
    r"/[a-z0-9-]+/[a-z0-9-]+/[a-z0-9-]+-\d+/details\.html$", re.I
)


class Links(HTMLParser):
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
            self.links.append((" ".join(self.label), self.href))
            self.href = None


def decode(value):
    """Unescape common inline JSON encodings without executing
    application
        code.
    """
    value = html.unescape(value)
    value = (
        value.replace(r"\/", "/")
        .replace(r"\u002F", "/")
        .replace(r"\u002f", "/")
    )
    value = value.replace(r"\u0026", "&").replace(r"\u003d", "=")
    value = value.replace(r"\u002D", "-").replace(r"\u002d", "-")
    value = value.replace(r"\u003A", ":").replace(r"\u003a", ":")
    return value


def source_detail(url, source):
    p = urlparse(url)
    host = (p.hostname or "").lower()
    if p.scheme != "https":
        return False
    domains = {
        "AutoScout24": "autoscout24.nl",
        "Bedrijfsauto": "bedrijfsauto.nl",
        "AutoWereld": "autowereld.nl",
    }
    domain = domains.get(source)
    if not domain or not (host == domain or host.endswith("." + domain)):
        return False
    path = p.path.lower()
    matcher = {
        "AutoScout24": AUTO_SCOUT,
        "Bedrijfsauto": BEDRIJFSAUTO,
        "AutoWereld": AUTOWERELD,
    }[source]
    return bool(matcher.fullmatch(path))


def diagnostics(markup, base, source):
    """Summarize response structure without persisting vehicle or seller
    data.
    """
    text = decode(markup)
    parser = Links()
    parser.feed(text)
    own = [
        urlparse(urljoin(base, href)).path
        for _, href in parser.links
        if href
        and urlparse(urljoin(base, href)).hostname
        in ("autoscout24.nl", "www.autoscout24.nl")
    ]
    offer_fragments = [
        m.group(0)[:180]
        for m in re.finditer(r'/aanbod/[^\s"<>]{4,220}', text, re.I)
    ]
    return {
        "offer_path_samples": list(dict.fromkeys(offer_fragments))[:3],
        "raw_aanbod_references": len(re.findall(r"/aanbod/", text, re.I)),
        "uuid_occurrences": len(re.findall(UUID, text, re.I)),
        "first_party_aanbod_anchors": sum(
            p.startswith("/aanbod/") for p in own
        ),
        "first_party_anchor_count": len(own),
        "embedded_next_data": "__NEXT_DATA__" in text,
        "vehicle_card_markers": sum(
            text.lower().count(token)
            for token in ("listing-card", "listing-item", "vehicle-card")
        ),
    }


def extract(markup, base, source, limit=1000):
    """Return distinct (label, URL) detail candidates, including
    JSON-escaped anchors.
    """
    if source not in ("AutoScout24", "Bedrijfsauto", "AutoWereld"):
        return []
    markup = decode(markup)
    parser = Links()
    parser.feed(markup)
    pairs = list(parser.links)
    # Links inside Next.js/JSON responses may not be HTML anchors.
    for m in re.finditer(
        (
            'https?://[^\\s"<>\\\\]+|/(?:aanbod|peugeot|ford|cit'
            "roen|fiat|renault|opel|mercedes|volkswagen|iveco"
            ')/[^\\s"<>\\\\]+'
        ),
        markup,
        re.I,
    ):
        pairs.append(("", m.group()))
    if source == "AutoScout24":
        # Embedded application data can concatenate JSON keys or flags
        # after a
        # detail URL, so capture a bounded, exact slug+UUID rather than
        # requiring the entire surrounding script token to be a URL.
        detail = re.compile(
            r"/aanbod/([a-z0-9_-]+-" + UUID + r")(?=[^a-z0-9-]|$)", re.I
        )
        for found in detail.finditer(markup):
            pairs.append(("", found.group(0)))
    results = {}
    for label, raw in pairs:
        url = (
            urldefrag(urljoin(base, decode(raw).strip()))[0]
            .split("?")[0]
            .rstrip(".,;)")
        )
        if source_detail(url, source) and TARGETS.search(
            label + " " + urlparse(url).path.replace("-", " ")
        ):
            results.setdefault(url, label)
            if len(results) >= limit:
                break
    return [(label, url) for url, label in results.items()]
