#!/usr/bin/env python3
"""Standalone validation script for benchmark datasets.

Usage:
    python benchmarks/validate_dataset.py benchmarks/data/dutch_generated_dataset.json
    python benchmarks/validate_dataset.py benchmarks/data/*.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path


def validate(path: Path) -> bool:
    """Validate a single dataset file. Returns True if all checks pass."""
    data = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(data, list):
        print(f"  ✗ Root element is not a list")
        return False

    errors: list[str] = []
    entity_counts: Counter = Counter()

    for i, sample in enumerate(data):
        text = sample.get("full_text", "")
        spans = sample.get("spans", [])

        if not isinstance(text, str) or not text.strip():
            errors.append(f"Sample {i}: missing or empty 'full_text'")
            continue

        if not isinstance(spans, list):
            errors.append(f"Sample {i}: 'spans' is not a list")
            continue

        for j, span in enumerate(spans):
            # Required fields
            for field in ("entity_type", "entity_value", "start_position", "end_position"):
                if field not in span:
                    errors.append(f"Sample {i}, span {j}: missing field '{field}'")
                    continue

            start = span["start_position"]
            end = span["end_position"]
            value = span["entity_value"]
            etype = span["entity_type"]

            # Type checks
            if not isinstance(start, int) or not isinstance(end, int):
                errors.append(f"Sample {i}, span {j}: positions must be integers")
                continue

            # Range checks
            if start < 0 or end > len(text) or start >= end:
                errors.append(
                    f"Sample {i}, span {j} ({etype}): invalid range [{start}:{end}] "
                    f"for text of length {len(text)}"
                )
                continue

            # Offset check
            actual = text[start:end]
            if actual != value:
                errors.append(
                    f"Sample {i}, span {j} ({etype}): "
                    f"text[{start}:{end}]='{actual}' != entity_value='{value}'"
                )

            entity_counts[etype] += 1

        # Overlap check
        sorted_spans = sorted(spans, key=lambda s: s["start_position"])
        for j in range(1, len(sorted_spans)):
            if sorted_spans[j]["start_position"] < sorted_spans[j - 1]["end_position"]:
                errors.append(
                    f"Sample {i}: overlapping spans "
                    f"[{sorted_spans[j-1]['start_position']}:{sorted_spans[j-1]['end_position']}] "
                    f"and [{sorted_spans[j]['start_position']}:{sorted_spans[j]['end_position']}]"
                )

    # Duplicate check
    texts = [s.get("full_text", "") for s in data]
    dupes = {t: c for t, c in Counter(texts).items() if c > 1}

    # Report
    total_spans = sum(entity_counts.values())
    negative = sum(1 for s in data if not s.get("spans"))

    print(f"\n{'='*60}")
    print(f"  {path.name}")
    print(f"{'='*60}")
    print(f"  Samples:    {len(data)}")
    print(f"  Spans:      {total_spans}")
    print(f"  Negative:   {negative}")
    print(f"  Duplicates: {len(dupes)}")
    print(f"\n  Entity distribution:")
    for etype, count in sorted(entity_counts.items(), key=lambda x: -x[1]):
        print(f"    {etype:25s} {count:4d}")

    if dupes:
        errors.append(f"{len(dupes)} duplicate full_text entries found")

    if errors:
        print(f"\n  ⚠ {len(errors)} error(s):")
        for e in errors[:30]:
            print(f"    - {e}")
        if len(errors) > 30:
            print(f"    ... and {len(errors) - 30} more")
        return False

    print(f"\n  ✓ All checks passed")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate PII benchmark datasets")
    parser.add_argument("files", nargs="+", help="Dataset JSON file(s) to validate")
    args = parser.parse_args()

    all_ok = True
    for file_str in args.files:
        path = Path(file_str)
        if not path.exists():
            print(f"File not found: {path}")
            all_ok = False
            continue
        if not validate(path):
            all_ok = False

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
