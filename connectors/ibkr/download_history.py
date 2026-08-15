"""Download IBKR historical 5m bars for MES/MNQ into immutable raw + manifest.

Requires TWS or IB Gateway with API socket enabled (default paper port 7497).

Examples:
  python -m connectors.ibkr.download_history --symbol MES --days 5
  python -m connectors.ibkr.download_history --symbol MNQ --days 5 --port 7497
  python -m connectors.ibkr.download_history --symbol MES --days 30 --contract-month 202609
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from ib_insync import IB, ContFuture, Future, util

# Allow `python -m connectors.ibkr.download_history` from repo root
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from tradelab.ingestion.storage import write_immutable_parquet, write_manifest  # noqa: E402


def _resolve_contract(ib: IB, symbol: str, contract_month: str | None):
    symbol = symbol.upper()
    if contract_month:
        contract = Future(symbol, contract_month, "CME", currency="USD")
    else:
        # Continuous future for spike convenience; store resolved localSymbol in manifest
        contract = ContFuture(symbol, "CME", currency="USD")
    qualified = ib.qualifyContracts(contract)
    if not qualified:
        raise RuntimeError(f"Could not qualify contract for {symbol} month={contract_month}")
    return qualified[0]


def _bars_to_frame(bars, *, source: str, instrument: str, contract_month: str, exchange: str, run_id: str, checksum_placeholder: str) -> pd.DataFrame:
    rows = []
    for b in bars:
        ts = b.date
        if isinstance(ts, str):
            ts = pd.Timestamp(ts, tz="UTC")
        else:
            ts = pd.Timestamp(ts)
            if ts.tzinfo is None:
                ts = ts.tz_localize("UTC")
            else:
                ts = ts.tz_convert("UTC")
        rows.append(
            {
                "source": source,
                "instrument": instrument,
                "contract_month": contract_month,
                "exchange": exchange,
                "bar_size": "5 mins",
                "timestamp_utc": ts,
                "session_date": ts.strftime("%Y-%m-%d"),
                "open": float(b.open),
                "high": float(b.high),
                "low": float(b.low),
                "close": float(b.close),
                "volume": float(b.volume),
                "rth": True,
                "timezone_original": "UTC",
                "ingestion_run_id": run_id,
                "raw_checksum": checksum_placeholder,
            }
        )
    return pd.DataFrame(rows)


def download(
    *,
    symbol: str,
    days: int,
    host: str,
    port: int,
    client_id: int,
    contract_month: str | None,
    use_rth: bool,
    data_root: Path,
) -> dict:
    util.startLoop()
    ib = IB()
    ib.connect(host, port, clientId=client_id, readonly=True, timeout=15)
    try:
        contract = _resolve_contract(ib, symbol, contract_month)
        resolved_month = getattr(contract, "lastTradeDateOrContractMonth", None) or contract_month or "CONT"
        if len(str(resolved_month)) >= 6:
            resolved_month = str(resolved_month)[:6]

        duration = f"{days} D" if days <= 365 else f"{max(1, days // 365)} Y"
        # IB pacing: keep windows modest for spike
        bars = ib.reqHistoricalData(
            contract,
            endDateTime="",
            durationStr=duration,
            barSizeSetting="5 mins",
            whatToShow="TRADES",
            useRTH=use_rth,
            formatDate=2,
            keepUpToDate=False,
        )
        if not bars:
            raise RuntimeError(
                "IB returned 0 bars. Check market data permissions for CME micro futures "
                "and that the session is within available history."
            )

        run_id = str(uuid.uuid4())
        out_dir = data_root / "raw" / "ibkr" / run_id
        out_dir.mkdir(parents=True, exist_ok=True)
        parquet_path = out_dir / f"{symbol.upper()}_5m.parquet"
        manifest_path = out_dir / "manifest.json"

        df = _bars_to_frame(
            bars,
            source="ibkr",
            instrument=symbol.upper(),
            contract_month=str(resolved_month),
            exchange=getattr(contract, "exchange", "CME") or "CME",
            run_id=run_id,
            checksum_placeholder="pending",
        )
        checksum = write_immutable_parquet(df, parquet_path)
        df["raw_checksum"] = checksum
        # rewrite with checksum filled (new path to keep immutability of first write)
        final_parquet = out_dir / f"{symbol.upper()}_5m_final.parquet"
        checksum = write_immutable_parquet(df, final_parquet)

        request_params = {
            "whatToShow": "TRADES",
            "useRTH": use_rth,
            "barSizeSetting": "5 mins",
            "durationStr": duration,
            "formatDate": 2,
            "host": host,
            "port": port,
            "localSymbol": getattr(contract, "localSymbol", None),
            "conId": getattr(contract, "conId", None),
            "secType": getattr(contract, "secType", None),
        }
        manifest = {
            "source": "ibkr",
            "instrument": symbol.upper(),
            "contract_month": str(resolved_month),
            "bar_size": "5 mins",
            "timezone_original": "UTC",
            "row_count": int(len(df)),
            "ingestion_run_id": run_id,
            "parquet_uri": str(final_parquet),
            "checksum": checksum,
            "request_params": request_params,
            "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        write_manifest(manifest_path, manifest)
        return manifest
    finally:
        if ib.isConnected():
            ib.disconnect()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Download IBKR 5m history for TradeLab AI")
    p.add_argument("--symbol", default="MES", choices=["MES", "MNQ", "mes", "mnq"])
    p.add_argument("--days", type=int, default=5, help="History window for spike (default 5)")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=7497, help="7497 paper TWS, 7496 live TWS, 4002 paper GW")
    p.add_argument("--client-id", type=int, default=71)
    p.add_argument("--contract-month", default=None, help="YYYYMM explicit contract; default ContFuture")
    p.add_argument("--use-rth", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--data-root", type=Path, default=Path("data"))
    args = p.parse_args(argv)

    try:
        manifest = download(
            symbol=args.symbol,
            days=args.days,
            host=args.host,
            port=args.port,
            client_id=args.client_id,
            contract_month=args.contract_month,
            use_rth=args.use_rth,
            data_root=args.data_root,
        )
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 1

    print(json.dumps({"ok": True, **manifest}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
