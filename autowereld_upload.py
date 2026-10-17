"""Compatibility launcher for existing Pi services; use installed
package
CLI.
"""

import runpy
import sys
from pathlib import Path


def main():
    sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
    runpy.run_module("campervan_search.autowereld_upload", run_name="__main__")


if __name__ == "__main__":
    main()
