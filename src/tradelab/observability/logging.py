"""Structured logging helpers with correlation fields."""

from __future__ import annotations

import logging
import sys
from typing import Any


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    if root.handlers:
        root.setLevel(level.upper())
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s correlation=%(correlation)s"
        )
    )
    root.addHandler(handler)
    root.setLevel(level.upper())


class CorrelationFilter(logging.Filter):
    def __init__(self, correlation: str = "-") -> None:
        super().__init__()
        self.correlation = correlation

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "correlation"):
            record.correlation = self.correlation  # type: ignore[attr-defined]
        return True


def get_logger(name: str, *, analysis_id: str | None = None, experiment_id: str | None = None) -> logging.Logger:
    logger = logging.getLogger(name)
    correlation = analysis_id or experiment_id or "-"
    # Avoid stacking duplicate filters
    if not any(isinstance(f, CorrelationFilter) for f in logger.filters):
        logger.addFilter(CorrelationFilter(correlation))
    return logger


def log_extra(**fields: Any) -> dict[str, Any]:
    return {"extra_fields": fields}
