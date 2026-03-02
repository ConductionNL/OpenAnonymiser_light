import logging
import time

from fastapi import APIRouter, HTTPException, status
from presidio_analyzer import RecognizerResult

from src.api.config import settings
from src.api.dtos import (
    AnalyzeTextRequest,
    AnalyzeTextResponse,
    AnonymizeTextRequest,
    AnonymizeTextResponse,
    PIIEntity,
)
from src.api.services import text_analyzer

logger = logging.getLogger(__name__)
text_analysis_router = APIRouter(tags=["text-analysis"])


def _to_pii_entity(result: RecognizerResult, text: str) -> PIIEntity:
    """Convert a Presidio RecognizerResult to a PIIEntity DTO."""
    return PIIEntity(
        entity_type=result.entity_type,
        text=text[result.start : result.end],
        start=result.start,
        end=result.end,
        score=result.score,
    )


@text_analysis_router.post("/analyze")
async def analyze_text(request: AnalyzeTextRequest) -> AnalyzeTextResponse:
    """Analyze text for PII entities.

    Returns detected entities with their positions, types, and confidence scores.
    Scores come directly from Presidio: 0.85 default for SpaCy NER,
    pattern-specific floats for regex recognizers.
    """
    start_time = time.perf_counter()
    try:
        entities = request.entities or settings.DEFAULT_ENTITIES
        results = text_analyzer.analyze(
            text=request.text,
            entities=entities,
            language=request.language,
        )
        pii_entities = [_to_pii_entity(r, request.text) for r in results]
        processing_time_ms = int((time.perf_counter() - start_time) * 1000)

        logger.info(
            "analyze: %d entities in %dms | lang=%s entities=%s",
            len(pii_entities),
            processing_time_ms,
            request.language,
            entities,
        )
        return AnalyzeTextResponse(
            pii_entities=pii_entities,
            text_length=len(request.text),
            processing_time_ms=processing_time_ms,
            language=request.language,
        )
    except Exception as e:
        logger.error("analyze failed: %s", e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@text_analysis_router.post("/anonymize")
async def anonymize_text(request: AnonymizeTextRequest) -> AnonymizeTextResponse:
    """Anonymize PII entities in text.

    Runs Presidio AnalyzerEngine then AnonymizerEngine with the requested strategy.
    Returns original text, anonymized text, and the detected entities.
    """
    start_time = time.perf_counter()
    try:
        entities = request.entities or settings.DEFAULT_ENTITIES

        analyzer_results = text_analyzer.analyze(
            text=request.text,
            entities=entities,
            language=request.language,
        )
        engine_result = text_analyzer.anonymize(
            text=request.text,
            analyzer_results=analyzer_results,
            strategy=request.anonymization_strategy,
        )

        entities_found = [_to_pii_entity(r, request.text) for r in analyzer_results]
        processing_time_ms = int((time.perf_counter() - start_time) * 1000)

        logger.info(
            "anonymize: %d entities in %dms | strategy=%s lang=%s",
            len(entities_found),
            processing_time_ms,
            request.anonymization_strategy,
            request.language,
        )
        return AnonymizeTextResponse(
            original_text=request.text,
            anonymized_text=engine_result.text,
            entities_found=entities_found,
            text_length=len(request.text),
            processing_time_ms=processing_time_ms,
            anonymization_strategy=request.anonymization_strategy,
        )
    except Exception as e:
        logger.error("anonymize failed: %s", e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
