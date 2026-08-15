"""TradeLab AI FastAPI entrypoint — research only, no order placement."""

from __future__ import annotations

from fastapi import FastAPI

from apps.api.routers import analysis, catalog, experiments
from tradelab.observability.logging import configure_logging
from tradelab.observability.settings import get_settings

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(
    title="TradeLab AI API",
    version="0.1.0",
    description="Auditable quantitative research API. No live trading endpoints.",
)

app.include_router(catalog.router)
app.include_router(experiments.router)
app.include_router(analysis.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": "0.1.0"}
