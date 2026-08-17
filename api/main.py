"""
Main entry point for the Value Investors Club API.
Creates the FastAPI application and includes all routes.
"""
import uvicorn
from fastapi import FastAPI
from starlette.requests import Request

from api.routes import (
    companies_router,
    health_router,
    holdings_router,
    investors_router,
    ideas_router,
    review_router,
    users_router,
)
from api.telemetry import configure_telemetry, span

configure_telemetry()

# Create FastAPI app
app = FastAPI(
    title="Value Investors Club API",
    description="Read-only API for accessing Value Investors Club data",
    version="1.0.0",
)


@app.middleware("http")
async def trace_api_request(request: Request, call_next):
    with span("api.request", {"http.method": request.method, "http.route": request.url.path}):
        return await call_next(request)

# Include all routers
app.include_router(health_router)
app.include_router(ideas_router)
app.include_router(companies_router)
app.include_router(users_router)
app.include_router(holdings_router)
app.include_router(review_router)
app.include_router(investors_router)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8010)
