"""Maintained, explicit direct dealer allowlist and bounded inventory crawling."""
import json
from pathlib import Path
from decimal import Decimal
import re
from urllib.parse import urlparse, urljoin

from inventory_discovery import links_on_page, NEXT
from discovery_queue import cards, key
from listing_evidence import PRICE, parse_amount

REGISTRY_PATH = Path(__file__).with_name("dealer_registry.json")


def load_registry(path=REGISTRY_PATH):
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError("Dealer registry must be a list")
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or row.get("id") in seen:
            raise ValueError("Invalid or duplicate dealer registry entry")
        seen.add(row["id"])
        domain = row.get("domain", "")
        if not re.fullmatch(r"[a-z0-9-]+\.[a-z]{2,}", domain):
            raise ValueError("Invalid dealer domain")
        for field in ("inventory_url", "contact_url"):
            if not on_domain(row.get(field, ""), domain):
                raise ValueError("Dealer URL outside its registered HTTPS domain")
        pattern = row.get("detail_path_pattern", "")
        if not pattern.startswith("^") or not pattern.endswith("$"):
            raise ValueError("Dealer detail patterns must be anchored")
        re.compile(pattern)
    return rows


def on_domain(url, domain):
    p = urlparse(url)
    host = (p.hostname or "").lower()
    return p.scheme == "https" and (host == domain or host.endswith("." + domain))


def dealer_for_url(url, registry=None, detail=False):
    for dealer in load_registry() if registry is None else registry:
        if on_domain(url, dealer["domain"]) and (not detail or re.fullmatch(dealer["detail_path_pattern"], urlparse(url).path)):
            return dealer
    return None


def crawl_dealers(fetcher, maximum_pages=2, registry=None):
    registry = load_registry() if registry is None else registry
    details = {}
    evidence = {}
    coverage = []
    for dealer in registry:
        queue = [dealer["inventory_url"]]
        visited = set()
        row = {"dealer_id": dealer["id"], "name": dealer["name"], "domain": dealer["domain"],
               "inventory_pages_checked": 0, "inventory_pages_fetched": 0, "detail_urls_discovered": 0,
               "errors": [], "status": "not_checked", "inventory_url": dealer["inventory_url"],
               "contact_url": dealer["contact_url"], "registry_checked_on": dealer.get("checked_on")}
        while queue and len(visited) < maximum_pages:
            url = queue.pop(0)
            if url in visited or not on_domain(url, dealer["domain"]):
                continue
            visited.add(url)
            row["inventory_pages_checked"] += 1
            try:
                markup, content_type = fetcher(url)
                if "html" not in content_type.lower():
                    raise ValueError("Dealer inventory is not HTML")
                row["inventory_pages_fetched"] += 1
                evidence.update(cards(markup, url))
                for label, link, rel in links_on_page(markup, url):
                    if dealer_for_url(link, [dealer], detail=True):
                        details.setdefault(link, label)
                        price_match = PRICE.match(label.strip())
                        amount = parse_amount(price_match.group(1)) if price_match else None
                        card = {"url": link, "title": label,
                            "advertised_eur": float(amount) if amount is not None else None,
                            "inventory_url": url, "evidence": "unverified inventory card only",
                            "discovery_city_hint": dealer.get("discovery_locations", [""])[0] if len(dealer.get("discovery_locations", [])) == 1 else ""}
                        if price_match and amount is not None and re.match(
                                r"^[\s,.-]*(?:ex\.?|excl\.?|exclusief)\s*(?:21%\s*)?btw\b",
                                label[price_match.end():price_match.end()+30], re.I):
                            card["gross_lower_bound_eur"] = float(amount * Decimal("1.21"))
                        evidence.setdefault(key(link), card)
                    elif on_domain(link, dealer["domain"]) and (NEXT.search(label) or rel == "next"):
                        # Pagination is constrained to the current inventory path.
                        if urlparse(link).path.rstrip("/") == urlparse(url).path.rstrip("/") and link not in visited:
                            queue.append(link)
                for card in evidence.values():
                    if dealer_for_url(card["url"], [dealer], detail=True):
                        details.setdefault(card["url"], card["title"])
            except Exception as exc:
                row["errors"].append(str(exc)[:180])
                break
        row["detail_urls_discovered"] = sum(dealer_for_url(url, [dealer], detail=True) is not None for url in details)
        row["inventory_pages_pending"] = len(queue)
        row["status"] = "inventory_accessible" if row["inventory_pages_fetched"] else "source_unavailable"
        row["note"] = "Bounded public inventory sample; not exhaustive stock or verified route/availability."
        coverage.append(row)
    return {"details": details, "cards": evidence, "coverage": coverage}


def matches_registered_detail(page, url):
    """BWCR publishes a page-specific form action and gallery instead of JSON-LD."""
    dealer = dealer_for_url(url, detail=True)
    if not dealer or dealer.get("identity_strategy") != "detail_form_and_gallery":
        return False
    path = urlparse(url).path
    match = re.match(r"/occasions-kopen/([0-9]+)-", path)
    if not match or match.group(1) not in page.gallery_ids or not page.detail_forms:
        return False
    def normalized(value):
        parsed = urlparse(value)
        return parsed.scheme, (parsed.hostname or "").removeprefix("www."), parsed.path.rstrip("/")
    return page.main_count == 1 and all(normalized(urljoin(url, action)) == normalized(url) for action in page.detail_forms)
