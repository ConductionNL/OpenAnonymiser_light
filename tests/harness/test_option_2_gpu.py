"""Harness tests voor flavor 2 (gpu) — transformer-NER + regex patterns.

Draait tegen een container die is opgespind via `compose.yaml`
(service `gpu`, poort 8082). Skipt automatisch als die container
niet bereikbaar is.

GPU-belofte: hogere NER-recall + volledige regex-dekking.

CAVEAT (2026-04-17): de huidige `development`-image draait GLiNER
met **regex-patterns uit**. Vormvaste entities (EMAIL/PHONE/IBAN/etc.)
worden dan gemist. Tests die regex-dekking vereisen zijn daarom
`xfail`-gemarkeerd tot de flavor-split-PR
(`openspec/changes/split-into-3-flavors`) een
`plugins.gpu.yaml` oplevert met patterns AAN.

Haal de `xfail`-marker weg zodra dat landt.
"""

from __future__ import annotations

import httpx
import pytest

from tests.golden.runner import run as run_golden
from tests.harness.conftest import GPU_URL

pytestmark = pytest.mark.harness


class TestHealth:
    def test_health_responds(self, gpu_client: httpx.Client) -> None:
        r = gpu_client.get("/api/v1/health")
        assert r.status_code == 200
        assert r.json() == {"ping": "pong"}


class TestDTOContract:
    """Minimale DTO-check: het analyse-endpoint retourneert de verwachte shape."""

    def test_analyze_returns_expected_fields(self, gpu_client: httpx.Client) -> None:
        r = gpu_client.post(
            "/api/v1/analyze",
            json={"text": "Jan woont in Utrecht.", "language": "nl"},
        )
        assert r.status_code == 200
        data = r.json()
        assert set(data) >= {"pii_entities", "text_length", "language"}


class TestGoldenRegexInvariants:
    """Na flavor-split moeten regex-entities óók op gpu 100 % recall halen.

    Nu nog `xfail` omdat development patterns uit heeft staan.
    """

    REGEX_ENTITIES = {
        "EMAIL",
        "PHONE_NUMBER",
        "IBAN",
        "DATE_TIME",
        "BSN",
    }

    @pytest.fixture(scope="class")
    def report(self, gpu_client: httpx.Client):  # noqa: ARG002
        return run_golden(GPU_URL)

    @pytest.mark.xfail(
        reason="development-image heeft patterns disabled; fix landt met flavor-split-PR",
        strict=False,
    )
    @pytest.mark.parametrize("entity_type", sorted(REGEX_ENTITIES))
    def test_regex_entity_recall_is_perfect(self, report, entity_type: str) -> None:
        if entity_type not in report.per_entity:
            pytest.skip(f"entity_type {entity_type} niet in golden dataset")
        r = report.per_entity[entity_type]
        assert r.recall == 1.0


class TestGoldenNERBandsGPU:
    """GPU-flavor mag een hogere NER-drempel halen dan classic."""

    NER_THRESHOLDS = {
        "PERSON": 0.85,
        "LOCATION": 0.80,
        "ORGANIZATION": 0.60,
    }

    @pytest.fixture(scope="class")
    def report(self, gpu_client: httpx.Client):  # noqa: ARG002
        return run_golden(GPU_URL)

    @pytest.mark.parametrize("entity_type,threshold", sorted(NER_THRESHOLDS.items()))
    def test_ner_recall_above_threshold(
        self, report, entity_type: str, threshold: float
    ) -> None:
        if entity_type not in report.per_entity:
            pytest.skip(f"entity_type {entity_type} niet in golden dataset")
        r = report.per_entity[entity_type]
        assert r.recall >= threshold, (
            f"gpu NER-recall op {entity_type} is {r.recall:.2f}, "
            f"onder drempel {threshold:.2f}."
        )
