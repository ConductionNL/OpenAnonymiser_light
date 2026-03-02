"""Shared pytest fixtures for the OpenAnonymiser test suite."""

import os

import httpx
import pytest

BASE_URL = os.getenv("OPENANONYMISER_BASE_URL", "http://localhost:8080")


@pytest.fixture(scope="session")
def client() -> httpx.Client:
    """Session-scoped httpx client pointing at BASE_URL."""
    with httpx.Client(base_url=BASE_URL, timeout=60.0) as c:
        yield c
