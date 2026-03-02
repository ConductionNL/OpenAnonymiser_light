import logging
from typing import Dict, List, Optional

from presidio_analyzer import AnalyzerEngine, RecognizerRegistry, RecognizerResult
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_analyzer.predefined_recognizers import SpacyRecognizer
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import EngineResult, OperatorConfig

from src.api.config import settings
from src.api.utils.plugin_loader import load_plugins

logger = logging.getLogger(__name__)

# Module-level singletons — loaded once at first use
_analyzer_engine: Optional[AnalyzerEngine] = None
_anonymizer_engine: Optional[AnonymizerEngine] = None

# Populated by _build_analyzer() from the loaded plugin configuration.
_PATTERN_ENTITY_TYPES: frozenset[str] = frozenset()
_NER_ENTITY_TYPES: frozenset[str] = frozenset()


def _build_analyzer() -> AnalyzerEngine:
    """Build Presidio AnalyzerEngine from plugin configuration (plugins.yaml).

    Reads src/api/plugins.yaml (or PLUGINS_CONFIG env var) and instantiates
    all enabled recognizers. Pattern recognizers and optional transformer/LLM
    modules are loaded via the plugin_loader.
    """
    global _PATTERN_ENTITY_TYPES, _NER_ENTITY_TYPES

    plugin_cfg = load_plugins()
    _PATTERN_ENTITY_TYPES = plugin_cfg.pattern_entity_types
    _NER_ENTITY_TYPES = plugin_cfg.ner_entity_types

    nlp_engine = NlpEngineProvider(
        nlp_configuration=plugin_cfg.ner_config
    ).create_engine()

    registry = RecognizerRegistry()
    registry.supported_languages = [plugin_cfg.language]

    if plugin_cfg.ner_config:
        registry.add_recognizer(
            SpacyRecognizer(
                supported_language=plugin_cfg.language,
                supported_entities=list(plugin_cfg.ner_entity_types),
                ner_strength=plugin_cfg.ner_config.get(
                    "ner_model_configuration", {}
                ).get("default_score", 0.85),
            )
        )

    for recognizer in plugin_cfg.recognizers:
        registry.add_recognizer(recognizer)

    engine = AnalyzerEngine(
        nlp_engine=nlp_engine,
        registry=registry,
        supported_languages=[plugin_cfg.language],
    )
    logger.info(
        "AnalyzerEngine initialized: SpacyRecognizer (NER) + %d pattern recognizers",
        len(plugin_cfg.recognizers),
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
