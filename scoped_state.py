"""Minimal facts from a uniquely URL-linked marketplace detail record."""
from urllib.parse import urlparse, urljoin
from html import unescape
import re

from listing_evidence import structured, parse_amount


def reference(url):
    p = urlparse(url)
    return p.scheme, (p.hostname or "").removeprefix("www."), p.path.rstrip("/")


def detail_facts(markup, url):
    if (urlparse(url).hostname or "").removeprefix("www.") not in ("autoscout24.nl", "autotrack.nl"):
        return None
    matches = []
    for node in structured(markup):
        record = node.get("listingDetails")
        if not isinstance(record, dict) or not isinstance(record.get("webPage"), str):
            continue
        record_url = urljoin(url, record["webPage"])
        same_page = reference(record_url) == reference(url)
        record_id = record.get("id")
        # AutoTrack explicitly syndicates AS24 detail records. Accept only the
        # exact shared UUID under an AutoTrack page controller; never infer
        # identity from a similar title, plate guess or third-party URL.
        syndicated = (reference(url)[1] == "autotrack.nl" and reference(record_url)[1] == "autoscout24.nl"
            and reference(str(node.get("canonicalOrigin") or ""))[:2] == reference(url)[:2]
            and isinstance(node.get("marketplace"), dict) and node["marketplace"].get("domain") == "autotrack_nl"
            and isinstance(record_id, str) and re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", record_id)
            and urlparse(url).path.endswith(record_id) and urlparse(record_url).path.endswith(record_id))
        if same_page or syndicated:
            matches.append(record)
    if len(matches) != 1:
        return None
    record = matches[0]
    vehicle = record.get("vehicle", {})
    vehicle = vehicle if isinstance(vehicle, dict) else {}
    fields = {"@type": "VehicleEvidence", "listing_url": url,
              "seller_vehicle_identity": {key: vehicle.get(key) for key in ("make", "model", "modelVersionInput", "productionYear", "firstRegistrationDateRaw", "transmissionType", "gears", "motorTypeName", "bodyType", "powerInHp")},
              "source_record_id": record.get("id"), "licensePlate": vehicle.get("licensePlate"),
              "seller_reported_availability": record.get("status"),
              "seller_reported_dimensions": {key: vehicle.get(key) for key in ("loadHeight", "loadLength", "payload")},
              "seller_reported_service_history": vehicle.get("hasFullServiceHistory")}
    equipment = vehicle.get("equipment", {})
    labels = []
    if isinstance(equipment, dict):
        for group in equipment.values():
            if isinstance(group, list):
                labels.extend(str(item["id"]) for item in group if isinstance(item, dict) and isinstance(item.get("id"), str))
    description = " ".join(re.sub(r"<[^>]+>", " ", unescape(str(record.get("description") or ""))).split())
    body = re.search(r"\bL[1-4][ .-]*H[1-3]\b", description, re.I)
    if body:
        fields["seller_vehicle_identity"]["advertisedBody"] = re.sub(r"[ .-]", "", body.group()).upper()
    # Retain contradictions in the seller's own price wording before a trusted
    # gross/net field can short-circuit price extraction. Never scan other ads.
    price_mentions = list(re.finditer(r"(?:€|EUR)\s*[\d.,]+(?:,-)?", description, re.I))
    label = r"(ex|excl\.?|exclusief|incl\.?|inclusief)\s+btw"
    for index, hit in enumerate(price_mentions):
        start = max(0, hit.start()-24, price_mentions[index-1].end() if index else 0)
        end = min(len(description), hit.end()+24, price_mentions[index+1].start() if index+1 < len(price_mentions) else len(description))
        before = re.search(label + r"\s*$", description[start:hit.start()], re.I)
        after = re.match(r"[\s,.-]*" + label, description[hit.end():end], re.I)
        # Only labels immediately attached to this amount can contradict each
        # other; a label after a separator/"prijs" may belong to the next amount.
        if before and after and before.group(1).lower().startswith("ex") != after.group(1).lower().startswith("ex"):
            fields["seller_price_conflict"] = description[start:end]
    fields["description"] = " ".join([str(vehicle.get("modelVersionInput") or ""), description] + labels)
    prices = record.get("prices", {})
    public = prices.get("public", {}) if isinstance(prices, dict) else {}
    display = record.get("price", {})
    # A platform's default inclusive label cannot settle a seller's explicit
    # "sale price excludes VAT" statement when no net/gross pair explains it.
    if (isinstance(public, dict) and isinstance(display, dict)
            and not public.get("netPriceRaw")
            and re.search(r"\bincl\.?\s*btw", str(display.get("vatLabel") or ""), re.I)
            and re.search(r"\b(?:verkoopprijs|vraagprijs|prijs)\s+(?:is\s+)?(?:exclusief|excl\.?)\s+btw\b", description, re.I)):
        fields["seller_price_conflict"] = "Platform labels price inclusive; seller explicitly describes the sale price as exclusive; no gross/net pair supplied."
    if isinstance(public, dict) and isinstance(display, dict) and not public.get("onRequestOnly") and not display.get("isConditionalPrice"):
        gross = parse_amount(public.get("priceRaw"))
        net = parse_amount(public.get("netPriceRaw"))
        # Explicit gross/net fields on this exact listing. No rounding, guessed
        # VAT from a nearby label, dealer tier price or suggested retail price.
        if (gross is not None and net is not None and gross >= net
                and "€" in str(public.get("price", "")) and "€" in str(public.get("netPrice", ""))):
            fields["price"] = float(gross)
            fields["priceCurrency"] = "EUR"
            fields["priceSpecification"] = {"price": float(gross), "priceCurrency": "EUR", "valueAddedTaxIncluded": True}
            fields["net_price_reported"] = float(net)
    margin_text = str(vehicle.get("modelVersionInput") or "") + " " + description
    margin = any(not re.search(r"\b(?:geen|niet|zonder)\s+$", margin_text[max(0, hit.start()-16):hit.start()], re.I)
                 for hit in re.finditer(r"\bmarge(?=\s|$)", margin_text, re.I))
    if (isinstance(public, dict) and isinstance(display, dict)
            and public.get("taxDeductible") is False and margin
            and not public.get("onRequestOnly") and not display.get("isConditionalPrice")
            and parse_amount(public.get("priceRaw")) is not None and "€" in str(public.get("price", ""))):
        fields["price"] = float(parse_amount(public["priceRaw"]))
        fields["priceCurrency"] = "EUR"
        fields["priceSpecification"] = {"price": fields["price"], "priceCurrency": "EUR", "valueAddedTaxIncluded": True}
        fields["seller_reported_margin"] = True
    location = record.get("location", {})
    if isinstance(location, dict) and location.get("zip") and location.get("street"):
        fields["vehicle_location"] = {"@type": "VehicleLocation", "address": {
            "postalCode": location["zip"], "streetAddress": location["street"],
            "addressLocality": location.get("city"), "addressCountry": location.get("countryCode")}}
    return fields
