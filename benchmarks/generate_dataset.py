#!/usr/bin/env python3
"""Generate Dutch PII benchmark datasets.

Produces two JSON files:
  - dutch_generated_dataset.json   (normal templates, ~250-300 sentences)
  - dutch_edge_cases_dataset.json  (edge cases + false-positive traps)

Usage:
    python benchmarks/generate_dataset.py [--seed 42] [--repeats 3]
    python benchmarks/generate_dataset.py --validate  # generate + validate
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

# Ensure benchmarks package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from benchmarks.data.generators.entities import GENERATORS, generate
from benchmarks.data.generators.templates import TEMPLATES
from benchmarks.data.generators.edge_cases import EDGE_CASE_TEMPLATES, FALSE_POSITIVE_TRAPS

# Regex to find {ENTITY_TYPE} placeholders
_PLACEHOLDER_RE = re.compile(r"\{([A-Z_]+)\}")

# Target counts per entity type in the normal dataset
TARGET_COUNTS: dict[str, int] = {
    "PERSON": 50, "LOCATION": 50, "ORGANIZATION": 50, "STREET_ADDRESS": 50,
    "POSTCODE": 50, "EMAIL": 50, "PHONE_NUMBER": 50, "BSN": 50, "IBAN": 50,
    "KVK_NUMBER": 50, "VAT_NUMBER": 50, "LICENSE_PLATE": 50, "IP_ADDRESS": 50,
    "MAC_ADDRESS": 50, "DATE": 50, "DRIVERS_LICENSE": 50,
    "ID_NO": 50, "CASE_NO": 50, "NORP": 50, "MONEY": 50,
    "EDUCATION_LEVEL": 50, "POLITICAL_PARTY": 50, "SOCIAL_MEDIA": 30,
}


def _fill_template(template: str) -> dict | None:
    """Fill a template with generated entity values and compute character offsets.

    Returns a dict with 'full_text' and 'spans', or None if template has
    unsupported placeholders.
    """
    spans: list[dict] = []
    result = ""
    last_end = 0

    for match in _PLACEHOLDER_RE.finditer(template):
        entity_type = match.group(1)
        if entity_type not in GENERATORS:
            return None  # skip templates with unknown placeholders

        # Append text before this placeholder
        result += template[last_end:match.start()]

        # Generate entity value
        value = generate(entity_type)
        start_pos = len(result)
        result += value
        end_pos = len(result)

        spans.append({
            "entity_type": entity_type,
            "entity_value": value,
            "start_position": start_pos,
            "end_position": end_pos,
        })

        last_end = match.end()

    # Append remaining text after last placeholder
    result += template[last_end:]

    # Validate all spans
    for span in spans:
        actual = result[span["start_position"]:span["end_position"]]
        if actual != span["entity_value"]:
            raise ValueError(
                f"Offset mismatch: expected '{span['entity_value']}' "
                f"but got '{actual}' at [{span['start_position']}:{span['end_position']}]"
            )

    return {"full_text": result, "spans": spans}


def _count_entities(samples: list[dict]) -> Counter:
    """Count entity occurrences across all samples."""
    counts: Counter = Counter()
    for sample in samples:
        for span in sample["spans"]:
            counts[span["entity_type"]] += 1
    return counts


def _needs_more(counts: Counter, targets: dict[str, int]) -> dict[str, int]:
    """Return entity types that are below target, with the deficit."""
    return {
        etype: target - counts.get(etype, 0)
        for etype, target in targets.items()
        if counts.get(etype, 0) < target
    }


def _templates_for_entity(entity_type: str, templates: list[str]) -> list[str]:
    """Return templates that contain the given entity type placeholder."""
    placeholder = f"{{{entity_type}}}"
    return [t for t in templates if placeholder in t]


def generate_normal_dataset(seed: int = 42, repeats: int = 3) -> list[dict]:
    """Generate the normal benchmark dataset.

    Strategy:
    1. Run through all templates `repeats` times with different random values
    2. Check entity coverage — if any type is below target, generate extra
       sentences from templates containing that entity type
    """
    random.seed(seed)

    samples: list[dict] = []

    # Phase 1: generate from all templates
    for _ in range(repeats):
        for template in TEMPLATES:
            sample = _fill_template(template)
            if sample and sample["spans"]:
                samples.append(sample)

    # Phase 2: fill gaps — keep generating until all targets are met
    max_iterations = 2000
    iteration = 0
    stale_count = 0
    while iteration < max_iterations:
        counts = _count_entities(samples)
        gaps = _needs_more(counts, TARGET_COUNTS)
        if not gaps:
            break

        # Cycle through all under-represented entities, not just the worst
        gap_entities = sorted(gaps, key=gaps.get, reverse=True)
        added = False
        for worst_entity in gap_entities:
            candidates = _templates_for_entity(worst_entity, TEMPLATES)
            if not candidates:
                continue
            template = random.choice(candidates)
            sample = _fill_template(template)
            if sample and sample["spans"]:
                samples.append(sample)
                added = True
                break

        if not added:
            stale_count += 1
            if stale_count > 50:
                break  # no progress possible
        else:
            stale_count = 0
        iteration += 1

    return samples


def generate_edge_case_dataset(seed: int = 42) -> list[dict]:
    """Generate the edge-case / adversarial benchmark dataset.

    Includes:
    - Edge-case templates with real PII
    - False-positive traps (no PII, empty spans)
    """
    random.seed(seed + 1000)  # different seed from normal

    samples: list[dict] = []

    # Generate edge-case templates (2 variations each)
    for template in EDGE_CASE_TEMPLATES:
        for _ in range(2):
            sample = _fill_template(template)
            if sample:
                samples.append(sample)

    # Add false-positive traps as negative samples
    for text in FALSE_POSITIVE_TRAPS:
        samples.append({"full_text": text, "spans": []})

    return samples


def validate_dataset(samples: list[dict], label: str = "dataset", check_targets: bool = True) -> bool:
    """Validate dataset integrity. Returns True if all checks pass."""
    errors: list[str] = []

    for i, sample in enumerate(samples):
        text = sample.get("full_text", "")
        spans = sample.get("spans", [])

        if not text:
            errors.append(f"Sample {i}: empty full_text")
            continue

        for j, span in enumerate(spans):
            start = span["start_position"]
            end = span["end_position"]
            value = span["entity_value"]
            actual = text[start:end]

            if actual != value:
                errors.append(
                    f"Sample {i}, span {j}: offset mismatch — "
                    f"expected '{value}' got '{actual}' at [{start}:{end}]"
                )

            if start < 0 or end > len(text) or start >= end:
                errors.append(
                    f"Sample {i}, span {j}: invalid offsets [{start}:{end}] "
                    f"for text of length {len(text)}"
                )

        # Check for overlapping spans
        sorted_spans = sorted(spans, key=lambda s: s["start_position"])
        for j in range(1, len(sorted_spans)):
            prev_end = sorted_spans[j - 1]["end_position"]
            curr_start = sorted_spans[j]["start_position"]
            if curr_start < prev_end:
                errors.append(
                    f"Sample {i}: overlapping spans at positions "
                    f"{sorted_spans[j-1]['start_position']}-{prev_end} and "
                    f"{curr_start}-{sorted_spans[j]['end_position']}"
                )

    # Check for exact duplicate full_text
    texts = [s["full_text"] for s in samples]
    dupes = [t for t, c in Counter(texts).items() if c > 1]
    if dupes:
        errors.append(f"Found {len(dupes)} duplicate full_text entries")

    # Report
    counts = _count_entities(samples)
    print(f"\n{'='*60}")
    print(f"Validation: {label}")
    print(f"{'='*60}")
    print(f"Total samples: {len(samples)}")
    print(f"Total spans:   {sum(counts.values())}")
    print(f"Negative samples (no spans): {sum(1 for s in samples if not s['spans'])}")
    print(f"\nEntity distribution:")
    for etype, count in sorted(counts.items(), key=lambda x: -x[1]):
        target = TARGET_COUNTS.get(etype, "?")
        if check_targets:
            status = "✓" if isinstance(target, int) and count >= target else "✗"
            print(f"  {status} {etype:25s} {count:4d}  (target: {target})")
        else:
            print(f"    {etype:25s} {count:4d}")

    # Entities with zero coverage (only check for normal dataset)
    if check_targets:
        for etype in TARGET_COUNTS:
            if counts.get(etype, 0) == 0:
                errors.append(f"Entity type {etype} has ZERO samples")

    if errors:
        print(f"\n⚠ {len(errors)} validation errors:")
        for e in errors[:20]:
            print(f"  - {e}")
        if len(errors) > 20:
            print(f"  ... and {len(errors) - 20} more")
        return False

    print(f"\n✓ All validation checks passed")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Dutch PII benchmark datasets")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    parser.add_argument("--repeats", type=int, default=3, help="Template repetitions for normal set (default: 3)")
    parser.add_argument("--validate", action="store_true", help="Also run validation after generation")
    parser.add_argument("--output-dir", type=str, default=None, help="Output directory (default: benchmarks/data/)")
    args = parser.parse_args()

    output_dir = Path(args.output_dir) if args.output_dir else Path(__file__).resolve().parent / "data"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate normal dataset
    print("Generating normal dataset...")
    normal = generate_normal_dataset(seed=args.seed, repeats=args.repeats)
    normal_path = output_dir / "dutch_generated_dataset.json"
    normal_path.write_text(json.dumps(normal, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  → {normal_path} ({len(normal)} samples)")

    # Generate edge-case dataset
    print("Generating edge-case dataset...")
    edge = generate_edge_case_dataset(seed=args.seed)
    edge_path = output_dir / "dutch_edge_cases_dataset.json"
    edge_path.write_text(json.dumps(edge, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  → {edge_path} ({len(edge)} samples)")

    # Validate
    if args.validate:
        ok1 = validate_dataset(normal, "dutch_generated_dataset.json")
        ok2 = validate_dataset(edge, "dutch_edge_cases_dataset.json", check_targets=False)
        if not (ok1 and ok2):
            sys.exit(1)
    else:
        # Always print basic stats
        counts_n = _count_entities(normal)
        counts_e = _count_entities(edge)
        print(f"\nNormal: {len(normal)} samples, {sum(counts_n.values())} spans")
        print(f"Edge:   {len(edge)} samples, {sum(counts_e.values())} spans")


if __name__ == "__main__":
    main()
