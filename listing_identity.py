"""Bind extracted evidence to a single advert; ambiguous pages remain leads."""
import json
from html import escape
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from listing_evidence import structured


def identity(url):
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().removeprefix("www.")
    return parsed.scheme.lower(), host, parsed.path.rstrip("/") or "/"


def require_same_listing(requested, final):
    if identity(requested) != identity(final):
        raise ValueError("Response redirected away from requested page")


class PageScope(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.canonicals = []
        self.stack = []
        self.parts = []
        self.main_count = 0

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "link" and "canonical" in attributes.get("rel", "").lower().split():
            self.canonicals.append(attributes.get("href", ""))
        if tag in ("area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"):
            return
        excluded = tag in ("aside", "nav", "footer", "script", "style") or any(
            marker in (attributes.get("class", "") + " " + attributes.get("id", "")).lower()
            for marker in ("related", "recommend", "similar", "vergelijkbaar", "aanbevolen")
        )
        parent_active, parent_excluded = self.stack[-1][1:] if self.stack else (False, False)
        active = parent_active or tag == "main"
        if tag == "main":
            self.main_count += 1
        self.stack.append((tag, active, excluded or parent_excluded))

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        if self.stack and self.stack[-1][1] and not self.stack[-1][2]:
            self.parts.append(data)

    def handle_entityref(self, name):
        self.handle_data("&" + name + ";")

    def handle_charref(self, name):
        self.handle_data("&#" + name + ";")


def bind_evidence(markup, url):
    """Return scoped markup and provenance, or no evidence for an unbound lead.

    Visible facts require a matching canonical URL and one main element.
    Structured facts require exactly one vehicle explicitly identifying this URL.
    Never fall back to arbitrary page-wide text, prices, plates or coordinates.
    """
    page = PageScope()
    page.feed(markup)
    canonical = [urljoin(url, value) for value in page.canonicals]
    if any(identity(value) != identity(url) for value in canonical):
        raise ValueError("Canonical URL does not identify requested listing")
    vehicles = []
    for node in structured(markup):
        types = node.get("@type", [])
        types = [types] if isinstance(types, str) else types
        if isinstance(types, list) and any(str(value).lower() in ("car", "vehicle", "product") for value in types):
            vehicles.append(node)
    matching = [node for node in vehicles if isinstance(node.get("url"), str)
                and identity(urljoin(url, node["url"])) == identity(url)]
    # Repeated conflicting identities are ambiguous even when only one matches.
    if len(matching) > 1:
        raise ValueError("Multiple vehicle objects claim the requested listing")
    primary = matching[0] if matching else None
    if vehicles and primary is None:
        return "", {"status": "unbound", "reason": "No unique URL-linked primary vehicle"}
    visible = " ".join(page.parts) if canonical and page.main_count == 1 else ""
    if primary is None and not visible:
        return "", {"status": "unbound", "reason": "No URL-linked vehicle or canonical main content"}
    if primary is not None:
        # Related products must not be traversed by downstream generic extractors.
        excluded_keys = {"isRelatedTo", "isSimilarTo", "relatedLink", "recommendations", "itemListElement"}
        def clean(value):
            if isinstance(value, dict):
                return {key: clean(item) for key, item in value.items() if key not in excluded_keys}
            if isinstance(value, list):
                return [clean(item) for item in value]
            return value
        primary = clean(primary)
        description = " ".join(str(primary.get(key) or "") for key in ("name", "description"))
        scoped = '<script type="application/ld+json">' + json.dumps(primary).replace("<", "\\u003c") + '</script>'
        scoped += "<p>" + escape(description) + "</p>"
    else:
        scoped = ""
    scoped += "<main>" + escape(visible) + "</main>"
    return scoped, {"status": "bound", "listing_url": url,
                    "basis": "url_linked_vehicle" if primary is not None else "canonical_main",
                    "canonical_url": canonical[0] if canonical else None}
