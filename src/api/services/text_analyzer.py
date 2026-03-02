import logging
from typing import Dict, List, Optional

from presidio_analyzer import AnalyzerEngine, RecognizerRegistry, RecognizerResult
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_analyzer.predefined_recognizers import SpacyRecognizer
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import EngineResult, OperatorConfig

from src.api.config import settings
from src.api.utils.patterns import (
    CaseNumberRecognizer,
    DutchBSNRecognizer,
    DutchDateRecognizer,
    DutchDriversLicenseRecognizer,
    DutchIBANRecognizer,
    DutchKvKRecognizer,
    DutchLicensePlateRecognizer,
    DutchPassportIdRecognizer,
    DutchPhoneNumberRecognizer,
    DutchVATRecognizer,
    EmailRecognizer,
    IPv4Recognizer,
)

logger = logging.getLogger(__name__)

# Module-level singletons — loaded once at first use
_analyzer_engine: Optional[AnalyzerEngine] = None
_anonymizer_engine: Optional[AnonymizerEngine] = None

# Entity types produced by pattern recognizers (regex-based, high precision).
_PATTERN_ENTITY_TYPES: frozenset[str] = frozenset(
    {
        "PHONE_NUMBER",
        "EMAIL",
        "IBAN",
        "BSN",
        "DATE_TIME",
        "ID_NO",
        "DRIVERS_LICENSE",
        "VAT_NUMBER",
        "KVK_NUMBER",
        "LICENSE_PLATE",
        "IP_ADDRESS",
        "CASE_NO",
    }
)

# Entity types produced by SpaCy NER.
_NER_ENTITY_TYPES: frozenset[str] = frozenset({"PERSON", "LOCATION", "ORGANIZATION"})

# Dutch SpaCy label → Presidio entity mapping.
# nl_core_news_* uses PER/LOC/ORG/GPE; GPE covers cities and countries.
_NL_LABEL_MAPPING = {
    "PER": "PERSON",
    "PERSON": "PERSON",
    "LOC": "LOCATION",
    "LOCATION": "LOCATION",
    "GPE": "LOCATION",
    "ORG": "ORGANIZATION",
    "ORGANIZATION": "ORGANIZATION",
}


def _build_analyzer() -> AnalyzerEngine:
    """Build Presidio AnalyzerEngine for Dutch text.

    Uses SpacyRecognizer for NER (PERSON/LOCATION/ORGANIZATION) and
    custom PatternRecognizer subclasses for all other Dutch PII types.
    """
    nlp_config = {
        "nlp_engine_name": "spacy",
        "models": [
            {"lang_code": settings.DEFAULT_LANGUAGE, "model_name": settings.DEFAULT_SPACY_MODEL}
        ],
        "ner_model_configuration": {
            "labels_to_ignore": [],  # keep all labels; default ignores ORG
            "model_to_presidio_entity_mapping": _NL_LABEL_MAPPING,
            "low_score_entity_names": [],
            "default_score": 0.85,
        },
    }

    nlp_engine = NlpEngineProvider(nlp_configuration=nlp_config).create_engine()

    registry = RecognizerRegistry()
    registry.supported_languages = [settings.DEFAULT_LANGUAGE]

    # NER via Presidio's SpacyRecognizer — handles Dutch PER/LOC/GPE/ORG with scoring
    registry.add_recognizer(
        SpacyRecognizer(
            supported_language=settings.DEFAULT_LANGUAGE,
            supported_entities=["PERSON", "LOCATION", "ORGANIZATION"],
            ner_strength=0.85,
        )
    )

    # Dutch pattern recognizers
    for recognizer in [
        DutchPhoneNumberRecognizer(),
        DutchIBANRecognizer(),
        DutchBSNRecognizer(),
        DutchDateRecognizer(),
        EmailRecognizer(),
        DutchPassportIdRecognizer(),
        DutchDriversLicenseRecognizer(),
        DutchVATRecognizer(),
        DutchKvKRecognizer(),
        DutchLicensePlateRecognizer(),
        IPv4Recognizer(),
        CaseNumberRecognizer(),
    ]:
        registry.add_recognizer(recognizer)

    engine = AnalyzerEngine(
        nlp_engine=nlp_engine,
        registry=registry,
        supported_languages=[settings.DEFAULT_LANGUAGE],
    )
    logger.info(
        "AnalyzerEngine initialized: SpacyRecognizer (NER) + %d pattern recognizers",
        12,
    )
    return engine


def get_analyzer() -> AnalyzerEngine:
    """Return the module-level AnalyzerEngine singleton, initializing if needed."""
    global _analyzer_engine
    if _analyzer_engine is None:
        _analyzer_engine = _build_analyzer()
    return _analyzer_engine


def get_anonymizer() -> AnonymizerEngine:
    """Return the module-level AnonymizerEngine singleton, initializing if needed."""
    global _anonymizer_engine
    if _anonymizer_engine is None:
        _anonymizer_engine = AnonymizerEngine()
    return _anonymizer_engine


def _remove_ner_overlapping_patterns(
    results: List[RecognizerResult],
) -> List[RecognizerResult]:
    """Drop NER results that overlap with a pattern recognizer result.

    SpaCy NER can misclassify structured tokens (email addresses, license
    plates, IBANs) as ORGANIZATION/PERSON/LOCATION. Pattern recognizers are
    more precise for these cases. When spans overlap, the pattern result wins.
    """
    pattern_results = [r for r in results if r.entity_type in _PATTERN_ENTITY_TYPES]
    if not pattern_results:
        return results

    def _overlaps_any_pattern(r: RecognizerResult) -> bool:
        return any(r.start < p.end and r.end > p.start for p in pattern_results)

    return [
        r
        for r in results
        if r.entity_type not in _NER_ENTITY_TYPES or not _overlaps_any_pattern(r)
    ]


def analyze(
    text: str,
    entities: Optional[List[str]] = None,
    language: str = settings.DEFAULT_LANGUAGE,
) -> List[RecognizerResult]:
    """Analyze text for PII using Presidio AnalyzerEngine.

    Args:
        text: Text to analyze.
        entities: Optional list of entity types to detect. None returns all.
        language: Language code (default: settings.DEFAULT_LANGUAGE).

    Returns:
        List of RecognizerResult — Presidio's native result type.
        NER results overlapping with pattern results are removed.
    """
    results = get_analyzer().analyze(text=text, entities=entities, language=language)
    return _remove_ner_overlapping_patterns(results)


def anonymize(
    text: str,
    analyzer_results: List[RecognizerResult],
    strategy: str = "replace",
) -> EngineResult:
    """Anonymize text using Presidio AnonymizerEngine.

    Args:
        text: Original text to anonymize.
        analyzer_results: RecognizerResults from analyze().
        strategy: Anonymization strategy (replace, redact, hash, mask).

    Returns:
        EngineResult — Presidio's native anonymization result.
    """
    operators = _build_operators(strategy, analyzer_results)
    return get_anonymizer().anonymize(
        text=text,
        analyzer_results=analyzer_results,
        operators=operators,
    )


def _build_operators(
    strategy: str, results: List[RecognizerResult]
) -> Dict[str, OperatorConfig]:
    """Build per-entity-type Presidio OperatorConfig from strategy.

    For 'replace': each entity type gets its own <ENTITY_TYPE> placeholder,
    matching Presidio's recommended approach for readable anonymized output.
    """
    if strategy == "redact":
        return {"DEFAULT": OperatorConfig("redact")}
    if strategy == "hash":
        return {"DEFAULT": OperatorConfig("hash")}
    if strategy == "mask":
        return {
            "DEFAULT": OperatorConfig(
                "mask", {"chars_to_mask": 6, "masking_char": "*", "from_end": False}
            )
        }
    # replace (default): <ENTITY_TYPE> per entity type
    operators: Dict[str, OperatorConfig] = {}
    for r in results:
        if r.entity_type not in operators:
            operators[r.entity_type] = OperatorConfig(
                "replace", {"new_value": f"<{r.entity_type}>"}
            )
    return operators
