"""Reconcile latest IBKR vs NinjaTrader raw bars and write versioned reports.

Example:
  python -m connectors.reconcile_sources --instrument MES
  python -m connectors.reconcile_sources --instrument MNQ
  python -m connectors.reconcile_sources --all
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from tradelab.quality.reconcile import reconcile_frames  # noqa: E402
from tradelab.quality.validators import build_quality_report  # noqa: E402

TICK = {"MES": Decimal("0.25"), "MNQ": Decimal("0.25")}


def _latest_parquet(root: Path, instrument: str, prefer_final: bool = True) -> Path:
    pattern = f"*/{instrument}_5m*.parquet"
    candidates = list(root.glob(pattern))
    if prefer_final:
        finals = [p for p in candidates if p.name.endswith("_final.parquet")]
        if finals:
            candidates = finals
        else:
            candidates = [p for p in candidates if not p.name.endswith("_tmp.parquet")]
    if not candidates:
        raise FileNotFoundError(f"No parquet for {instrument} under {root}")
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _normalize_ts(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["timestamp_utc"] = pd.to_datetime(out["timestamp_utc"], utc=True)
    # floor to minute to avoid microsecond mismatch between sources
    out["timestamp_utc"] = out["timestamp_utc"].dt.floor("min")
    out = out.drop_duplicates(subset=["timestamp_utc"], keep="last")
    out = out.sort_values("timestamp_utc").reset_index(drop=True)
    return out


def reconcile_instrument(instrument: str, *, data_root: Path, reports_dir: Path) -> dict:
    instrument = instrument.upper()
    ibkr_path = _latest_parquet(data_root / "raw" / "ibkr", instrument, prefer_final=True)
    nt_path = _latest_parquet(data_root / "raw" / "ninjatrader", instrument, prefer_final=False)

    ibkr = _normalize_ts(pd.read_parquet(ibkr_path))
    nt = _normalize_ts(pd.read_parquet(nt_path))

    # Restrict comparison to IBKR coverage (typically RTH-only) for fair overlap
    start, end = ibkr["timestamp_utc"].min(), ibkr["timestamp_utc"].max()
    nt_window = nt[(nt["timestamp_utc"] >= start) & (nt["timestamp_utc"] <= end)].copy()

    result = reconcile_frames(
        nt_window,
        ibkr,
        tick_size=TICK[instrument],
        left_label="ninjatrader",
        right_label="ibkr",
    )

    merged = nt_window.merge(
        ibkr,
        on="timestamp_utc",
        suffixes=("_nt", "_ib"),
        how="inner",
    )
    if not merged.empty:
        dclose = (merged["close_nt"] - merged["close_ib"]).abs()
        price_stats = {
            "close_corr": float(merged["close_nt"].corr(merged["close_ib"])),
            "close_exact_match_rate": float((dclose <= 1e-9).mean()),
            "close_within_1_tick_rate": float((dclose <= float(TICK[instrument]) + 1e-9).mean()),
            "close_within_4_ticks_rate": float((dclose <= 4 * float(TICK[instrument]) + 1e-9).mean()),
            "close_abs_diff_median": float(dclose.median()),
            "close_abs_diff_p95": float(dclose.quantile(0.95)),
            "close_abs_diff_max": float(dclose.max()),
        }
    else:
        price_stats = {}

    # Sample first 20 quarantine rows for the report body
    q_sample = result["quarantine"][:20]
    price_disc_count = len(result["price_discrepancies"])
    common = result["common_coverage"]["timestamps"]
    conflict_ts = len({d["timestamp_utc"] for d in result["price_discrepancies"]})
    conflict_rate = (conflict_ts / common) if common else 0.0
    within_1 = price_stats.get("close_within_1_tick_rate", 0.0)

    quality_ibkr = build_quality_report(ibkr)
    quality_nt = build_quality_report(nt_window)

    # MVP policy: keep both raw; prefer IBKR RTH for canonical if overlap exists.
    # High vendor divergence is expected and must not be silently merged.
    if common == 0:
        preferred = "insufficient_overlap"
    elif within_1 >= 0.9:
        preferred = "either_ok_prefer_ibkr"
    else:
        preferred = "ibkr_canonical_nt_quarantine"

    report_id = str(uuid.uuid4())
    out_dir = reports_dir / "reconciliation"
    out_dir.mkdir(parents=True, exist_ok=True)
    stub = f"{instrument}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}_{report_id[:8]}"
    json_path = out_dir / f"{stub}.json"
    md_path = out_dir / f"{stub}.md"

    payload = {
        "reconciliation_id": report_id,
        "instrument": instrument,
        "tick_size": float(TICK[instrument]),
        "ibkr_path": str(ibkr_path),
        "ninjatrader_path": str(nt_path),
        "ibkr_rows": int(len(ibkr)),
        "ninjatrader_rows_in_ibkr_window": int(len(nt_window)),
        "ninjatrader_rows_total": int(len(nt)),
        "window_start_utc": str(start),
        "window_end_utc": str(end),
        "common_coverage": result["common_coverage"],
        "price_discrepancy_count": price_disc_count,
        "conflict_timestamps": conflict_ts,
        "conflict_rate": conflict_rate,
        "price_stats": price_stats,
        "volume_rel_diff": result["volume_rel_diff"],
        "quarantine_count": len(result["quarantine"]),
        "quarantine_sample": q_sample,
        "quality_ibkr": quality_ibkr,
        "quality_ninjatrader_window": quality_nt,
        "preferred_source_recommendation": preferred,
        "notes": [
            "Timestamps aligned in UTC after NT America/Chicago localization.",
            "OHLC vendor differences beyond 1 tick are quarantined (no silent merge).",
            "Volume relative differences are informative only.",
            "IBKR series was requested with useRTH=True; NT chart may include broader session bars outside overlap.",
        ],
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    json_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    md = f"""# Reconciliation report — {instrument}

- **id**: `{report_id}`
- **window (UTC)**: {start} → {end}
- **IBKR file**: `{ibkr_path}` ({len(ibkr)} bars)
- **NinjaTrader file**: `{nt_path}` ({len(nt)} total; {len(nt_window)} in IBKR window)

## Coverage

| Metric | Value |
|--------|-------|
| Common timestamps | {common} |
| NT only (in window) | {result["common_coverage"]["left_only"]} |
| IBKR only | {result["common_coverage"]["right_only"]} |
| OHLC discrepancies (>1 tick) | {price_disc_count} |
| Timestamps with price conflict | {conflict_ts} ({conflict_rate:.2%}) |
| Close correlation | {price_stats.get("close_corr")} |
| Close exact match rate | {price_stats.get("close_exact_match_rate")} |
| Close within 1 tick | {price_stats.get("close_within_1_tick_rate")} |
| Close within 4 ticks | {price_stats.get("close_within_4_ticks_rate")} |
| Close abs diff median / p95 / max | {price_stats.get("close_abs_diff_median")} / {price_stats.get("close_abs_diff_p95")} / {price_stats.get("close_abs_diff_max")} |
| Mean abs volume rel diff | {result["volume_rel_diff"].get("mean_abs_pct")} |
| Quarantine items | {len(result["quarantine"])} |

## Quality (no silent merge)

- IBKR quality_status: `{quality_ibkr.get("quality_status")}` gaps={quality_ibkr.get("gap_count")}
- NT (window) quality_status: `{quality_nt.get("quality_status")}` gaps={quality_nt.get("gap_count")}

## Recommendation

Preferred source for canonical MVP: **{preferred}**  
Keep both raw immutable batches. Quarantine conflicting timestamps; do not blend OHLC.

## Quarantine sample (first 20)

```json
{json.dumps(q_sample, indent=2)}
```
"""
    md_path.write_text(md, encoding="utf-8")
    payload["report_uri_json"] = str(json_path)
    payload["report_uri_md"] = str(md_path)
    try:
        from tradelab.rag.indexer import index_file

        index_file(md_path)
        index_file(json_path)
    except Exception:
        pass
    return payload


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--instrument", choices=["MES", "MNQ", "mes", "mnq"])
    p.add_argument("--all", action="store_true")
    p.add_argument("--data-root", type=Path, default=Path("data"))
    p.add_argument("--reports-dir", type=Path, default=Path("data_catalog/reports"))
    args = p.parse_args(argv)

    instruments = ["MES", "MNQ"] if args.all or not args.instrument else [args.instrument.upper()]
    summaries = []
    for inst in instruments:
        try:
            report = reconcile_instrument(inst, data_root=args.data_root, reports_dir=args.reports_dir)
            summaries.append(
                {
                    "instrument": inst,
                    "ok": True,
                    "common": report["common_coverage"]["timestamps"],
                    "conflicts": report["conflict_timestamps"],
                    "conflict_rate": report["conflict_rate"],
                    "within_1_tick": (report.get("price_stats") or {}).get("close_within_1_tick_rate"),
                    "close_corr": (report.get("price_stats") or {}).get("close_corr"),
                    "quarantine": report["quarantine_count"],
                    "vol_rel": report["volume_rel_diff"].get("mean_abs_pct"),
                    "preferred": report["preferred_source_recommendation"],
                    "report_md": report["report_uri_md"],
                }
            )
        except Exception as exc:  # noqa: BLE001
            summaries.append({"instrument": inst, "ok": False, "error": str(exc)})

    print(json.dumps({"ok": all(s.get("ok") for s in summaries), "results": summaries}, indent=2))
    return 0 if all(s.get("ok") for s in summaries) else 1


if __name__ == "__main__":
    # Allow `python -m connectors.reconcile_sources`
    raise SystemExit(main())
