"""Golden-dataset runner.

Leest `dataset.jsonl`, stuurt elk voorbeeld naar `/api/v1/analyze` van
een draaiende OpenAnonymiser-instance, en produceert per entity-type
een precision/recall/F1-rapport.

Gebruik:
    python tests/golden/runner.py --base-url http://localhost:8081
    python tests/golden/runner.py --base-url http://localhost:8082 \\
        --dataset tests/golden/dataset.jsonl --output /tmp/report.json

Kan standalone draaien of als module worden geïmporteerd door de
harness-tests (`test_option_1_classic.py`, `test_option_2_gpu.py`).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

import httpx

DEFAULT_DATASET = Path(__file__).parent / "dataset.jsonl"


@dataclass(frozen=True)
class Span:
    entity_type: str
    start: int
    end: int


@dataclass
class EntityReport:
    entity_type: str
    expected: int
    detected: int
    correct: int

    @property
    def precision(self) -> float:
        return self.correct / self.detected if self.detected else 0.0

    @property
    def recall(self) -> float:
        return self.correct / self.expected if self.expected else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0


@dataclass
class GoldenReport:
    base_url: str
    total_examples: int
    per_entity: dict[str, EntityReport]
    missing_examples: list[str]
    extra_detections: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "base_url": self.base_url,
            "total_examples": self.total_examples,
            "per_entity": {
                et: {**asdict(r), "precision": r.precision, "recall": r.recall, "f1": r.f1}
                for et, r in self.per_entity.items()
            },
            "missing_examples": self.missing_examples,
            "extra_detections": self.extra_detections,
        }


def _load_dataset(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def _spans(entities: Iterable[dict[str, Any]]) -> set[Span]:
    return {Span(e["entity_type"], int(e["start"]), int(e["end"])) for e in entities}


def run(base_url: str, dataset_path: Path = DEFAULT_DATASET) -> GoldenReport:
    dataset = _load_dataset(dataset_path)
    per_entity: dict[str, EntityReport] = {}
    missing: list[str] = []
    extra: list[dict[str, Any]] = []

    def _bump(et: str, **delta: int) -> None:
        if et not in per_entity:
            per_entity[et] = EntityReport(et, 0, 0, 0)
        r = per_entity[et]
        r.expected += delta.get("expected", 0)
        r.detected += delta.get("detected", 0)
        r.correct += delta.get("correct", 0)

    with httpx.Client(base_url=base_url, timeout=60.0) as client:
        for example in dataset:
            expected_spans = _spans(example["entities"])
            response = client.post(
                "/api/v1/analyze",
                json={"text": example["text"], "language": "nl"},
            )
            response.raise_for_status()
            detected_spans = _spans(response.json()["pii_entities"])

            for span in expected_spans:
                _bump(span.entity_type, expected=1)
                if span in detected_spans:
                    _bump(span.entity_type, correct=1)
                else:
                    missing.append(f"{example['id']}:{span.entity_type}@{span.start}")

            for span in detected_spans:
                _bump(span.entity_type, detected=1)
                if span not in expected_spans:
                    extra.append(
                        {
                            "id": example["id"],
                            "entity_type": span.entity_type,
                            "start": span.start,
                            "end": span.end,
                        }
                    )

    return GoldenReport(
        base_url=base_url,
        total_examples=len(dataset),
        per_entity=dict(sorted(per_entity.items())),
        missing_examples=missing,
        extra_detections=extra,
    )


def _print_report(report: GoldenReport) -> None:
    print(f"Base URL: {report.base_url}")
    print(f"Examples: {report.total_examples}")
    print(f"{'entity_type':<20} {'exp':>5} {'det':>5} {'ok':>5} {'P':>7} {'R':>7} {'F1':>7}")
    for et, r in report.per_entity.items():
        print(
            f"{et:<20} {r.expected:>5} {r.detected:>5} {r.correct:>5} "
            f"{r.precision:>7.2f} {r.recall:>7.2f} {r.f1:>7.2f}"
        )
    if report.missing_examples:
        print(f"\nMissed ({len(report.missing_examples)}):")
        for m in report.missing_examples:
            print(f"  - {m}")
    if report.extra_detections:
        print(f"\nExtra detections ({len(report.extra_detections)}):")
        for e in report.extra_detections[:10]:
            print(f"  - {e}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="OpenAnonymiser base URL")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path, help="schrijf JSON-rapport naar dit pad")
    args = parser.parse_args(argv)

    report = run(args.base_url, args.dataset)
    _print_report(report)
    if args.output:
        args.output.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
