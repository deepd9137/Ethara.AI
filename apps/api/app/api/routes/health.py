from fastapi import APIRouter
from fastapi.responses import ORJSONResponse
from sqlalchemy import text

from app.core.config import settings
from app.db.session import AsyncSessionLocal

router = APIRouter()


@router.get("/health", tags=["ops"])
async def health_check() -> ORJSONResponse:
    db_status = "ok"
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    status_code = 200 if db_status == "ok" else 503
    return ORJSONResponse(
        status_code=status_code,
        content={
            "status": "ok" if db_status == "ok" else "degraded",
            "db": db_status,
            "version": settings.APP_VERSION,
            "commit": settings.GIT_SHA,
        },
    )
