"""Per-entity detection tests for all 15 supported entity types.

Uses realistic Dutch PII in context sentences. Each test filters on a single
entity type so Presidio's span-conflict resolution doesn't mask results.

Run: pytest tests/test_supported_entities.py -v
"""

import httpx


def _detected_types(client: httpx.Client, text: str, entities: list[str]) -> set[str]:
    r = client.post(
        "/api/v1/analyze",
        json={"text": text, "language": "nl", "entities": entities},
    )
    assert r.status_code == 200
    return {e["entity_type"] for e in r.json()["pii_entities"]}


def _detected_texts(client: httpx.Client, text: str, entities: list[str]) -> list[str]:
    r = client.post(
        "/api/v1/analyze",
        json={"text": text, "language": "nl", "entities": entities},
    )
    assert r.status_code == 200
    return [e["text"] for e in r.json()["pii_entities"]]


class TestNEREntities:
    """SpaCy NER-based entities (score 0.85)."""

    def test_person_detected(self, client: httpx.Client) -> None:
        types = _detected_types(
            client, "Pieter van den Berg belde gisteren.", ["PERSON"]
        )
        assert "PERSON" in types

    def test_location_detected(self, client: httpx.Client) -> None:
        types = _detected_types(
            client, "De vergadering vond plaats in Rotterdam.", ["LOCATION"]
        )
        assert "LOCATION" in types

    def test_organization_detected(self, client: httpx.Client) -> None:
        types = _detected_types(
            client,
            "ING Bank heeft de lening verstrekt.",
            ["ORGANIZATION"],
        )
        assert "ORGANIZATION" in types

    def test_ner_scores_are_floats(self, client: httpx.Client) -> None:
        r = client.post(
            "/api/v1/analyze",
            json={
                "text": "Jan Jansen werkt bij Rijkswaterstaat in Utrecht.",
                "language": "nl",
                "entities": ["PERSON", "LOCATION", "ORGANIZATION"],
            },
        )
        assert r.status_code == 200
        for e in r.json()["pii_entities"]:
            assert isinstance(e["score"], float), (
                f"{e['entity_type']}: expected float score, got {e['score']!r}"
            )
            assert 0.0 < e["score"] <= 1.0


class TestPatternEntities:
    """Regex pattern recognizer entities."""

    def test_phone_mobile(self, client: httpx.Client) -> None:
        types = _detected_types(
            client, "Bel ons op 0612345678.", ["PHONE_NUMBER"]
        )
        assert "PHONE_NUMBER" in types

    def test_phone_international_0031(self, client: httpx.Client) -> None:
        # +31 after a space doesn't trigger \b (both non-word chars) — use 0031 form.
        types = _detected_types(
            client, "Bereikbaar op 0031612345678.", ["PHONE_NUMBER"]
        )
        assert "PHONE_NUMBER" in types

    def test_email_detected(self, client: httpx.Client) -> None:
        texts = _detected_texts(
            client,
            "Stuur een e-mail naar support@example.nl voor meer informatie.",
            ["EMAIL"],
        )
        assert "support@example.nl" in texts

    def test_iban_nl(self, client: httpx.Client) -> None:
        texts = _detected_texts(
            client, "IBAN: NL91ABNA0417164300.", ["IBAN"]
        )
        assert "NL91ABNA0417164300" in texts

    def test_iban_nl_spaced(self, client: httpx.Client) -> None:
        texts = _detected_texts(
            client, "Rekeningnummer: NL91 ABNA 0417 1643 00.", ["IBAN"]
        )
        assert any("NL91" in t for t in texts)

    def test_bsn_nine_digits(self, client: httpx.Client) -> None:
        types = _detected_types(client, "BSN: 111222333.", ["BSN"])
        assert "BSN" in types

    def test_date_dd_mm_yyyy(self, client: httpx.Client) -> None:
        types = _detected_types(
            client, "Geboortedatum: 15-03-1990.", ["DATE_TIME"]
        )
        assert "DATE_TIME" in types

    def test_date_spelled_out(self, client: httpx.Client) -> None:
        types = _detected_types(
            client,
            "Op 1 september 2020 werd het ingediend.",
            ["DATE_TIME"],
        )
        assert "DATE_TIME" in types

    def test_id_no_passport(self, client: httpx.Client) -> None:
        types = _detected_types(
            client, "Paspoortnummer: AB1234561.", ["ID_NO"]
        )
        assert "ID_NO" in types

    def test_vat_number(self, client: httpx.Client) -> None:
        texts = _detected_texts(
            client, "BTW-nummer: NL123456789B01.", ["VAT_NUMBER"]
        )
        assert "NL123456789B01" in texts

    def test_license_plate(self, client: httpx.Client) -> None:
        types = _detected_types(
            client, "Kenteken AB-12-CD werd gesignaleerd.", ["LICENSE_PLATE"]
        )
        assert "LICENSE_PLATE" in types

    def test_ip_address(self, client: httpx.Client) -> None:
        texts = _detected_texts(
            client, "Verbonden via IP 192.168.1.1.", ["IP_ADDRESS"]
        )
        assert "192.168.1.1" in texts

    def test_case_no_z_format(self, client: httpx.Client) -> None:
        types = _detected_types(
            client,
            "Zaaknummer Z-2023-12345 is in behandeling.",
            ["CASE_NO"],
        )
        assert "CASE_NO" in types

    def test_case_no_awb_format(self, client: httpx.Client) -> None:
        types = _detected_types(
            client, "Bezwaar AWB 21/12345 ingediend.", ["CASE_NO"]
        )
        assert "CASE_NO" in types

    def test_drivers_license(self, client: httpx.Client) -> None:
        types = _detected_types(
            client, "Rijbewijsnummer: 1234567890.", ["DRIVERS_LICENSE"]
        )
        assert "DRIVERS_LICENSE" in types

    def test_kvk_number(self, client: httpx.Client) -> None:
        types = _detected_types(
            client, "KvK-nummer: 12345678.", ["KVK_NUMBER"]
        )
        assert "KVK_NUMBER" in types


class TestEmailNotOrganization:
    """Regression: SpaCy NER must not tag emails as ORGANIZATION."""

    def test_no_organization_overlapping_email(self, client: httpx.Client) -> None:
        r = client.post(
            "/api/v1/analyze",
            json={
                "text": "Stuur een mail naar support@example.nl voor meer informatie.",
                "language": "nl",
            },
        )
        assert r.status_code == 200
        entities = r.json()["pii_entities"]
        email_spans = [
            (e["start"], e["end"])
            for e in entities
            if e["entity_type"] == "EMAIL"
        ]
        org_spans = [
            (e["start"], e["end"])
            for e in entities
            if e["entity_type"] == "ORGANIZATION"
        ]
        for es, ee in email_spans:
            for os_, oe in org_spans:
                assert not (es < oe and ee > os_), (
                    f"ORGANIZATION [{os_}:{oe}] overlaps with EMAIL [{es}:{ee}] — "
                    "SpaCy NER false positive should be filtered"
                )

    def test_email_entity_is_detected(self, client: httpx.Client) -> None:
        """The email itself must still be detected as EMAIL."""
        r = client.post(
            "/api/v1/analyze",
            json={
                "text": "Stuur een mail naar support@example.nl.",
                "language": "nl",
                "entities": ["EMAIL"],
            },
        )
        assert r.status_code == 200
        types = {e["entity_type"] for e in r.json()["pii_entities"]}
        assert "EMAIL" in types


class TestPhoneVsDriversLicense:
    """Presidio returns all matching entity types per span (cross-type is by design).

    A 10-digit Dutch mobile number (e.g. 0612345678) matches both
    PHONE_NUMBER (score 0.60) and DRIVERS_LICENSE (score 0.45).
    Presidio's remove_duplicates only deduplicates same-type results,
    so both are returned. This is expected behavior.
    """

    def test_phone_number_is_detected(self, client: httpx.Client) -> None:
        r = client.post(
            "/api/v1/analyze",
            json={
                "text": "Bel 0612345678.",
                "language": "nl",
                "entities": ["PHONE_NUMBER"],
            },
        )
        assert r.status_code == 200
        types = {e["entity_type"] for e in r.json()["pii_entities"]}
        assert "PHONE_NUMBER" in types

    def test_phone_has_higher_score_than_drivers_license(
        self, client: httpx.Client
    ) -> None:
        """When both match, PHONE_NUMBER (0.60) scores higher than DRIVERS_LICENSE (0.45)."""
        r = client.post(
            "/api/v1/analyze",
            json={
                "text": "Bel 0612345678.",
                "language": "nl",
                "entities": ["PHONE_NUMBER", "DRIVERS_LICENSE"],
            },
        )
        assert r.status_code == 200
        entities = r.json()["pii_entities"]
        phone = next((e for e in entities if e["entity_type"] == "PHONE_NUMBER"), None)
        drivers = next(
            (e for e in entities if e["entity_type"] == "DRIVERS_LICENSE"), None
        )
        assert phone is not None, "PHONE_NUMBER must be detected"
        if drivers is not None:
            assert phone["score"] > drivers["score"], (
                "PHONE_NUMBER score must exceed DRIVERS_LICENSE score on same token"
            )
