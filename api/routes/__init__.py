"""
Routes package for the ValueInvestorsClub API.
Contains all API route handlers.
"""
from api.routes.companies import router as companies_router
from api.routes.crawl import router as crawl_router
from api.routes.health import router as health_router
from api.routes.holdings import router as holdings_router
from api.routes.ideas import router as ideas_router
from api.routes.investors import router as investors_router
from api.routes.review import router as review_router
from api.routes.search import router as search_router
from api.routes.users import router as users_router

__all__ = [
    "health_router",
    "ideas_router",
    "companies_router",
    "users_router",
    "holdings_router",
    "review_router",
    "investors_router",
    "search_router",
    "crawl_router",
]
