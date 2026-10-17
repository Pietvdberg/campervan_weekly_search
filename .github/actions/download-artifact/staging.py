"""Manage temporary artifact directories using only the standard
library.
"""

import argparse
import os
import shutil
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "clean"))
    args = parser.parse_args()
    if args.action == "prepare":
        directory = tempfile.mkdtemp(
            prefix="camper-artifact-", dir=os.environ["RUNNER_TEMP"]
        )
        with open(os.environ["GITHUB_OUTPUT"], "a") as output:
            output.write("path=" + directory + "\n")
    else:
        shutil.rmtree(os.environ["ARTIFACT_ARCHIVE_DIRECTORY"])


if __name__ == "__main__":
    main()
