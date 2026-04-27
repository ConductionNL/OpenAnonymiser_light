"""Harness tests voor flavor 1 (classic) — SpaCy NER + regex patterns.

Draait tegen een container die is opgespind via `compose.yaml`
(service `classic`, poort 8081). Skipt automatisch als die container
niet bereikbaar is.

Classic-belofte: volledige regex-dekking en redelijke NER-recall.
Geen GPU, geen externe deps.
"""

from __future__ import annotations

import httpx
import pytest

from tests.golden.runner import run as run_golden
from tests.harness.conftest import CLASSIC_URL

pytestmark = pytest.mark.harness


class TestHealth:
    def test_health_responds(self, classic_client: httpx.Client) -> None:
        r = classic_client.get("/api/v1/health")
        assert r.status_code == 200
        assert r.json() == {"ping": "pong"}


class TestGoldenRegexInvariants:
    """Harde ondergrens: elk regex-gedreven entity moet 100 % recall hebben."""

    REGEX_ENTITIES = {
        "EMAIL",
        "PHONE_NUMBER",
        "IBAN",
        "DATE_TIME",
        "BSN",
        "LICENSE_PLATE",
        "KVK_NUMBER",
        "CASE_NO",
        "IP_ADDRESS",
    }

    @pytest.fixture(scope="class")
    def report(self, classic_client: httpx.Client):  # noqa: ARG002 — fixture ensures service up
        return run_golden(CLASSIC_URL)

    @pytest.mark.parametrize("entity_type", sorted(REGEX_ENTITIES))
    def test_regex_entity_recall_is_perfect(self, report, entity_type: str) -> None:
        if entity_type not in report.per_entity:
            pytest.skip(f"entity_type {entity_type} niet in golden dataset")
        r = report.per_entity[entity_type]
        assert r.recall == 1.0, (
            f"classic moet {entity_type} altijd detecteren (regex-based). "
            f"Gemist: {[m for m in report.missing_examples if m.endswith(entity_type)]}"
        )


class TestGoldenNERBands:
    """Zachte ondergrens: NER-recall per entity-type binnen bandbreedte."""

    NER_THRESHOLDS = {
        "PERSON": 0.75,
        "LOCATION": 0.75,
        "ORGANIZATION": 0.50,
    }

    @pytest.fixture(scope="class")
    def report(self, classic_client: httpx.Client):  # noqa: ARG002
        return run_golden(CLASSIC_URL)

    @pytest.mark.parametrize("entity_type,threshold", sorted(NER_THRESHOLDS.items()))
    def test_ner_recall_above_threshold(
        self, report, entity_type: str, threshold: float
    ) -> None:
        if entity_type not in report.per_entity:
            pytest.skip(f"entity_type {entity_type} niet in golden dataset")
        r = report.per_entity[entity_type]
        assert r.recall >= threshold, (
            f"classic NER-recall op {entity_type} is {r.recall:.2f}, "
            f"onder drempel {threshold:.2f}. Golden-dataset mogelijk te streng "
            f"of model-drift — bekijk tests/golden/dataset.jsonl."
        )
