"""Evidence extraction from a vehicle's own HTML; unknowns remain unknown.

Structured seller statements are evidence of what was advertised, not independent
proof of mechanical condition, legal payload, or current availability.
"""
import html
import json
import os
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from urllib.request import Request, urlopen
from urllib.parse import quote

ORIGIN=(4.2930,51.4945)  # Bergen op Zoom approximate city centre (lon, lat)
TARGET_TYPES={"Vehicle","Car","Product","Offer"}
SCRIPT=re.compile(r'<script\b([^>]*)>(.*?)</script\s*>',re.I|re.S)
PLATE=re.compile(r'\b(?:kenteken|nummerplaat|registratie)\s*[:\-]?\s*([A-Z0-9]{1,3}-[A-Z0-9]{1,3}-[A-Z0-9]{1,3})\b',re.I)
PRICE=re.compile(r'(?:€|EUR)\s*(\d{1,3}(?:\.\d{3})+(?:,\d{2})?|\d{4,6}(?:[.,]\d{2})?|\d{1,3}(?:,\d{2})?)(?!\d)',re.I)
LOCATION=re.compile(r'\b(?:plaats|vestiging|locatie|standplaats)\s*:\s*([A-ZÀ-ÿ][A-Za-zÀ-ÿ -]{2,45})',re.I)

def objects(value,depth=0):
    if depth>10:return
    if isinstance(value,dict):
        yield value
        for item in value.values():
            yield from objects(item,depth+1)
    elif isinstance(value,list):
        for item in value[:500]:
            yield from objects(item,depth+1)

def structured(markup):
    found=[]
    for attrs,body in SCRIPT.findall(markup):
        attrs=attrs.lower()
        if ('ld+json' not in attrs and
            'id="__next_data__"' not in attrs and
            "id='__next_data__'" not in attrs):
            continue
        try:
            value=json.loads(html.unescape(body))
            found.extend(objects(value))
        except (ValueError,TypeError):
            continue
    return found

def parse_amount(value):
    if value is None:return None
    text=str(value).strip().replace("€","").replace(" ","")
    if "," in text:
        text=text.replace(".","").replace(",",".")
    elif text.count(".")>1 or (text.count(".")==1 and len(text.split(".")[-1])==3):
        text=text.replace(".","")
    try:
        n=Decimal(text)
        if n<=0 or n>1000000:return None
        return n
    except InvalidOperation:return None

def price_evidence(markup,objs):
    """Resolve VAT only when wording belongs to the *same* advertised amount.

    Price and VAT context from arbitrary other cards or scripts must not be
    combined. A bare JSON-LD offer price is not evidence of tax treatment.
    """
    visible = re.sub(r"<(?:script|style)\\b[^>]*>.*?</(?:script|style)>", " ", markup, flags=re.I|re.S)
    text=" ".join(html.unescape(re.sub(r"<[^>]+>"," ",visible)).split())
    offer=next((d for d in objs if "price" in d and ("priceCurrency" in d or "priceSpecification" in d)),None)
    offer_amount=parse_amount(offer.get("price")) if offer else None
    matches=list(PRICE.finditer(text))
    # Prefer a first-party structured offer price, but do not use the VAT
    # label next to a different price elsewhere on the page.
    ordered=([m for m in matches if parse_amount(m.group(1))==offer_amount]
             if offer_amount is not None else matches)
    if not ordered and offer_amount is None:
        return {"amount_incl_vat":None,"basis":"unknown","source":"none"}
    for match in ordered:
        amount=parse_amount(match.group(1))
        if amount is None:continue
        before=text[max(0,match.start()-32):match.start()].lower()
        after=text[match.end():match.end()+48].lower()
        context=before+" PRICE "+after
        # Explicit seller labels immediately adjacent to this specific amount.
        excl=bool(re.search(r"(?:excl\\.?|exclusief)\\s*(?:21%\\s*)?(?:btw|vat)",context,re.I))
        incl=bool(re.search(r"(?:incl\\.?|inclusief)\\s*(?:21%\\s*)?(?:btw|vat)",context,re.I))
        margin=bool(re.search(r"\\bmarge(?:auto|regeling)?\\b",context,re.I))
        if (excl and incl) or (excl and margin):
            continue
        if excl:
            inclusive=(amount*Decimal("1.21")).quantize(Decimal("0.01"),rounding=ROUND_HALF_UP)
            return {"amount_incl_vat":float(inclusive),"advertised_amount":float(amount),
                    "basis":"exclusive_21_percent","source":"adjacent_seller_text"}
        if incl or margin:
            return {"amount_incl_vat":float(amount),"advertised_amount":float(amount),
                    "basis":"explicit_inclusive_or_margin","source":"adjacent_seller_text"}
    amount=offer_amount if offer_amount is not None else (parse_amount(matches[0].group(1)) if matches else None)
    return {"amount_incl_vat":None,"advertised_amount":float(amount) if amount is not None else None,
            "basis":"unknown","source":"advertised"}


POSTCODE=re.compile(r"\\b([1-9][0-9]{3})\\s?([A-Za-z]{2})\\b")

def address_from_structured(objs):
    """Only resolve independently documented full NL postcode + house number."""
    for d in objs:
        raw=d.get("address")
        if not isinstance(raw,dict):continue
        postcode=str(raw.get("postalCode") or "").upper().replace(" ","")
        number=str(raw.get("streetAddress") or "")
        match=POSTCODE.fullmatch(postcode)
        house=re.search(r"\\b([1-9]\\d{0,4})\\s*[A-Za-z]?\\s*$",number)
        country=str(raw.get("addressCountry") or "NL").upper()
        if isinstance(raw.get("addressCountry"),dict):
            country=str(raw["addressCountry"].get("name") or "").upper()
        if match and house and country in ("NL","NLD","NETHERLANDS","NEDERLAND"):
            return (postcode,house.group(1))
    return None


def pdok_coordinates(address,fetcher=None):
    """PDOK public Dutch BAG location lookup; no city-centre approximation."""
    postcode,house=address
    query=quote(postcode+" "+house)
    url="https://api.pdok.nl/bzk/locatieserver/search/v3_1/free?"+f"q={query}&rows=3&fq=type%3Aadres"
    if fetcher is None:
        def fetcher(url):
            with urlopen(Request(url,headers={"User-Agent":"CamperVanResearch/3.0"}),timeout=9) as r:
                return json.load(r)
    docs=fetcher(url).get("response",{}).get("docs",[])
    for doc in docs:
        found_postcode=str(doc.get("postcode") or "").upper().replace(" ","")
        found_house=str(doc.get("huisnummer") or "")
        match=re.fullmatch(r"POINT\\s*\\(\\s*([\\d.]+)\\s+([\\d.]+)\\s*\\)",str(doc.get("centroide_ll") or ""))
        if found_postcode==postcode and found_house==house and match:
            lon,lat=map(float,match.groups())
            if 3.2<=lon<=7.3 and 50.5<=lat<=53.8:return lon,lat
    return None

def coords(objs):
    for d in objs:
        lat=d.get("latitude")
        lon=d.get("longitude")
        if lat is None or lon is None:continue
        try:
            lat=float(lat);lon=float(lon)
            if 50.5<=lat<=53.8 and 3.2<=lon<=7.3:return (lon,lat)
        except (ValueError,TypeError):pass
    return None

def route_km(destination,fetcher=None):
    """OSRM driving route; can be self-hosted via OSRM_BASE_URL, else public demo."""
    base=os.environ.get("OSRM_BASE_URL","https://router.project-osrm.org").rstrip("/")
    a,b=ORIGIN
    c,d=destination
    url=f"{base}/route/v1/driving/{a},{b};{c},{d}?overview=false"
    if fetcher is None:
        def fetcher(url):
            with urlopen(Request(url,headers={"User-Agent":"CamperVanResearch/3.0"}),timeout=9) as r:
                return json.load(r)
    value=fetcher(url)
    if value.get("code")!="Ok" or not value.get("routes"):return None
    distance=float(value["routes"][0]["distance"])/1000
    return round(distance,1) if 0<distance<1000 else None

def enrich(markup,route_fetcher=None,geocode_fetcher=None):
    objs=structured(markup)
    price=price_evidence(markup,objs)
    location=coords(objs)
    location_source="structured_coordinates" if location is not None else None
    address=address_from_structured(objs) if location is None else None
    if address is not None:
        try:
            location=pdok_coordinates(address,geocode_fetcher)
            if location is not None:location_source="pdok_verified_full_address"
        except (ValueError,KeyError,TypeError,OSError,TimeoutError):pass
    checks={}
    if price["amount_incl_vat"] is not None:
        checks["price_incl_vat_within_8000"]=price["amount_incl_vat"]<=8000
    distance=None
    if location is not None:
        try:
            distance=route_km(location,route_fetcher)
        except (ValueError,KeyError,TypeError,OSError,TimeoutError):
            pass
        if distance is not None:checks["distance_within_100km"]=distance<=100
    return {"structured_objects":len(objs),"vat":price,
            "distance_km":distance,"location_coordinates":location,"location_source":location_source,"checks":checks}
