"""Import NinjaTrader CSV exports into TradeLab raw Parquet + manifest.

Default input folder:
  %USERPROFILE%\\Documents\\TradeLabAI\\ninjatrader_exports

Examples:
  python connectors/ninjatrader-csharp/import_csv.py --latest --instrument MES --contract-month 202609
  python connectors/ninjatrader-csharp/import_csv.py --csv path/to/file.csv --instrument MNQ --contract-month 202609
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from tradelab.ingestion.storage import write_immutable_parquet, write_manifest  # noqa: E402

DEFAULT_EXPORT_DIR = Path.home() / "Documents" / "TradeLabAI" / "ninjatrader_exports"


def import_csv(
    csv_path: Path,
    *,
    instrument: str,
    contract_month: str,
    exchange: str = "CME",
    timezone_original: str = "America/Chicago",
    data_root: Path = Path("data"),
) -> dict:
    raw = pd.read_csv(csv_path)
    raw.columns = [c.strip().lower() for c in raw.columns]
    required = {"timestamp_exchange", "open", "high", "low", "close", "volume"}
    if not required.issubset(set(raw.columns)):
        raise ValueError(f"CSV missing columns {required - set(raw.columns)}")

    ts = pd.to_datetime(raw["timestamp_exchange"])
    if getattr(ts.dt, "tz", None) is None:
        ts = ts.dt.tz_localize(timezone_original, ambiguous="infer", nonexistent="shift_forward")
    session_date = ts.dt.tz_convert("America/Chicago").dt.strftime("%Y-%m-%d")
    ts = ts.dt.tz_convert("UTC")

    run_id = str(uuid.uuid4())
    out_dir = data_root / "raw" / "ninjatrader" / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    parquet_path = out_dir / f"{instrument.upper()}_5m.parquet"
    manifest_path = out_dir / "manifest.json"

    df = pd.DataFrame(
        {
            "source": "ninjatrader",
            "instrument": instrument.upper(),
            "contract_month": contract_month,
            "exchange": exchange,
            "bar_size": "5 mins",
            "timestamp_utc": ts,
            "session_date": session_date,
            "open": raw["open"].astype(float),
            "high": raw["high"].astype(float),
            "low": raw["low"].astype(float),
            "close": raw["close"].astype(float),
            "volume": raw["volume"].astype(float),
            "rth": True,
            "timezone_original": timezone_original,
            "ingestion_run_id": run_id,
            "raw_checksum": "pending",
        }
    )
    checksum = write_immutable_parquet(df, parquet_path)

    # patch checksum column in a sidecar note (file itself is immutable)
    manifest = {
        "source": "ninjatrader",
        "instrument": instrument.upper(),
        "contract_month": contract_month,
        "bar_size": "5 mins",
        "timezone_original": timezone_original,
        "row_count": int(len(df)),
        "ingestion_run_id": run_id,
        "parquet_uri": str(parquet_path),
        "checksum": checksum,
        "request_params": {
            "csv_path": str(csv_path),
            "session_template": "CME US Index Futures RTH",
            "importer": "connectors/ninjatrader-csharp/import_csv.py",
        },
        "downloaded_at_utc": datetime.now(UTC).isoformat(),
    }
    write_manifest(manifest_path, manifest)
    return manifest


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Import NinjaTrader CSV into TradeLab raw store")
    p.add_argument("--csv", type=Path, help="Path to a single CSV export")
    p.add_argument("--watch-dir", type=Path, default=DEFAULT_EXPORT_DIR)
    p.add_argument("--instrument", default="MES")
    p.add_argument("--contract-month", default=None, help="YYYYMM (default: current UTC month)")
    p.add_argument("--timezone-original", default="America/Chicago")
    p.add_argument("--data-root", type=Path, default=Path("data"))
    p.add_argument("--latest", action="store_true", help="Import newest CSV in watch-dir")
    args = p.parse_args(argv)

    csv_path = args.csv
    if args.latest or csv_path is None:
        folder = args.watch_dir
        files = sorted(folder.glob("*.csv"), key=lambda x: x.stat().st_mtime, reverse=True)
        if not files:
            print(json.dumps({"ok": False, "error": f"No CSV found in {folder}"}))
            return 1
        csv_path = files[0]

    contract_month = args.contract_month or datetime.now(UTC).strftime("%Y%m")
    try:
        manifest = import_csv(
            csv_path,
            instrument=args.instrument,
            contract_month=contract_month,
            timezone_original=args.timezone_original,
            data_root=args.data_root,
        )
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 1

    print(json.dumps({"ok": True, **manifest}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
