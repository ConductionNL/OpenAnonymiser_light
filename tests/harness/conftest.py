"""Pytest config voor de flavor test-harness.

Registreert de `harness` marker en biedt per-flavor httpx-clients die
praten tegen de poorten uit `compose.yaml`.

De tests skippen automatisch als de betreffende container niet
bereikbaar is — zo kan `pytest tests/` in de normale CI draaien zonder
dat de harness interfereert.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx
import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

CLASSIC_URL = os.getenv("HARNESS_CLASSIC_URL", "http://localhost:8081")
GPU_URL = os.getenv("HARNESS_GPU_URL", "http://localhost:8082")


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "harness: tests die tegen een draaiende container van een specifieke flavor worden uitgevoerd",
    )


def _client_or_skip(base_url: str, flavor: str) -> httpx.Client:
    c = httpx.Client(base_url=base_url, timeout=60.0)
    try:
        r = c.get("/api/v1/health")
        if r.status_code != 200:
            c.close()
            pytest.skip(f"{flavor} container op {base_url} reageerde met {r.status_code}")
    except httpx.RequestError as exc:
        c.close()
        pytest.skip(f"{flavor} container op {base_url} niet bereikbaar: {exc}")
    return c


@pytest.fixture(scope="session")
def classic_client() -> httpx.Client:
    c = _client_or_skip(CLASSIC_URL, "classic")
    yield c
    c.close()


@pytest.fixture(scope="session")
def gpu_client() -> httpx.Client:
    c = _client_or_skip(GPU_URL, "gpu")
    yield c
    c.close()
