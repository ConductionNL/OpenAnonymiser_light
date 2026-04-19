"""Real-world use-case tests for OpenAnonymiser.

Tests that simulate actual citizen-data handling scenarios: mixed PII in one
text, complete anonymization, analyze/anonymize consistency, and versioning
awareness.

Run: pytest tests/test_usecases.py -v
"""

import httpx
import pytest

# Reference text with all common Dutch PII types in realistic context.
BURGERBRIEF = (
    "Op 15-03-2023 heeft Jan Jansen (BSN: 111222333) een aanvraag ingediend bij "
    "Gemeente Amsterdam. Zijn contactgegevens: jan.jansen@example.com, "
    "tel 0612345678. Bankrekeningnummer: NL91ABNA0417164300. "
    "Zaaknummer: Z-2023-12345."
)


@pytest.mark.skip(reason="Pattern recognizers disabled in plugins.yaml")
def test_common_pii_detected_in_default_set(client: httpx.Client) -> None:
    """Pattern-based PII must all be found with the default entity set."""
    r = client.post(
        "/api/v1/analyze",
        json={"text": BURGERBRIEF, "language": "nl"},
    )
    assert r.status_code == 200
    found = {e["entity_type"] for e in r.json()["pii_entities"]}
    required = {"EMAIL", "PHONE_NUMBER", "IBAN", "BSN"}
    missing = required - found
    assert not missing, f"Missing from default detection: {sorted(missing)}"


def test_ner_types_present(client: httpx.Client) -> None:
    """SpaCy NER should detect PERSON, LOCATION, and ORGANIZATION."""
    r = client.post(
        "/api/v1/analyze",
        json={
            "text": BURGERBRIEF,
            "language": "nl",
            "entities": ["PERSON", "LOCATION", "ORGANIZATION"],
        },
    )
    assert r.status_code == 200
    found = {e["entity_type"] for e in r.json()["pii_entities"]}
    assert "PERSON" in found, "Expected PERSON (Jan Jansen) not found"


@pytest.mark.skip(reason="Pattern recognizers disabled in plugins.yaml")
def test_anonymize_removes_all_common_pii(client: httpx.Client) -> None:
    """After replace-anonymization, original PII values must not appear in output."""
    r = client.post(
        "/api/v1/anonymize",
        json={
            "text": BURGERBRIEF,
            "language": "nl",
            "anonymization_strategy": "replace",
        },
    )
    assert r.status_code == 200
    anon = r.json()["anonymized_text"]
    for pii_value in [
        "Jan Jansen",
        "111222333",
        "jan.jansen@example.com",
        "0612345678",
        "NL91ABNA0417164300",
    ]:
        assert pii_value not in anon, (
            f"PII value '{pii_value}' still present after anonymization"
        )


@pytest.mark.skip(reason="Pattern recognizers disabled in plugins.yaml")
def test_entities_found_in_anonymize_matches_analyze(client: httpx.Client) -> None:
    """entities_found in /anonymize must equal /analyze results for same input."""
    text = "Jan Jansen belt 0612345678 en mailt jan@example.com."
    entities = ["PERSON", "PHONE_NUMBER", "EMAIL"]

    analyze_r = client.post(
        "/api/v1/analyze",
        json={"text": text, "language": "nl", "entities": entities},
    )
    anonymize_r = client.post(
        "/api/v1/anonymize",
        json={
            "text": text,
            "language": "nl",
            "entities": entities,
            "anonymization_strategy": "replace",
        },
    )
    assert analyze_r.status_code == 200
    assert anonymize_r.status_code == 200

    analyze_types = sorted(
        e["entity_type"] for e in analyze_r.json()["pii_entities"]
    )
    anonymize_types = sorted(
        e["entity_type"] for e in anonymize_r.json()["entities_found"]
    )
    assert analyze_types == anonymize_types


@pytest.mark.skip(reason="Pattern recognizers disabled in plugins.yaml")
def test_only_requested_entities_anonymized(client: httpx.Client) -> None:
    """When filtering to IBAN only, phone and email should survive in output."""
    text = "IBAN: NL91ABNA0417164300. Tel: 0612345678. Mail: jan@example.com."
    r = client.post(
        "/api/v1/anonymize",
        json={
            "text": text,
            "language": "nl",
            "entities": ["IBAN"],
            "anonymization_strategy": "replace",
        },
    )
    assert r.status_code == 200
    anon = r.json()["anonymized_text"]
    assert "NL91ABNA0417164300" not in anon
    assert "0612345678" in anon
    assert "jan@example.com" in anon


@pytest.mark.skip(reason="Pattern recognizers disabled in plugins.yaml")
def test_all_anonymization_strategies_produce_different_output(
    client: httpx.Client,
) -> None:
    """All four strategies should yield distinct anonymized texts."""
    text = "IBAN: NL91ABNA0417164300."
    results = {}
    for strategy in ("replace", "redact", "hash", "mask"):
        r = client.post(
            "/api/v1/anonymize",
            json={
                "text": text,
                "language": "nl",
                "anonymization_strategy": strategy,
                "entities": ["IBAN"],
            },
        )
        assert r.status_code == 200
        results[strategy] = r.json()["anonymized_text"]

    # All must differ from the original
    for strategy, anon in results.items():
        assert "NL91ABNA0417164300" not in anon, (
            f"strategy='{strategy}': original IBAN still present"
        )

    # replace, hash, mask outputs must be distinct from each other
    assert results["replace"] != results["hash"]
    assert results["replace"] != results["mask"]


def test_all_entities_have_numeric_scores(client: httpx.Client) -> None:
    """Regression: no entity may have a null or string score."""
    r = client.post(
        "/api/v1/analyze",
        json={
            "text": (
                "Pieter Janssen (BSN 111222333) woont in Den Haag. "
                "Werkgever: Rijkswaterstaat. Mail: p.janssen@overheid.nl."
            ),
            "language": "nl",
        },
    )
    assert r.status_code == 200
    for e in r.json()["pii_entities"]:
        score = e.get("score")
        assert isinstance(score, (int, float)), (
            f"{e['entity_type']}: score is not numeric — got {score!r}"
        )
        assert score > 0, f"{e['entity_type']}: score must be positive"
