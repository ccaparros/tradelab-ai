"""IBKR historical adapter skeleton — offline-friendly with recorded responses."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class PacingError(Exception):
    pass


class IBKRHistoricalClient:
    """Minimal interface for reqHistoricalData-style pulls.

    Live TWS wiring is intentionally out of band for demo mode. Use
    `fetch_from_recording` in tests/CI.
    """

    def __init__(self, *, host: str = "127.0.0.1", port: int = 7497, client_id: int = 1) -> None:
        self.host = host
        self.port = port
        self.client_id = client_id
        self._last_request_ts = 0.0

    def respect_pacing(self, min_interval_sec: float = 1.0) -> None:
        elapsed = time.time() - self._last_request_ts
        if elapsed < min_interval_sec:
            time.sleep(min_interval_sec - elapsed)
        self._last_request_ts = time.time()

    def fetch_from_recording(self, recording_path: Path) -> list[dict[str, Any]]:
        self.respect_pacing(0.0)
        data = json.loads(recording_path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError("recording must be a list of bars")
        return data

    def build_request_params(
        self,
        *,
        what_to_show: str = "TRADES",
        use_rth: bool = True,
        bar_size: str = "5 mins",
        timezone: str = "UTC",
    ) -> dict[str, Any]:
        return {
            "whatToShow": what_to_show,
            "useRTH": use_rth,
            "barSizeSetting": bar_size,
            "timezone": timezone,
            "host": self.host,
            "port": self.port,
        }
