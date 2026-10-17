"""Minimal facts from a uniquely URL-linked marketplace detail record."""
from urllib.parse import urlparse, urljoin

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
        if isinstance(record, dict) and isinstance(record.get("webPage"), str) and reference(urljoin(url, record["webPage"])) == reference(url):
            matches.append(record)
    if len(matches) != 1:
        return None
    record = matches[0]
    vehicle = record.get("vehicle", {})
    vehicle = vehicle if isinstance(vehicle, dict) else {}
    fields = {"@type": "VehicleEvidence", "listing_url": url,
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
    fields["description"] = " ".join([str(vehicle.get("modelVersionInput") or "")] + labels)
    prices = record.get("prices", {})
    public = prices.get("public", {}) if isinstance(prices, dict) else {}
    display = record.get("price", {})
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
    location = record.get("location", {})
    if isinstance(location, dict) and location.get("zip") and location.get("street"):
        fields["vehicle_location"] = {"@type": "VehicleLocation", "address": {
            "postalCode": location["zip"], "streetAddress": location["street"],
            "addressLocality": location.get("city"), "addressCountry": location.get("countryCode")}}
    return fields
