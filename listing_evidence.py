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
    text=" ".join(html.unescape(re.sub(r"<[^>]+>"," ",markup)).split())
    offer=next((d for d in objs if "price" in d and ("priceCurrency" in d or "priceSpecification" in d)),None)
    amount=parse_amount(offer.get("price")) if offer else None
    if amount is None:
        m=PRICE.search(text)
        amount=parse_amount(m.group(1)) if m else None
    if amount is None:return {"amount_incl_vat":None,"basis":"unknown","source":"none"}
    # Only an explicit price context qualifies for VAT calculation; JSON-LD alone
    # does not establish whether an advertised business price excludes VAT.
    context=re.search(r'(?:€|EUR)\s*[\d.,]+\s*(?:excl\.?\s*(?:btw|vat)|ex(?:cl)?\.?\s*btw|incl\.?\s*(?:btw|vat)|marge)',text,re.I)
    near=context.group(0).lower() if context else ""
    if re.search(r'excl|ex\s*btw',near):
        incl=(amount*Decimal("1.21")).quantize(Decimal("0.01"),rounding=ROUND_HALF_UP)
        basis="exclusive_21_percent"
    elif "incl" in near or "marge" in near:
        incl=amount
        basis="explicit_inclusive_or_margin"
    else:
        return {"amount_incl_vat":None,"advertised_amount":float(amount),"basis":"unknown","source":"advertised"}
    return {"amount_incl_vat":float(incl),"advertised_amount":float(amount),"basis":basis,"source":"explicit_text"}

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

def enrich(markup,route_fetcher=None):
    objs=structured(markup)
    price=price_evidence(markup,objs)
    location=coords(objs)
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
            "distance_km":distance,"location_coordinates":location,"checks":checks}
