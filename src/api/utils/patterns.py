from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class DutchPhoneNumberRecognizer(PatternRecognizer):
    """Herkenner voor Nederlandse telefoonnummers.

    Gebruikt een regex-patroon voor mobiele en vaste nummers in NL-formaat.
    """

    def __init__(
        self,
        context: Optional[List[str]] = None,
        supported_language: str = "nl",
    ) -> None:
        patterns = [
            Pattern("DUTCH_PHONE", r"(?<!\w)(?:0|(?:\+|00)31)[- ]?(?:\d[- ]?){9}\b", 0.6)
        ]
        super().__init__(
            supported_entity="PHONE_NUMBER",
            patterns=patterns,
            context=context,  # type: ignore[arg-type]
            supported_language=supported_language,
        )


class DutchIBANRecognizer(PatternRecognizer):
    """Herkenner voor IBAN bankrekeningnummers.

    Ondersteunt Nederlandse IBANs (beginnend met 'NL') en internationale IBANs,
    in zowel aaneengesloten als gespatieerde vormen.
    """

    def __init__(
        self,
        context: Optional[List[str]] = None,
        supported_language: str = "nl",
    ) -> None:
        patterns = [
            # Specifiek NL-patroon met of zonder spaties
            Pattern(
                "DUTCH_IBAN",
                r"\bNL\d{2}\s?[A-Z]{4}(?:\s?\d{10}|\s?\d{4}\s?\d{4}\s?\d{2})\b",
                0.6,
            ),
            # Internationaal IBAN (niet-NL landcodes; min 2 groepen van 4 na het controlegetal)
            # NL wordt uitgesloten: NL IBANs vallen onder DUTCH_IBAN, BTW-nummers beginnen ook met NL
            Pattern(
                "INTL_IBAN",
                r"\b(?!NL)[A-Z]{2}\d{2}(?:\s?[A-Z0-9]{4}){2,7}(?:\s?[A-Z0-9]{1,4})?\b",
                0.55,
            ),
        ]
        super().__init__(
            supported_entity="IBAN",
            patterns=patterns,
            context=context,  # type: ignore[arg-type]
            supported_language=supported_language,
        )


class EmailRecognizer(PatternRecognizer):
    """Herkenner voor e-mailadressen volgens het standaard e-mailpatroon."""

    def __init__(
        self,
        context: Optional[List[str]] = None,
        supported_language: str = "nl",
    ) -> None:
        patterns = [
            Pattern(
                "EMAIL_ADDRESS",
                r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                0.6,
            )
        ]
        super().__init__(
            supported_entity="EMAIL",
            patterns=patterns,
            context=context,  # type: ignore[arg-type]
            supported_language=supported_language,
        )


class DutchBSNRecognizer(PatternRecognizer):
    def __init__(self, context: Optional[List[str]] = None) -> None:
        pattern = Pattern(
            "NL_BSN",
            r"\b(?:\d{9}|\d{3}[- ]?\d{3}[- ]?\d{3})\b",
            0.6,
        )
        super().__init__(
            supported_entity="BSN",
            patterns=[pattern],
            context=context,  # type: ignore[arg-type]
            supported_language="nl",
        )

    def validate_result(self, pattern_text: str) -> bool:
        """Validate BSN checksum using the 11-check algorithm."""
        return self._is_valid_bsn(pattern_text)

    def _is_valid_bsn(self, bsn: str) -> bool:
        """Check if BSN passes 11-check: 9th digit must equal (sum % 11)."""
        digits = [int(d) for d in bsn if d.isdigit()]
        
        if len(digits) != 9:
            return False

        total = sum((9 - i) * digits[i] for i in range(8))
        expected_check = total % 11
        return digits[8] == expected_check

class DutchPostcodeRecognizer(PatternRecognizer):
    def __init__(
        self, context: Optional[List[str]] = None, supported_language: str = "nl"
    ) -> None:
        # Negative lookbehind prevents matching year tails like "2025 IN" from dates
        pattern = Pattern(
            "NL_POSTCODE",
            r"(?<!\d[-/.])\b(?!0{4})(?:[1-9]\d{3})\s?(?!SA|SD|SS)[A-HJ-NP-Z]{2}\b",
            0.55,
        )
        super().__init__(
            "POSTCODE",
            patterns=[pattern],
            context=context,  # type: ignore[arg-type]
            supported_language=supported_language,
        )


# BTW-/VAT-nummer (NL999999999B99 – nieuw formaat)
class DutchVATRecognizer(PatternRecognizer):
    def __init__(
        self, context: Optional[List[str]] = None, supported_language: str = "nl"
    ) -> None:
        pattern = Pattern("NL_VAT", r"\bNL\d{9}B\d{2}\b", 0.6)
        super().__init__(
            "VAT_NUMBER",
            patterns=[pattern],
            context=context,  # type: ignore[arg-type]
            supported_language=supported_language,
        )


# KvK-nummer (8 cijfers in Handelsregister)
class DutchKvKRecognizer(PatternRecognizer):
    def __init__(
        self, context: Optional[List[str]] = None, supported_language: str = "nl"
    ) -> None:
        patterns = [
            Pattern("KVK_8_DIGIT", r"(?<!\d[/ ])\b\d{8}\b", 0.45)  # raise score with context
        ]
        super().__init__(
            "KVK_NUMBER",
            patterns=patterns,
            context=context,  # type: ignore[arg-type]
            supported_language=supported_language,
        )


# Nederlands kenteken — sidecodes 1-14
_LICENSE_PATTERNS = [
    # Sidecodes 1-6: elk segment 2 tekens
    r"[A-Z]{2}-\d{2}-\d{2}",       # 1: XX-99-99
    r"\d{2}-\d{2}-[A-Z]{2}",       # 2: 99-99-XX
    r"\d{2}-[A-Z]{2}-\d{2}",       # 3: 99-XX-99
    r"[A-Z]{2}-\d{2}-[A-Z]{2}",    # 4: XX-99-XX
    r"[A-Z]{2}-[A-Z]{2}-\d{2}",    # 5: XX-XX-99
    r"\d{2}-[A-Z]{2}-[A-Z]{2}",    # 6: 99-XX-XX
    # Sidecodes 7-14: segmenten met 1 of 3 tekens
    r"\d{2}-[A-Z]{3}-\d",          # 7: 99-XXX-9
    r"\d-[A-Z]{3}-\d{2}",          # 8: 9-XXX-99
    r"[A-Z]{2}-\d{3}-[A-Z]",       # 9: XX-999-X
    r"[A-Z]-\d{3}-[A-Z]{2}",       # 10: X-999-XX
    r"[A-Z]{3}-\d{2}-[A-Z]",       # 11: XXX-99-X
    r"[A-Z]-\d{2}-[A-Z]{3}",       # 12: X-99-XXX
    r"\d-[A-Z]{2}-\d{3}",          # 13: 9-XX-999
    r"\d{3}-[A-Z]{2}-\d",          # 14: 999-XX-9
]


class DutchLicensePlateRecognizer(PatternRecognizer):
    def __init__(
        self, context: Optional[List[str]] = None, supported_language: str = "nl"
    ) -> None:
        pattern = Pattern("NL_PLATE", rf"\b(?:{'|'.join(_LICENSE_PATTERNS)})\b", 0.5)
        super().__init__(
            "LICENSE_PLATE",
            patterns=[pattern],
            context=context,  # type: ignore[arg-type]
            supported_language=supported_language,
        )


# Taal-onafhankelijke IPv4-adres-herkenner
class IPv4Recognizer(PatternRecognizer):
    def __init__(
        self, context: Optional[List[str]] = None, supported_language: str = "nl"
    ) -> None:
        pattern = Pattern(
            "IPV4",
            r"\b(?:25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)"
            r"(?:\.(?:25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)){3}\b",
            0.5,
        )
        super().__init__(
            "IP_ADDRESS",
            patterns=[pattern],
            context=context,  # type: ignore[arg-type]
            supported_language=supported_language,
        )


class DutchDateRecognizer(PatternRecognizer):
    def __init__(
        self, context: Optional[List[str]] = None, supported_language: str = "nl"
    ) -> None:
        patterns = [
            # dd-mm-yyyy, dd/mm/yyyy, dd.mm.yyyy
            Pattern(
                "DATE_DD_MM_YYYY",
                r"\b(?:0?[1-9]|[12][0-9]|3[01])[\-/.](?:0?[1-9]|1[0-2])[\-/.](?:19|20)\d{2}\b",
                0.5,
            ),
            # mm-dd-yyyy, mm/dd/yyyy, mm.dd.yyyy
            Pattern(
                "DATE_MM_DD_YYYY",
                r"\b(?:0?[1-9]|1[0-2])[\-/.](?:0?[1-9]|[12][0-9]|3[01])[\-/.](?:19|20)\d{2}\b",
                0.5,
            ),
            # yyyy-mm-dd
            Pattern(
                "DATE_YYYY_MM_DD",
                r"\b(?:19|20)\d{2}[\-/.](?:0?[1-9]|1[0-2])[\-/.](?:0?[1-9]|[12][0-9]|3[01])\b",
                0.5,
            ),
            # dd mm yy (space-separated, 2-digit year)
            # Negative lookahead prevents matching IP fragments like 10.10.10(.1)
            Pattern(
                "DATE_DD_MM_YY",
                r"\b(?:0?[1-9]|[12][0-9]|3[01])[\s/.-](?:0?[1-9]|1[0-2])[\s/.-]\d{2}(?!\.\d)\b",
                0.45,
            ),
            # 1 september 2020 (spelled-out months in Dutch, case-insensitive)
            Pattern(
                "DATE_DD_MONTH_YYYY",
                r"(?i)\b(?:0?[1-9]|[12][0-9]|3[01])\s+(?:januari|februari|maart|april|mei|juni|juli|augustus|september|oktober|november|december)\s+(?:19|20)\d{2}\b",
                0.5,
            ),
        ]
        super().__init__(
            supported_entity="DATE_TIME",
            patterns=patterns,
            context=context,  # type: ignore[arg-type]
            supported_language=supported_language,
        )


class DutchPassportIdRecognizer(PatternRecognizer):
    """Herkenner voor Nederlandse paspoort-/identiteitskaartnummers.

    Regels:
    - Positie 1-2: letters (hoofdletters), zonder de letter 'O'.
    - Positie 3-8: letters (zonder 'O') of cijfers; sinds 2019 geen '0' meer in nieuwe documenten.
    - Positie 9: cijfer (in nieuwe documenten 1-9).

    We ondersteunen daarom twee patronen:
    - NL_DOC_OLD: toestaat '0' (oude documenten)
    - NL_DOC_NEW: sluit '0' uit (nieuwe documenten)
    """

    def __init__(
        self, context: Optional[List[str]] = None, supported_language: str = "nl"
    ) -> None:
        patterns = [
            # Oud formaat: letters zonder 'O', pos 3-8 letters/cijfers (0-9), pos 9 cijfer (0-9)
            Pattern(
                "NL_DOC_OLD",
                r"\b[A-NP-Z]{2}[A-NP-Z0-9]{6}\d\b",
                0.55,
            ),
            # Nieuw formaat: geen '0' meer; cijfers 1-9, pos 9 ook 1-9
            Pattern(
                "NL_DOC_NEW",
                r"\b[A-NP-Z]{2}(?:[A-NP-Z]|[1-9]){6}[1-9]\b",
                0.6,
            ),
        ]
        super().__init__(
            supported_entity="ID_NO",
            patterns=patterns,
            context=context,  # type: ignore[arg-type]
            supported_language=supported_language,
        )


class CaseNumberRecognizer(PatternRecognizer):
    """Herkenner voor diverse (rechts)zaak- en dossiernummers.

    Ondersteunt o.a. Z-/WOO-/BEZWAAR-/INT-/VTH-/WP-nummers, algemene jaar/nummer,
    BAG-ID (16 cijfers), UUID-achtige zaak-ID's, en bekende gerecht-formats.
    """

    def __init__(
        self, context: Optional[List[str]] = None, supported_language: str = "nl"
    ) -> None:
        patterns = [
            # Z-YYYY-999999 (Z-jaar-nummer), ook permissief met '-' of '/'
            Pattern(
                "CASE_Z",
                r"\bZ[-\/]?\d{4}[-\/]?\d{4,6}\b",
                0.55,
            ),
            # WOO/BEZWAAR/INT/VTH/WP-YYYY-999 (of langer)
            Pattern(
                "CASE_PREFIXED",
                r"\b(?:WOO|BEZWAAR|INT|VTH|WP)[-\/]?\d{4}[-\/]?\d{3,6}\b",
                0.6,
            ),
            # Algemeen Jaar-Nummer (risico op false positives, lagere score)
            Pattern(
                "CASE_YEAR_NUMBER",
                r"\b\d{4}[-\/]\d{4,6}\b",
                0.45,
            ),
            # BAG ID, exact 16 cijfers (lager vertrouwen want generiek)
            Pattern(
                "CASE_BAG_ID",
                r"\b\d{16}\b",
                0.4,
            ),
            # UUID-stijl Zaak-ID — lage score want UUIDs worden ook voor
            # device-IDs en andere niet-zaak entiteiten gebruikt
            Pattern(
                "CASE_UUID",
                r"(?i)\b[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\b",
                0.35,
            ),
            # Civiel: C/XX/NNNNNN (meer digits toegestaan)
            Pattern(
                "CASE_C_CIVIL",
                r"\bC\/\d{2}\/\d{5,8}\b",
                0.55,
            ),
            # Bestuurlijk: AWB 21/12345
            Pattern(
                "CASE_AWB",
                r"\bAWB\s?\d{2}\/\d{3,6}\b",
                0.6,
            ),
            # Hoge Raad: HR 21/00123
            Pattern(
                "CASE_HR",
                r"\bHR\s?\d{2}\/\d{5}\b",
                0.6,
            ),
            # Gerechtshof: 200.12345
            Pattern(
                "CASE_GERECHTSHOF",
                r"\b200\.\d{5}\b",
                0.55,
            ),
            # Strafzaak OM: 08/123456-89
            Pattern(
                "CASE_OM",
                r"\b\d{2}\/\d{6}-\d{2}\b",
                0.6,
            ),
            # Algemeen: RBAMS 21/12345 (of andere rechtbankcodes 4-5 letters)
            Pattern(
                "CASE_COURT_GENERIC",
                r"\b[A-Z]{4,5}\s?\d{2}\/\d{3,6}\b",
                0.55,
            ),
        ]
        super().__init__(
            supported_entity="CASE_NO",
            patterns=patterns,
            context=context,  # type: ignore[arg-type]
            supported_language=supported_language,
        )


class MACAddressRecognizer(PatternRecognizer):
    """Herkenner voor MAC-adressen (IEEE 802).

    Ondersteunt colon-separated (AA:BB:CC:DD:EE:FF),
    dash-separated (AA-BB-CC-DD-EE-FF) en Cisco dot-notatie (AABB.CCDD.EEFF).
    """

    def __init__(
        self, context: Optional[List[str]] = None, supported_language: str = "nl"
    ) -> None:
        patterns = [
            Pattern(
                "MAC_COLON",
                r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b",
                0.9,
            ),
            Pattern(
                "MAC_DASH",
                r"\b(?:[0-9A-Fa-f]{2}-){5}[0-9A-Fa-f]{2}\b",
                0.9,
            ),
            Pattern(
                "MAC_CISCO_DOT",
                r"\b(?:[0-9A-Fa-f]{4}\.){2}[0-9A-Fa-f]{4}\b",
                0.85,
            ),
        ]
        super().__init__(
            supported_entity="MAC_ADDRESS",
            patterns=patterns,
            context=context,  # type: ignore[arg-type]
            supported_language=supported_language,
        )


class DutchDriversLicenseRecognizer(PatternRecognizer):
    """Herkenner voor Nederlands rijbewijsnummer (10 cijfers).

    Detecteert exact 10 opeenvolgende cijfers. Score relatief laag vanwege
    mogelijke false positives bij generieke cijfersreeksen.
    """

    def __init__(
        self, context: Optional[List[str]] = None, supported_language: str = "nl"
    ) -> None:
        patterns = [
            Pattern(
                "NL_DRIVERS_LICENSE",
                r"\b\d{10}\b",
                0.45,
            )
        ]
        super().__init__(
            supported_entity="DRIVERS_LICENSE",
            patterns=patterns,
            context=context,  # type: ignore[arg-type]
            supported_language=supported_language,
        )
