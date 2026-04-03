"""Plugin loader voor OpenAnonymiser.

Leest src/api/plugins.yaml en instantieert de geconfigureerde recognizers.
Ondersteunde typen: pattern, spacy, transformer, llm.

Gebruik:
    from src.api.utils.plugin_loader import load_plugins
    config = load_plugins()
    # config.recognizers  — lijst van EntityRecognizer instanties
    # config.ner_config   — dict voor NlpEngineProvider
    # config.pattern_entity_types  — frozenset van pattern-gedreven entity types
    # config.ner_entity_types      — frozenset van NER-gedreven entity types
"""

from __future__ import annotations

import importlib
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from presidio_analyzer.entity_recognizer import EntityRecognizer

logger = logging.getLogger(__name__)

_DEFAULT_PLUGINS_PATH = Path(__file__).resolve().parent.parent / "plugins.yaml"


@dataclass
class PluginConfig:
    """Resultaat van load_plugins()."""

    recognizers: list[EntityRecognizer] = field(default_factory=list)
    ner_config: dict[str, Any] = field(default_factory=dict)
    pattern_entity_types: frozenset[str] = field(default_factory=frozenset)
    ner_entity_types: frozenset[str] = field(default_factory=frozenset)
    language: str = "nl"


def _expand_env(value: str) -> str:
    """Vervang ${VAR:-default} en ${VAR} door de waarde uit de omgeving."""
    def _replace(match: re.Match) -> str:
        var, _, default = match.group(1).partition(":-")
        return os.environ.get(var, default)

    return re.sub(r"\$\{([^}]+)\}", _replace, value)


def _load_pattern_recognizer(name: str) -> EntityRecognizer:
    """Importeer een PatternRecognizer subclass uit patterns.py by naam."""
    module = importlib.import_module("src.api.utils.patterns")
    cls = getattr(module, name)
    return cls()


def _load_transformer_recognizer(cfg: dict[str, Any]) -> EntityRecognizer:
    """Laad een HuggingFace transformer NER recognizer (lazy import)."""
    try:
        from src.api.utils.adapters.transformer_adapter import TransformerRecognizer  # type: ignore[import]
    except ImportError as exc:
        raise ImportError(
            f"Transformer plugin '{cfg['name']}' vereist: pip install transformers torch. "
            f"Fout: {exc}"
        ) from exc
    return TransformerRecognizer(
        name=cfg["name"],
        model=cfg["model"],
        entities=cfg.get("entities", []),
        language=cfg.get("language", "nl"),
    )


def _load_llm_recognizer(cfg: dict[str, Any]) -> EntityRecognizer:
    """Laad een LLM-gebaseerde recognizer (lazy import)."""
    try:
        from src.api.utils.adapters.llm_adapter import LLMRecognizer  # type: ignore[import]
    except ImportError as exc:
        raise ImportError(
            f"LLM plugin '{cfg['name']}' vereist extra packages. Fout: {exc}"
        ) from exc
    return LLMRecognizer(
        name=cfg["name"],
        provider=cfg["provider"],
        model=cfg["model"],
        entities=cfg.get("entities", []),
        language=cfg.get("language", "nl"),
    )


def _load_gliner_recognizer(cfg: dict[str, Any]) -> EntityRecognizer:
    "Laad de GLiNER recognizer (lazy import)."
    try: from presidio_analyzer.predefined_recognizers import GLiNERRecognizer
    except ImportError as exc:
        raise ImportError(
            f"GLiNER plugin '{cfg['name']}' vereist package: 'presidio-analyzer[gliner]'. "
            f"Fout: {exc}"
        ) from exc
    return GLiNERRecognizer(
        model_name=cfg["model"],
        supported_language=cfg["supported_language"],
        entity_mapping=cfg.get("entity_mapping", {}),
        flat_ner=cfg.get("flat_ner", False),
        multi_label=cfg.get("multi_label", True),
        map_location=cfg.get("map_location", "cpu"),
    )


def load_plugins(plugins_path: Path | None = None) -> PluginConfig:
    """Laad plugin-configuratie en instantieer alle actieve recognizers.

    Args:
        plugins_path: Pad naar plugins.yaml. Standaard: PLUGINS_CONFIG env var
            of src/api/plugins.yaml.

    Returns:
        PluginConfig met geïnstantieerde recognizers en NER-configuratie.
    """
    if plugins_path is None:
        env_path = os.environ.get("PLUGINS_CONFIG")
        plugins_path = Path(env_path) if env_path else _DEFAULT_PLUGINS_PATH

    raw = yaml.safe_load(plugins_path.read_text(encoding="utf-8"))
    language = raw.get("language", "nl")

    # NER configuratie
    ner_cfg = raw.get("ner", {})
    ner_enabled = ner_cfg.get("enabled", True)
    ner_model = _expand_env(ner_cfg.get("model", "nl_core_news_lg"))
    ner_entities: list[str] = ner_cfg.get("entities", ["PERSON", "LOCATION", "ORGANIZATION"])
    ner_strength: float = ner_cfg.get("ner_strength", 0.85)

    nlp_config: dict[str, Any] = {}
    if ner_enabled:
        nlp_config = {
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": language, "model_name": ner_model}],
            "ner_model_configuration": {
                "labels_to_ignore": [],
                "model_to_presidio_entity_mapping": {
                    "PER": "PERSON", "PERSON": "PERSON",
                    "LOC": "LOCATION", "LOCATION": "LOCATION", "GPE": "LOCATION",
                    "ORG": "ORGANIZATION", "ORGANIZATION": "ORGANIZATION",
                },
                "low_score_entity_names": [],
                "default_score": ner_strength,
            },
        }

    # Pattern recognizers
    recognizers: list[EntityRecognizer] = []
    pattern_entity_types: set[str] = set()
    ner_entity_types: set[str] = set(ner_entities) if ner_enabled else set()

    for plugin in raw.get("recognizers", []):
        if not plugin.get("enabled", True):
            logger.debug("Plugin '%s' is uitgeschakeld, overgeslagen.", plugin["name"])
            continue

        plugin_type = plugin["type"]
        name = plugin["name"]

        try:
            if plugin_type == "pattern":
                recognizer = _load_pattern_recognizer(name)
                # Verzamel de entity types die dit pattern ondersteunt
                for et in recognizer.supported_entities:
                    pattern_entity_types.add(et)
                recognizers.append(recognizer)
                logger.debug("Pattern plugin geladen: %s", name)

            elif plugin_type == "transformer":
                recognizer = _load_transformer_recognizer(plugin)
                recognizers.append(recognizer)
                logger.debug("Transformer plugin geladen: %s", name)

            elif plugin_type == "llm":
                recognizer = _load_llm_recognizer(plugin)
                recognizers.append(recognizer)
                logger.debug("LLM plugin geladen: %s", name)
            
            elif plugin_type == "gliner":
                recognizer = _load_gliner_recognizer(plugin)
                recognizers.append(recognizer)
                logger.debug("GLiNER plugin geladen: %s", name)

            else:
                logger.warning("Onbekend plugin type '%s' voor '%s', overgeslagen.", plugin_type, name)

        except (ImportError, AttributeError) as exc:
            logger.error("Plugin '%s' kon niet geladen worden: %s", name, exc)
            raise

    logger.info(
        "Plugins geladen: %d recognizers, NER=%s (%s)",
        len(recognizers),
        "aan" if ner_enabled else "uit",
        ner_model if ner_enabled else "-",
    )

    return PluginConfig(
        recognizers=recognizers,
        ner_config=nlp_config,
        pattern_entity_types=frozenset(pattern_entity_types),
        ner_entity_types=frozenset(ner_entity_types),
        language=language,
    )
