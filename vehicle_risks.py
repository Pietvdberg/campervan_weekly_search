"""Explicit sale exclusions and dated RDW concerns, not a mechanical inspection."""
from datetime import date, datetime
import re
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

EXCLUDED_DOMAINS = ("gaspedaal.nl", "trucksnl.nl", "wijkopenautos.nl", "bedrijfsauto.nl")
AUCTION = re.compile(r"\b(?:veiling(?:en|kosten|platform)?|auction)\b", re.I)


def auction_evidence(text):
    for match in AUCTION.finditer(str(text or "")):
        before = str(text)[max(0, match.start() - 24):match.start()]
        if not re.search(r"\b(?:geen|niet|no)\s+(?:(?:via|een|an|a)\s+)?$", before, re.I):
            return True
    return False


def sale_exclusion(candidate):
    host = (urlparse(candidate.get("listing_url") or "").hostname or "").lower()
    if any(host == domain or host.endswith("." + domain) for domain in EXCLUDED_DOMAINS):
        return "Explicitly excluded marketplace"
    if candidate.get("sale_method") == "auction" or auction_evidence(candidate.get("name")):
        return "Auction sale excluded by search requirements"
    return None


def rdw_risks(vehicle, today=None):
    today = today or datetime.now(ZoneInfo("Europe/Amsterdam")).date()
    concerns = []
    def add(code, message, blocks=False):
        concerns.append({"code": code, "message": message, "blocks_qualification": blocks,
                         "assessed_on": today.isoformat()})
    if str(vehicle.get("tellerstandoordeel") or "").casefold() == "onlogisch":
        add("odometer_inconsistent", "RDW odometer assessment is Onlogisch; resolve the discrepancy before recommendation.", True)
    raw_expiry = vehicle.get("vervaldatum_apk")
    expiry = None
    if raw_expiry:
        try:
            expiry = datetime.strptime(str(raw_expiry), "%Y%m%d").date()
        except ValueError:
            add("apk_date_unverified", "RDW APK expiry date could not be interpreted.")
    if expiry is not None and expiry < today:
        add("apk_expired", "RDW APK expired on " + expiry.isoformat() + "; do not assume current approval.", True)
    try:
        maximum = int(vehicle.get("toegestane_maximum_massa_voertuig"))
    except (ValueError, TypeError):
        maximum = None
    if maximum is not None and maximum > 3500:
        add("licence_mass_review", "Registered maximum mass exceeds 3,500 kg; verify driving-licence entitlement and intended use.")
    return concerns
