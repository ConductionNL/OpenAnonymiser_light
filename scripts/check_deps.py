#!/usr/bin/env python3
"""Print installed versions of Presidio and SpaCy dependencies.

Run manually:
    uv run scripts/check_deps.py

Called automatically by api.py at startup and by the Dockerfile build step.
Exit code 1 if any required package is missing.
"""

import sys
from importlib.metadata import PackageNotFoundError, version

REQUIRED = [
    "presidio-analyzer",
    "presidio-anonymizer",
    "spacy",
]


def check_versions() -> bool:
    """Print versions of required packages. Returns True if all are present."""
    all_ok = True
    for pkg in REQUIRED:
        try:
            v = version(pkg)
            print(f"  {pkg:<28} {v}")
        except PackageNotFoundError:
            print(f"  {pkg:<28} NOT INSTALLED", file=sys.stderr)
            all_ok = False
    return all_ok


if __name__ == "__main__":
    print("Dependency versions:")
    ok = check_versions()
    sys.exit(0 if ok else 1)
