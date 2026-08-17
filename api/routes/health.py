"""
Health check routes for the ValueInvestorsClub API.
"""
import logging

from fastapi import APIRouter, Response, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from api.database.connection import engine
from api.observability import metrics, metrics_content_type

router = APIRouter()
logger = logging.getLogger(__name__)


def database_is_ready() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        metrics.record("database_ready", 1)
        return True
    except SQLAlchemyError as error:
        metrics.record("database_ready", 0)
        logger.warning("database_readiness_failed: %s", error)
        return False


@router.get("/health/live")
def health_live():
    return {"status": "alive"}


@router.get("/health/ready")
def health_ready():
    if not database_is_ready():
        return Response(
            content='{"status":"not_ready"}',
            media_type="application/json",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return {"status": "ready"}


@router.get("/health")
def health_check():
    """
    Health check endpoint.
    Returns a simple response indicating that the API is healthy.
    """
    return {"status": "alive"}


@router.get("/metrics")
def prometheus_metrics():
    return Response(content=metrics.render(), media_type=metrics_content_type)
