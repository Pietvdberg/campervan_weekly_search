"""Bind extracted evidence to a single advert; ambiguous pages remain leads."""
import json
from html import escape
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from listing_evidence import structured
from scoped_state import detail_facts


def identity(url):
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().removeprefix("www.")
    return parsed.scheme.lower(), host, parsed.path.rstrip("/") or "/"


class ExternalRedirect(ValueError):
    """Response left the configured source, e.g. for an external consent gate."""


def require_same_listing(requested, final, inventory=False):
    if identity(requested)[:2] != identity(final)[:2]:
        raise ExternalRedirect("Source redirected to another origin (" + (urlparse(final).hostname or "unknown") + "); content not validated")
    if inventory:
        # A configured inventory entry point may move within its own HTTPS
        # host. It still supplies discovery links, never candidate evidence.
        if identity(requested)[:2] == identity(final)[:2] and identity(final)[0] == "https":
            return
    if identity(requested) != identity(final):
        raise ValueError("Response redirected away from requested page")


class PageScope(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.canonicals = []
        self.stack = []
        self.parts = []
        self.main_count = 0
        self.detail_forms = []
        self.gallery_ids = set()

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        in_main = self.stack and self.stack[-1][1] and not self.stack[-1][2]
        if in_main and tag == "form" and attributes.get("id", "").startswith("car_details_form"):
            self.detail_forms.append(attributes.get("action", ""))
        if in_main and tag == "img":
            import re
            match = re.search(r"/webservices/feed_images/([0-9]+)/", attributes.get("src", ""))
            if match:
                self.gallery_ids.add(match.group(1))
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
    def identifies_listing(node):
        # Marktplaats and AutoScout24 identify the vehicle through its own
        # Offer.url, rather than a url property on the Vehicle/Product itself.
        direct = node.get("url")
        offers = node.get("offers", [])
        offers = [offers] if isinstance(offers, dict) else offers if isinstance(offers, list) else []
        references = ([direct] if isinstance(direct, str) else []) + [
            offer["url"] for offer in offers if isinstance(offer, dict) and isinstance(offer.get("url"), str)]
        return bool(references) and all(identity(urljoin(url, reference)) == identity(url) for reference in references)

    matching = [node for node in vehicles if identifies_listing(node)]
    # Repeated conflicting identities are ambiguous even when only one matches.
    if len(matching) > 1:
        raise ValueError("Multiple vehicle objects claim the requested listing")
    primary = matching[0] if matching else None
    if vehicles and primary is None:
        return "", {"status": "unbound", "reason": "No unique URL-linked primary vehicle"}
    dealer_bound = False
    if primary is None and not canonical:
        from dealer_sources import matches_registered_detail
        dealer_bound = matches_registered_detail(page, url)
    visible = " ".join(page.parts) if (canonical or dealer_bound) and page.main_count == 1 else ""
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
    facts = detail_facts(markup, url)
    if facts is not None:
        scoped += '<script type="application/ld+json">' + json.dumps(facts).replace("<", "\\u003c") + '</script>'
        scoped += '<p>' + escape(facts.get("description", "")) + '</p>'
    scoped += "<main>" + escape(visible) + "</main>"
    return scoped, {"status": "bound", "listing_url": url,
                    "basis": "url_linked_vehicle" if primary is not None else "registered_dealer_form_gallery" if dealer_bound else "canonical_main",
                    "canonical_url": canonical[0] if canonical else None}
