"""Explicit sale exclusions and dated RDW concerns, not a mechanical
inspection.
"""

import re
from datetime import datetime
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

EXCLUDED_DOMAINS = (
    "gaspedaal.nl",
    "trucksnl.nl",
    "wijkopenautos.nl",
    "bedrijfsauto.nl",
)
AUCTION = re.compile(r"\b(?:veiling(?:en|kosten|platform)?|auction)\b", re.I)


def auction_evidence(text):
    for match in AUCTION.finditer(str(text or "")):
        before = str(text)[max(0, match.start() - 24) : match.start()]
        if not re.search(
            r"\b(?:geen|niet|no)\s+(?:(?:via|een|an|a)\s+)?$", before, re.I
        ):
            return True
    return False


CURRENT_FAILURE = re.compile(
    (
        "\\b(?:(?:motor|injector(?:en)?|versnellingsbak|koppel"
        "ing|airco)\\s+(?:(?:is|zijn)\\s+)?(?:defect|kapot|vast"
        ")|motor\\s+(?:is\\s+)?niet\\s+(?:100\\s*%|%\\s*100)|motor"
        "\\s+(?:is\\s+)?niet\\s+goed|motorproblemen|motor(?:stor"
        "ings)?lampje\\s+(?:brandt(?!\\s+niet\\b)|is\\s+aan)|(?:m"
        "otor|airco)\\s+(?:loopt|werkt)\\s+niet|start\\s+niet|(?"
        ":betreft|is)\\s+(?:(?:een|deze)\\s+)?schadeauto)(?!\\w)"
    ),
    re.I,
)


def mechanical_failure(text):
    text = str(text or "")
    for hit in CURRENT_FAILURE.finditer(text):
        before = text[max(0, hit.start() - 24) : hit.start()]
        # Repair wording must refer to this fault, not a different
        # component in
        # a later sentence ("motor defect. Koppeling vervangen" is a
        # non-runner).
        after = text[hit.end() : hit.end() + 45]
        if re.search(
            r"\b(?:geen|zonder|no|indien|als|bij|in geval van)\s+$",
            before,
            re.I,
        ):
            continue
        if re.match(
            (
                "\\s*(?:geweest\\b|[,;]?\\s*(?:maar\\s+)?(?:inmid"
                "dels\\s+|nu\\s+)?(?:gerepareerd|verholpen|hers"
                "teld|vervangen)\\b)"
            ),
            after,
            re.I,
        ):
            continue
        return hit.group(0)
    return None


def sale_exclusion(candidate):
    claims = candidate.get("field_evidence", {}).get("seller_reported", [])
    for claim in claims if isinstance(claims, list) else []:
        value = (
            claim.get("seller_reported_availability")
            if isinstance(claim, dict)
            else None
        )
        if isinstance(value, str) and value.casefold().strip() in (
            "sold",
            "closed",
            "deleted",
            "inactive",
            "verkocht",
            "niet meer beschikbaar",
        ):
            return (
                "Individual advert explicitly reports the vehicle as"
                " unavailable"
            )
    if candidate.get("reported_mechanical_failure"):
        return "Explicitly reported current defect or engine warning: " + str(
            candidate["reported_mechanical_failure"]
        )
    host = (
        urlparse(candidate.get("listing_url") or "").hostname or ""
    ).lower()
    if any(
        host == domain or host.endswith("." + domain)
        for domain in EXCLUDED_DOMAINS
    ):
        return "Explicitly excluded marketplace"
    if candidate.get("sale_method") == "auction" or auction_evidence(
        candidate.get("name")
    ):
        return "Auction sale excluded by search requirements"
    return None


def rdw_risks(vehicle, today=None):
    today = today or datetime.now(ZoneInfo("Europe/Amsterdam")).date()
    concerns = []

    def add(code, message, blocks=False):
        concerns.append(
            {
                "code": code,
                "message": message,
                "blocks_qualification": blocks,
                "assessed_on": today.isoformat(),
            }
        )

    if str(vehicle.get("tellerstandoordeel") or "").casefold() == "onlogisch":
        add(
            "odometer_inconsistent",
            "RDW odometer assessment is Onlogisch; resolve the discrepancy"
            " before recommendation.",
            True,
        )
    raw_expiry = vehicle.get("vervaldatum_apk")
    expiry = None
    if raw_expiry:
        try:
            expiry = datetime.strptime(str(raw_expiry), "%Y%m%d").date()
        except ValueError:
            add(
                "apk_date_unverified",
                "RDW APK expiry date could not be interpreted.",
            )
    if expiry is not None and expiry < today:
        add(
            "apk_expired",
            "RDW APK expired on "
            + expiry.isoformat()
            + "; do not assume current approval.",
            True,
        )
    try:
        maximum = int(vehicle.get("toegestane_maximum_massa_voertuig"))
    except (ValueError, TypeError):
        maximum = None
    if maximum is not None and maximum > 3500:
        add(
            "licence_mass_review",
            "Registered maximum mass exceeds the specification’s category B /"
            " 3,500 kg limit; resolve legal registration before"
            " recommendation.",
            True,
        )
    return concerns
