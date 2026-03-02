from fastapi.routing import APIRouter

from src.api.routers.text_analysis import text_analysis_router

router = APIRouter(prefix="/api/v1")


@router.get("/health")
def ping() -> dict[str, str]:
    """Health check endpoint.

    Geeft een eenvoudige status terug om te controleren of de API draait.
    """
    return {"ping": "pong"}


router.include_router(text_analysis_router)

__all__ = ["router"]
