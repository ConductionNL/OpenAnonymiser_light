import logging
from contextlib import asynccontextmanager
from importlib.metadata import PackageNotFoundError, version
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.config import settings, setup_logging
from src.api.routers import router

setup_logging()
logger = logging.getLogger(__name__)


def _log_versions() -> None:
    """Log installed Presidio and SpaCy versions at startup."""
    for pkg in ("presidio-analyzer", "presidio-anonymizer", "spacy"):
        try:
            logger.info("  %-28s %s", pkg, version(pkg))
        except PackageNotFoundError:
            logger.warning("  %-28s NOT INSTALLED", pkg)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """FastAPI lifespan: log versions and pre-warm the NLP engine on startup."""
    logger.info("Dependency versions:")
    _log_versions()

    # Pre-warm: load SpaCy model and Presidio engines now so first requests are fast.
    from src.api.services.text_analyzer import get_analyzer, get_anonymizer

    logger.info("Pre-warming Presidio engines (loading SpaCy model)...")
    get_analyzer()
    get_anonymizer()
    logger.info("Presidio engines ready.")

    yield


app = FastAPI(
    title="Presidio-NL API",
    description="API voor Nederlandse tekst analyse en anonimisatie",
    version="1.3.0",
    docs_url="/api/v1/docs",
    openapi_url="/api/v1/openapi.json",
    redoc_url="/api/v1/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router=router)
