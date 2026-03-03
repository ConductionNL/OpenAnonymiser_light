import logging.config
import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Applicatieconfiguratie voor de Presidio-NL API.

    Bevat standaardwaarden voor debugmodus, ondersteunde entiteiten, taal,
    en de te gebruiken NLP-modellen (spaCy).
    """

    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    # Default entity types returned when no filter is specified.
    # Covers the most common PII — all recognizers may produce additional types.
    DEFAULT_ENTITIES = [
        "PERSON",
        "LOCATION",
        "ORGANIZATION",
        "PHONE_NUMBER",
        "EMAIL",
        "IBAN",
        "BSN",
        "DATE_TIME",
    ]

    # Full set of entity types produced by all registered recognizers.
    # Used for request validation and Swagger documentation.
    ALL_SUPPORTED_ENTITIES = [
        # NER (SpaCy via SpacyRecognizer)
        "PERSON",
        "LOCATION",
        "ORGANIZATION",
        # Pattern recognizers
        "PHONE_NUMBER",
        "EMAIL",
        "IBAN",
        "BSN",
        "DATE_TIME",
        "ID_NO",
        "DRIVERS_LICENSE",
        "CASE_NO",
        "VAT_NUMBER",
        "KVK_NUMBER",
        "LICENSE_PLATE",
        "IP_ADDRESS",
    ]

    DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "nl")
    DEFAULT_NLP_ENGINE = os.getenv("DEFAULT_NLP_ENGINE", "spacy").lower()
    DEFAULT_SPACY_MODEL = os.getenv("DEFAULT_SPACY_MODEL", "nl_core_news_md")
    ALLOWED_ORIGINS = ["*"]


settings: Settings = Settings()


def setup_logging() -> None:
    """Configureer logging voor de applicatie.

    Stelt zowel een file- als streamhandler in, met DEBUG- of INFO-niveau
    afhankelijk van de configuratie. Logt naar 'app.log' en de console.
    """
    console_log_level = "DEBUG" if settings.DEBUG else "INFO"
    log_dir = os.getenv("LOG_DIR", "/tmp/logs")
    os.makedirs(log_dir, exist_ok=True)
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
            },
            "handlers": {
                "file": {
                    "class": "logging.FileHandler",
                    "formatter": "default",
                    "level": "DEBUG",
                    "filename": os.path.join(log_dir, "app.log"),
                },
                "stream": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "level": console_log_level,
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {
                "level": "DEBUG",
                "handlers": ["file", "stream"],
            },
        }
    )

    logging.debug("Logging is configured.")
