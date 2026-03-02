from typing import Optional

from pydantic import BaseModel, field_validator

from src.api.config import settings


class PIIEntity(BaseModel):
    """A single detected PII entity — mirrors Presidio's RecognizerResult fields."""

    entity_type: str
    text: str
    start: int
    end: int
    score: float


class AnalyzeTextRequest(BaseModel):
    """Request for POST /api/v1/analyze."""

    text: str
    language: str = settings.DEFAULT_LANGUAGE
    entities: Optional[list[str]] = None

    @field_validator("text")
    def validate_text_not_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Text cannot be empty")
        return value.strip()

    @field_validator("language")
    def validate_language(cls, value: str) -> str:
        supported = ["nl", "en"]
        if value not in supported:
            raise ValueError(f"Unsupported language: {value}. Supported: {', '.join(supported)}")
        return value


class AnalyzeTextResponse(BaseModel):
    """Response for POST /api/v1/analyze."""

    pii_entities: list[PIIEntity]
    text_length: int
    processing_time_ms: Optional[int] = None
    language: Optional[str] = None


class AnonymizeTextRequest(BaseModel):
    """Request for POST /api/v1/anonymize."""

    text: str
    language: str = settings.DEFAULT_LANGUAGE
    entities: Optional[list[str]] = None
    anonymization_strategy: str = "replace"

    @field_validator("text")
    def validate_text_not_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Text cannot be empty")
        return value.strip()

    @field_validator("language")
    def validate_language(cls, value: str) -> str:
        supported = ["nl", "en"]
        if value not in supported:
            raise ValueError(f"Unsupported language: {value}. Supported: {', '.join(supported)}")
        return value

    @field_validator("anonymization_strategy")
    def validate_strategy(cls, value: str) -> str:
        supported = ["replace", "mask", "redact", "hash"]
        if value not in supported:
            raise ValueError(f"Unsupported strategy: {value}. Supported: {', '.join(supported)}")
        return value


class AnonymizeTextResponse(BaseModel):
    """Response for POST /api/v1/anonymize."""

    original_text: str
    anonymized_text: str
    entities_found: list[PIIEntity]
    text_length: int
    processing_time_ms: Optional[int] = None
    anonymization_strategy: Optional[str] = None
