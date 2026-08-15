"""ORB + ATR intraday strategy definition and signal logic."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class OrbAtrParams(BaseModel):
    opening_range_minutes: int = Field(default=15)
    atr_period: int = Field(default=14, ge=2)
    atr_filter_mult: float = Field(default=1.0, ge=0)
    stop_risk_mult: float = Field(default=1.0, gt=0)
    target_risk_mult: float = Field(default=2.0, gt=0)
    session_exit_time: str = Field(default="15:45")
    commission_per_side: float = Field(default=0.62, ge=0)
    slippage_ticks: int = Field(default=1, ge=0)
    max_entries_per_session: int = Field(default=1)

    @field_validator("opening_range_minutes")
    @classmethod
    def _orb_allowlist(cls, v: int) -> int:
        if v not in (15, 30):
            raise ValueError("opening_range_minutes must be 15 or 30")
        return v

    @field_validator("max_entries_per_session")
    @classmethod
    def _one_entry(cls, v: int) -> int:
        if v != 1:
            raise ValueError("MVP allows exactly 1 entry per session")
        return v


STRATEGY_ID = "orb_atr_intraday"
STRATEGY_VERSION = "0.1.0"


def allowed_parameters_schema() -> dict[str, Any]:
    return OrbAtrParams.model_json_schema()


def validate_parameters(raw: dict[str, Any]) -> OrbAtrParams:
    return OrbAtrParams.model_validate(raw)
