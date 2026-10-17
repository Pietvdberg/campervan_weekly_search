"""Check a wheel installation from outside the repository without
network.
"""

import json
from importlib.metadata import distribution
from importlib.resources import files

from campervan_search.dealer_sources import load_registry
from campervan_search.report_html import render_html
from campervan_search.validate_search import code_fingerprint


def main():
    package = files("campervan_search")
    for filename in ("dealer_registry.json", "variant_research.json"):
        contents = package.joinpath("resources", filename).read_text()
        if not json.loads(contents):
            raise RuntimeError("Missing or empty resource: " + filename)
    if not load_registry():
        raise RuntimeError("Installed dealer registry was not loaded")
    html = render_html({"generated_on": "2026-10-17", "results": []})
    if "Camperzoektocht" not in html or "2026-10-17" not in html:
        raise RuntimeError("Installed HTML template did not render")
    if len(code_fingerprint()) != 64:
        raise RuntimeError("Installed code fingerprint is invalid")
    commands = distribution("campervan-weekly-search").entry_points
    for command in commands:
        if command.group == "console_scripts" and not callable(command.load()):
            raise RuntimeError("Broken command: " + command.name)
    print("Installed resources, template and console entry points passed")


if __name__ == "__main__":
    main()
