"""Inventory evidence controls crawl order only; it never qualifies a vehicle."""
from html import unescape
import re
from urllib.parse import urljoin, urlparse, urlunparse

from listing_evidence import structured, parse_amount
from source_catalog import VAN_MODEL, DISCOVERY_TOWNS
from vehicle_risks import auction_evidence, mechanical_failure

LOW_ROOF = re.compile(r"\bL[1-4]\s*H1\b", re.I)
HIGH_ROOF = re.compile(r"\bL[234][ .-]*H[23]\b|\bhoog\s*dak\b", re.I)
UNSUITABLE = re.compile(r"\b(?:transit\s+(?:connect|courier)|motor\s+vast|motor\s+defect|motor\s+loopt\s+niet|(?:injectoren?|injector(?:en)?|versnellingsbak|koppeling)\s+(?:defect|kapot)|schade|chassis\s*cabine|open\s+laadbak|pick[ -]?up|kipper|hoogwerker|bakwagen|laadkraan)\b", re.I)


def key(url):
    parsed = urlparse(url)
    return urlunparse((parsed.scheme.lower(), (parsed.hostname or "").lower().removeprefix("www."), parsed.path.rstrip("/"), "", "", ""))


def cards(markup, base):
    """Read explicit URL-linked public card fields; never invent advert IDs."""
    result = {}
    for node in structured(markup):
        raw_url = node.get("vipUrl") or node.get("url")
        if not isinstance(raw_url, str):
            continue
        amount = None
        title = str(node.get("title") or node.get("name") or "")
        if isinstance(node.get("priceInfo"), dict) and node.get("itemId"):
            info = node["priceInfo"]
            if info.get("priceType") in ("FIXED", "MIN_BID"):
                cents = info.get("priceCents")
                if isinstance(cents, (int, float)) and not isinstance(cents, bool) and cents > 0:
                    amount = cents / 100
        elif isinstance(node.get("price"), dict) and isinstance(node.get("vehicle"), dict):
            info = node["price"]
            title += " " + str(node["vehicle"].get("modelVersionInput") or "")
            # The same card must explicitly show EUR; no FX assumptions.
            if "€" in str(info.get("priceFormatted", "")) and not info.get("isConditionalPrice"):
                parsed = parse_amount(info.get("priceRaw"))
                amount = float(parsed) if parsed is not None else None
        elif node.get("@type") in ("Vehicle", "Car", "Product"):
            offers = node.get("offers", {})
            offers = [offers] if isinstance(offers, dict) else offers if isinstance(offers, list) else []
            amounts = {parse_amount(offer.get("price")) for offer in offers
                       if isinstance(offer, dict) and offer.get("priceCurrency") == "EUR"}
            amounts.discard(None)
            if len(amounts) == 1:
                amount = float(next(iter(amounts)))
        else:
            continue
        url = urljoin(base, raw_url)
        if urlparse(url).scheme != "https" or not title:
            continue
        location = node.get("location", {})
        city = str(location.get("city") or location.get("cityName") or "") if isinstance(location, dict) else ""
        entry = {"condition_clue": mechanical_failure(title + " " + str(node.get("description") or "")), "discovery_city_hint": city, "url": url, "title": unescape(title), "advertised_eur": amount,
                 "inventory_url": base, "evidence": "unverified inventory card only"}
        previous = result.get(key(url))
        if previous is None:
            result[key(url)] = entry
        elif previous["advertised_eur"] != amount:
            # Conflicting cards must not silently discard a possibly affordable advert.
            result[key(url)]["advertised_eur"] = None
            result[key(url)]["conflicting_prices"] = True
    return result


def budget_applied(markup):
    """A request parameter alone does not prove that a site applied the filter."""
    for node in structured(markup):
        query = node.get("pageQuery")
        if isinstance(query, dict) and str(query.get("priceto")) == "8000":
            return True
    return False


def select(pairs, evidence, eligible):
    selected = {}
    rejected = []
    for label, url in pairs:
        if not eligible(url):
            continue
        identity = key(url)
        card = evidence.get(identity, {})
        title = card.get("title") or label or urlparse(url).path.replace("-", " ")
        amount = card.get("gross_lower_bound_eur", card.get("advertised_eur"))
        reason = None
        if card.get("condition_clue") or mechanical_failure(title):
            reason = "explicit current mechanical failure"
        elif not VAN_MODEL.search(title + " " + urlparse(url).path.replace("-", " ")):
            reason = "not a target van model"
        elif LOW_ROOF.search(title):
            reason = "explicit low-roof configuration"
        elif auction_evidence(title):
            reason = "auction sale"
        elif any(not re.search(r"\b(?:geen|zonder|no)\s+$", title[max(0, hit.start()-15):hit.start()], re.I)
                 for hit in UNSUITABLE.finditer(title)):
            reason = "explicit damaged or incompatible body/engine"
        elif amount is not None and amount > 8000:
            reason = "advertised EUR lower bound exceeds gross budget"
        if reason:
            rejected.append({"url": url, "reason": reason, "inventory_evidence": card or None})
            continue
        regional_hint = str(card.get("discovery_city_hint") or "").casefold().strip() in DISCOVERY_TOWNS
        score = (regional_hint, bool(HIGH_ROOF.search(title)), amount is not None,
                 bool(re.search(r"\bairco|airconditioning\b", title, re.I)))
        previous = selected.get(identity)
        if previous is None or score > previous[0]:
            selected[identity] = (score, title, url)
    ordered = sorted(selected.values(), key=lambda row: row[0], reverse=True)
    return [(title, url) for _, title, url in ordered], rejected
