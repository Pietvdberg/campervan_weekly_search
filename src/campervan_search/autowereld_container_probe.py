"""Read-only AutoWereld feed probe for ephemeral GitHub-hosted container
comparison.

Only fetches the single configured public RSS URL. Does not execute
scripts,
solve challenges, use proxies, send email, or import discovery results.
"""

import hashlib
import json
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree

URL = "https://www.autowereld.nl/rss/peugeot/boxer/"
MAX_BYTES = 1024 * 1024


def classify(raw, content_type, status=200, final_url=URL):
    """Safe summary: never log response HTML, cookies, or authentication
    data.
    """
    data = raw.decode("utf-8", errors="replace")
    title = re.search(r"<title\b[^>]*>(.*?)</title\s*>", data, re.I | re.S)
    summary = {
        "http_status": status,
        "content_type": content_type[:90],
        "final_host": urlparse(final_url).hostname,
        "response_bytes": len(raw),
        "response_sha256_prefix": hashlib.sha256(raw).hexdigest()[:16],
        "html_title": (
            re.sub(r"<[^>]+>", " ", title.group(1)).strip()[:90]
            if title
            else None
        ),
        "xml_rss_items": 0,
        "valid_vehicle_links": 0,
        "classification": "not_rss",
    }
    try:
        root = ElementTree.fromstring(data)
        if root.tag.lower() == "rss":
            items = root.findall("./channel/item")
            summary["xml_rss_items"] = len(items)
            from campervan_search.autowereld_snapshot import valid_advert

            summary["valid_vehicle_links"] = sum(
                bool(
                    valid_advert(
                        (x.findtext("link") or "").strip(),
                        (x.findtext("title") or "").strip(),
                    )
                )
                for x in items
            )
            summary["classification"] = (
                "rss_with_vehicles"
                if summary["valid_vehicle_links"]
                else "rss_no_valid_vehicles"
            )
        elif root.tag.lower() in (
            "html",
            "{http://www.w3.org/1999/xhtml}html",
        ):
            summary["classification"] = "html_fallback"
    except ElementTree.ParseError:
        if re.search(r"<(?:!doctype\s+html|html\b)", data[:300], re.I):
            summary["classification"] = "html_fallback"
        else:
            summary["classification"] = "not_xml"
    return summary


def main():
    req = Request(
        URL,
        headers={
            "User-Agent": "Mozilla/5.0 CamperVanResearch/1.0",
            "Accept": "text/html,application/rss+xml,application/xml",
        },
    )
    try:
        with urlopen(req, timeout=15) as response:
            data = response.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                print(json.dumps({"classification": "oversized_response"}))
                return
            print(
                json.dumps(
                    classify(
                        data,
                        response.headers.get("Content-Type", ""),
                        response.status,
                        response.url,
                    )
                )
            )
    except HTTPError as exc:
        print(
            json.dumps(
                {"classification": "http_error", "http_status": exc.code}
            )
        )
    except (URLError, TimeoutError, OSError) as exc:
        print(
            json.dumps(
                {
                    "classification": "network_error",
                    "error_type": type(exc).__name__,
                }
            )
        )


if __name__ == "__main__":
    main()
