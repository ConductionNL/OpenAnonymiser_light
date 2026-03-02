"""Tests for /api/v1/health, /api/v1/analyze, and /api/v1/anonymize.

Covers response structure, input validation, and all anonymization strategies.
Run: pytest tests/test_string_endpoints.py -v
"""

import httpx


class TestHealth:
    def test_health_returns_pong(self, client: httpx.Client) -> None:
        r = client.get("/api/v1/health")
        assert r.status_code == 200
        assert r.json() == {"ping": "pong"}


class TestAnalyzeStructure:
    def test_response_fields(self, client: httpx.Client) -> None:
        r = client.post(
            "/api/v1/analyze",
            json={"text": "Jan Jansen woont in Amsterdam.", "language": "nl"},
        )
        assert r.status_code == 200
        data = r.json()
        assert "pii_entities" in data
        assert "text_length" in data
        assert "processing_time_ms" in data
        assert "language" in data
        assert data["text_length"] == len("Jan Jansen woont in Amsterdam.")
        assert data["language"] == "nl"

    def test_entity_fields(self, client: httpx.Client) -> None:
        r = client.post(
            "/api/v1/analyze",
            json={"text": "Jan Jansen woont in Amsterdam.", "language": "nl"},
        )
        assert r.status_code == 200
        for entity in r.json()["pii_entities"]:
            assert "entity_type" in entity
            assert "text" in entity
            assert "start" in entity
            assert "end" in entity
            assert "score" in entity
            assert isinstance(entity["score"], float)
            assert 0.0 < entity["score"] <= 1.0
            assert entity["start"] >= 0
            assert entity["end"] > entity["start"]

    def test_entity_filter_limits_types(self, client: httpx.Client) -> None:
        r = client.post(
            "/api/v1/analyze",
            json={
                "text": "Jan Jansen woont in Amsterdam. Bel 0612345678.",
                "language": "nl",
                "entities": ["PERSON"],
            },
        )
        assert r.status_code == 200
        types = {e["entity_type"] for e in r.json()["pii_entities"]}
        assert types <= {"PERSON"}

    def test_processing_time_non_negative(self, client: httpx.Client) -> None:
        r = client.post(
            "/api/v1/analyze",
            json={"text": "Jan woont in Utrecht.", "language": "nl"},
        )
        assert r.status_code == 200
        assert r.json()["processing_time_ms"] >= 0


class TestAnalyzeValidation:
    def test_empty_text_rejected(self, client: httpx.Client) -> None:
        r = client.post("/api/v1/analyze", json={"text": "", "language": "nl"})
        assert r.status_code == 422

    def test_whitespace_text_rejected(self, client: httpx.Client) -> None:
        r = client.post("/api/v1/analyze", json={"text": "   ", "language": "nl"})
        assert r.status_code == 422

    def test_missing_text_rejected(self, client: httpx.Client) -> None:
        r = client.post("/api/v1/analyze", json={"language": "nl"})
        assert r.status_code == 422

    def test_unsupported_language_rejected(self, client: httpx.Client) -> None:
        r = client.post("/api/v1/analyze", json={"text": "test", "language": "fr"})
        assert r.status_code == 422

    def test_malformed_json_rejected(self, client: httpx.Client) -> None:
        r = client.post(
            "/api/v1/analyze",
            content='{"text": "test",',
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 422


class TestAnonymizeStructure:
    def test_response_fields(self, client: httpx.Client) -> None:
        r = client.post(
            "/api/v1/anonymize",
            json={"text": "Jan Jansen woont in Amsterdam.", "language": "nl"},
        )
        assert r.status_code == 200
        data = r.json()
        assert "original_text" in data
        assert "anonymized_text" in data
        assert "entities_found" in data
        assert "text_length" in data
        assert "processing_time_ms" in data
        assert "anonymization_strategy" in data

    def test_original_text_preserved(self, client: httpx.Client) -> None:
        text = "Jan Jansen woont in Amsterdam."
        r = client.post("/api/v1/anonymize", json={"text": text, "language": "nl"})
        assert r.status_code == 200
        assert r.json()["original_text"] == text

    def test_default_strategy_is_replace(self, client: httpx.Client) -> None:
        r = client.post(
            "/api/v1/anonymize",
            json={"text": "Jan Jansen woont in Amsterdam.", "language": "nl"},
        )
        assert r.status_code == 200
        assert r.json()["anonymization_strategy"] == "replace"

    def test_entity_filter_preserves_non_targeted(self, client: httpx.Client) -> None:
        r = client.post(
            "/api/v1/anonymize",
            json={
                "text": "Jan Jansen woont in Amsterdam.",
                "language": "nl",
                "entities": ["PERSON"],
                "anonymization_strategy": "replace",
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert "Amsterdam" in data["anonymized_text"]
        assert "Jan Jansen" not in data["anonymized_text"]


class TestAnonymizeStrategies:
    def test_replace_uses_entity_placeholder(self, client: httpx.Client) -> None:
        r = client.post(
            "/api/v1/anonymize",
            json={
                "text": "Bel 0612345678.",
                "language": "nl",
                "anonymization_strategy": "replace",
                "entities": ["PHONE_NUMBER"],
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert "<PHONE_NUMBER>" in data["anonymized_text"]
        assert "0612345678" not in data["anonymized_text"]

    def test_redact_removes_value(self, client: httpx.Client) -> None:
        r = client.post(
            "/api/v1/anonymize",
            json={
                "text": "Bel 0612345678.",
                "language": "nl",
                "anonymization_strategy": "redact",
                "entities": ["PHONE_NUMBER"],
            },
        )
        assert r.status_code == 200
        assert "0612345678" not in r.json()["anonymized_text"]

    def test_hash_replaces_with_hex_string(self, client: httpx.Client) -> None:
        r = client.post(
            "/api/v1/anonymize",
            json={
                "text": "IBAN: NL91ABNA0417164300.",
                "language": "nl",
                "anonymization_strategy": "hash",
                "entities": ["IBAN"],
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert "NL91ABNA0417164300" not in data["anonymized_text"]
        assert data["anonymized_text"] != data["original_text"]

    def test_mask_inserts_asterisks(self, client: httpx.Client) -> None:
        r = client.post(
            "/api/v1/anonymize",
            json={
                "text": "IBAN: NL91ABNA0417164300.",
                "language": "nl",
                "anonymization_strategy": "mask",
                "entities": ["IBAN"],
            },
        )
        assert r.status_code == 200
        assert "******" in r.json()["anonymized_text"]

    def test_invalid_strategy_rejected(self, client: httpx.Client) -> None:
        r = client.post(
            "/api/v1/anonymize",
            json={
                "text": "Jan woont in Amsterdam.",
                "language": "nl",
                "anonymization_strategy": "invalid",
            },
        )
        assert r.status_code == 422
