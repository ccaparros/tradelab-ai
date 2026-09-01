"""Download IBKR historical 5m bars for MES/MNQ into immutable raw + manifest.

Requires TWS or IB Gateway with API socket enabled.
Paper TWS: 7497 · Live TWS: 7496 · Paper Gateway: 4002 · Live Gateway: 4001.

ContFuture cannot paginate (IB error 10339). This client walks quarterly
Future contracts (includeExpired) and stitches a nearest-expiry series.

Examples:
  python -m connectors.ibkr.download_history --symbol MES --days 5
  python -m connectors.ibkr.download_history --symbol MNQ --days 730 --port 7496
"""

from __future__ import annotations

import argparse
import json
import socket
import sys
import time
import uuid
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from ib_insync import IB

# Allow `python -m connectors.ibkr.download_history` from repo root
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from tradelab.ingestion.storage import write_immutable_parquet, write_manifest  # noqa: E402

DEFAULT_PORTS = (7497, 7496, 4002, 4001)
PACING_CODES = {162, 420}


def detect_tws_port(host: str, ports: tuple[int, ...] = DEFAULT_PORTS) -> int | None:
    for port in ports:
        sock = socket.socket()
        sock.settimeout(0.5)
        try:
            sock.connect((host, port))
            return port
        except OSError:
            continue
        finally:
            sock.close()
    return None


def stitch_nearest_expiry(df: pd.DataFrame) -> pd.DataFrame:
    """Keep the nearest-to-expiry contract when several print the same timestamp."""
    if df.empty:
        return df
    out = df.sort_values(["timestamp_utc", "contract_month"], kind="mergesort")
    return out.drop_duplicates(subset=["timestamp_utc"], keep="first").reset_index(drop=True)


def _bar_ts(bar) -> pd.Timestamp:
    ts = bar.date
    if isinstance(ts, str):
        ts = pd.Timestamp(ts, tz="UTC")
    else:
        ts = pd.Timestamp(ts)
        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        else:
            ts = ts.tz_convert("UTC")
    return ts


def _end_datetime_str(ts: pd.Timestamp) -> str:
    ts = pd.Timestamp(ts).tz_convert("UTC")
    return ts.strftime("%Y%m%d %H:%M:%S UTC")


def _parse_last_trade(value: str) -> date:
    return datetime.strptime(str(value)[:8], "%Y%m%d").date()


def _bars_to_frame(
    bars,
    *,
    source: str,
    instrument: str,
    contract_month: str,
    exchange: str,
    run_id: str,
    checksum_placeholder: str,
) -> pd.DataFrame:
    rows = []
    for b in bars:
        ts = _bar_ts(b)
        rows.append(
            {
                "source": source,
                "instrument": instrument,
                "contract_month": contract_month,
                "exchange": exchange,
                "bar_size": "5 mins",
                "timestamp_utc": ts,
                "session_date": ts.tz_convert("America/Chicago").strftime("%Y-%m-%d"),
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


def _fetch_chunk(
    ib: IB,
    contract,
    *,
    end_date_time: str,
    duration: str,
    use_rth: bool,
    errors: list[tuple[int, str]],
    pace_sec: float,
    retries: int = 4,
):
    last_exc: Exception | None = None
    for attempt in range(retries):
        wait = 0.0 if pace_sec <= 0 else (pace_sec if attempt == 0 else max(pace_sec, 60.0))
        if wait:
            time.sleep(wait)
        errors.clear()
        try:
            bars = ib.reqHistoricalData(
                contract,
                endDateTime=end_date_time,
                durationStr=duration,
                barSizeSetting="5 mins",
                whatToShow="TRADES",
                useRTH=use_rth,
                formatDate=2,
                keepUpToDate=False,
            )
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if "pacing" in str(exc).lower():
                print(f"pacing retry {attempt + 1}/{retries}: {exc}", file=sys.stderr)
                continue
            raise
        pacing = any(code in PACING_CODES and "pacing" in text.lower() for code, text in errors)
        if pacing:
            print(f"pacing violation, retry {attempt + 1}/{retries}", file=sys.stderr)
            last_exc = RuntimeError(errors[-1][1] if errors else "pacing violation")
            continue
        return bars
    raise last_exc or RuntimeError("historical request failed after retries")


def _history_contracts(ib: IB, symbol: str, contract_month: str | None, today: date):
    from ib_insync import Future

    if contract_month:
        spec = Future(
            symbol.upper(),
            contract_month,
            "CME",
            currency="USD",
            includeExpired=True,
        )
        qualified = ib.qualifyContracts(spec)
        if not qualified:
            raise RuntimeError(f"Could not qualify {symbol} month={contract_month}")
        return [qualified[0]]

    details = ib.reqContractDetails(
        Future(symbol.upper(), "", "CME", currency="USD", includeExpired=True)
    )
    front_cutoff = today + timedelta(days=45)
    seen: set[str] = set()
    contracts = []
    for item in sorted(details, key=lambda d: d.contract.lastTradeDateOrContractMonth):
        raw = item.contract
        ltd = _parse_last_trade(raw.lastTradeDateOrContractMonth)
        if ltd > front_cutoff:
            continue
        key = raw.lastTradeDateOrContractMonth[:8]
        if key in seen:
            continue
        seen.add(key)
        spec = Future(
            symbol.upper(),
            raw.lastTradeDateOrContractMonth,
            raw.exchange or "CME",
            currency="USD",
            includeExpired=True,
        )
        qualified = ib.qualifyContracts(spec)
        if qualified:
            contracts.append(qualified[0])
    if not contracts:
        raise RuntimeError(f"No quarterly futures available for {symbol}")
    return contracts


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
    chunk_days: int = 30,
    pace_sec: float = 11.0,
) -> dict:
    try:
        from ib_insync import IB, util
    except ImportError as exc:
        raise RuntimeError(
            'IBKR connector dependencies are missing; install with pip install -e ".[broker]"'
        ) from exc

    util.startLoop()
    ib = IB()
    errors: list[tuple[int, str]] = []

    def _on_error(_req_id, error_code, error_string, _contract):
        errors.append((int(error_code), str(error_string)))
        if int(error_code) not in {2104, 2106, 2107, 2158, 2119, 2103, 366}:
            print(f"IB error {error_code}: {error_string}", file=sys.stderr)

    ib.errorEvent += _on_error
    ib.RequestTimeout = 180
    ib.connect(host, port, clientId=client_id, readonly=True, timeout=20)
    try:
        today = date.today()
        contracts = _history_contracts(ib, symbol, contract_month, today)
        chunk_days = max(1, min(int(chunk_days), 60))
        now = pd.Timestamp.now(tz="UTC")
        target_start = now - pd.Timedelta(days=days)
        max_chunks = max(2, (days // chunk_days) + 4)
        frames: list[pd.DataFrame] = []
        chunk_meta: list[dict] = []
        first_request = True

        print(
            f"connected clientId={client_id} port={port} "
            f"contracts={[getattr(c, 'localSymbol', None) for c in contracts]} "
            f"target={days}D chunk={chunk_days}D",
            file=sys.stderr,
        )

        for contract in contracts:
            resolved_month = str(getattr(contract, "lastTradeDateOrContractMonth", "") or "")[:6]
            ltd = _parse_last_trade(contract.lastTradeDateOrContractMonth)
            if ltd >= today:
                end_date_time = ""
            else:
                end_date_time = f"{ltd:%Y%m%d} 23:59:59 UTC"
            print(
                f"contract {getattr(contract, 'localSymbol', resolved_month)} "
                f"expiry={contract.lastTradeDateOrContractMonth} start_end={end_date_time or 'now'}",
                file=sys.stderr,
            )
            for idx in range(max_chunks):
                bars = _fetch_chunk(
                    ib,
                    contract,
                    end_date_time=end_date_time,
                    duration=f"{chunk_days} D",
                    use_rth=use_rth,
                    errors=errors,
                    pace_sec=0.0 if first_request else pace_sec,
                )
                first_request = False
                if not bars:
                    print("  0 bars — next contract", file=sys.stderr)
                    break
                oldest = _bar_ts(bars[0])
                newest = _bar_ts(bars[-1])
                print(
                    f"  chunk {idx + 1}: {len(bars)} bars "
                    f"{oldest.isoformat()} → {newest.isoformat()}",
                    file=sys.stderr,
                )
                frames.append(
                    _bars_to_frame(
                        bars,
                        source="ibkr",
                        instrument=symbol.upper(),
                        contract_month=str(resolved_month),
                        exchange=getattr(contract, "exchange", "CME") or "CME",
                        run_id="pending",
                        checksum_placeholder="pending",
                    )
                )
                chunk_meta.append(
                    {
                        "localSymbol": getattr(contract, "localSymbol", None),
                        "conId": getattr(contract, "conId", None),
                        "endDateTime": end_date_time or "now",
                        "durationStr": f"{chunk_days} D",
                        "bar_count": len(bars),
                        "oldest_utc": oldest.isoformat(),
                        "newest_utc": newest.isoformat(),
                    }
                )
                if oldest <= target_start:
                    break
                end_date_time = _end_datetime_str(oldest - timedelta(minutes=5))

        if not frames:
            raise RuntimeError(
                "IB returned 0 bars. Check market data permissions for CME micro futures "
                "and that the session is within available history."
            )

        run_id = str(uuid.uuid4())
        out_dir = data_root / "raw" / "ibkr" / run_id
        out_dir.mkdir(parents=True, exist_ok=True)
        parquet_path = out_dir / f"{symbol.upper()}_5m.parquet"
        manifest_path = out_dir / "manifest.json"

        raw = pd.concat(frames, ignore_index=True)
        raw["timestamp_utc"] = pd.to_datetime(raw["timestamp_utc"], utc=True)
        raw["ingestion_run_id"] = run_id
        df = stitch_nearest_expiry(raw)
        checksum = write_immutable_parquet(df, parquet_path)
        df["raw_checksum"] = checksum
        final_parquet = out_dir / f"{symbol.upper()}_5m_final.parquet"
        checksum = write_immutable_parquet(df, final_parquet)

        span_days = int((df["timestamp_utc"].max() - df["timestamp_utc"].min()).days)
        request_params = {
            "whatToShow": "TRADES",
            "useRTH": use_rth,
            "barSizeSetting": "5 mins",
            "durationStr": f"{days} D quarterly walk x {chunk_days} D",
            "formatDate": 2,
            "host": host,
            "port": port,
            "chunk_days": chunk_days,
            "stitch": "nearest_expiry",
            "raw_row_count": int(len(raw)),
            "chunks": chunk_meta,
            "contracts": [
                {
                    "localSymbol": getattr(c, "localSymbol", None),
                    "conId": getattr(c, "conId", None),
                    "lastTradeDateOrContractMonth": getattr(
                        c, "lastTradeDateOrContractMonth", None
                    ),
                    "secType": getattr(c, "secType", None),
                }
                for c in contracts
            ],
            "readonly": True,
        }
        front_start = None
        if "contract_month" in df.columns and not df.empty:
            oldest_front = df.sort_values("timestamp_utc")["contract_month"].iloc[0]
            front_start = str(oldest_front)
        manifest = {
            "source": "ibkr",
            "instrument": symbol.upper(),
            "contract_month": str(df["contract_month"].iloc[-1]) if not df.empty else "CONT",
            "bar_size": "5 mins",
            "timezone_original": "UTC",
            "row_count": int(len(df)),
            "coverage_start_utc": df["timestamp_utc"].min().isoformat(),
            "coverage_end_utc": df["timestamp_utc"].max().isoformat(),
            "coverage_calendar_days": span_days,
            "oldest_contract_month": front_start,
            "ingestion_run_id": run_id,
            "parquet_uri": str(final_parquet),
            "checksum": checksum,
            "request_params": request_params,
            "downloaded_at_utc": datetime.now(UTC).isoformat(),
        }
        write_manifest(manifest_path, manifest)
        return manifest
    finally:
        if ib.isConnected():
            ib.disconnect()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Download IBKR 5m history for TradeLab AI")
    p.add_argument("--symbol", default="MES", choices=["MES", "MNQ", "mes", "mnq"])
    p.add_argument("--days", type=int, default=5, help="Target calendar window (paginated)")
    p.add_argument("--chunk-days", type=int, default=30, help="IB request window (keep ≤60 for 5m)")
    p.add_argument("--pace-sec", type=float, default=11.0, help="Seconds between historical chunks")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=0, help="0 = auto-detect 7497/7496/4002/4001")
    p.add_argument("--client-id", type=int, default=71)
    p.add_argument(
        "--contract-month",
        default=None,
        help="YYYYMM or YYYYMMDD single contract; default = all IB-available quarters",
    )
    p.add_argument("--use-rth", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--data-root", type=Path, default=Path("data"))
    args = p.parse_args(argv)

    port = args.port
    if port <= 0:
        detected = detect_tws_port(args.host)
        if not detected:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "error": (
                            "No TWS/Gateway socket on 7497/7496/4002/4001. "
                            "Enable API in TWS and accept the incoming connection popup."
                        ),
                    },
                    indent=2,
                )
            )
            return 1
        port = detected
        print(f"auto-detected TWS port {port}", file=sys.stderr)

    try:
        manifest = download(
            symbol=args.symbol,
            days=args.days,
            host=args.host,
            port=port,
            client_id=args.client_id,
            contract_month=args.contract_month,
            use_rth=args.use_rth,
            data_root=args.data_root,
            chunk_days=args.chunk_days,
            pace_sec=args.pace_sec,
        )
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 1

    print(json.dumps({"ok": True, **manifest}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
