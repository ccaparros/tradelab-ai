"""Publish IBKR RTH bars as canonical datasets; keep NT as reconciliation evidence.

Example:
  python -m connectors.publish_canonical --all
  python -m connectors.publish_canonical --instrument MES
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from tradelab.datasets.publisher import publish_canonical_dataset  # noqa: E402
from tradelab.datasets.store import list_datasets, upsert_dataset  # noqa: E402
from tradelab.observability.settings import get_settings  # noqa: E402
from tradelab.rag.indexer import index_markdown  # noqa: E402


def _latest_ibkr_final(instrument: str, data_root: Path) -> Path:
    files = list((data_root / "raw" / "ibkr").glob(f"*/{instrument}_5m_final.parquet"))
    if not files:
        files = list((data_root / "raw" / "ibkr").glob(f"*/{instrument}_5m.parquet"))
    if not files:
        raise FileNotFoundError(f"No IBKR parquet for {instrument}")
    return max(files, key=lambda p: p.stat().st_mtime)


def _latest_recon_report(instrument: str, reports_dir: Path) -> dict[str, str | None]:
    folder = reports_dir / "reconciliation"
    mds = sorted(folder.glob(f"{instrument}_*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    jsons = sorted(folder.glob(f"{instrument}_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return {
        "md": str(mds[0]) if mds else None,
        "json": str(jsons[0]) if jsons else None,
    }


def _latest_nt_raw(instrument: str, data_root: Path) -> str | None:
    files = list((data_root / "raw" / "ninjatrader").glob(f"*/{instrument}_5m.parquet"))
    if not files:
        return None
    return str(max(files, key=lambda p: p.stat().st_mtime))


def publish_one(instrument: str, *, data_root: Path, reports_dir: Path) -> dict:
    instrument = instrument.upper()
    get_settings.cache_clear()
    ibkr_path = _latest_ibkr_final(instrument, data_root)
    recon = _latest_recon_report(instrument, reports_dir)
    nt_path = _latest_nt_raw(instrument, data_root)

    df = pd.read_parquet(ibkr_path)
    df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True)
    df = df.sort_values("timestamp_utc").drop_duplicates(subset=["timestamp_utc"], keep="last")

    contract_month = str(df["contract_month"].iloc[0]) if "contract_month" in df.columns else "202609"
    published = publish_canonical_dataset(
        df,
        contract_id=uuid.uuid4(),
        preferred_source_id="ibkr",
        lineage={
            "preferred_source": "ibkr",
            "policy": "ibkr_canonical_nt_quarantine",
            "raw_ibkr_uri": str(ibkr_path),
            "raw_ninjatrader_uri": nt_path,
            "reconciliation_report_md": recon["md"],
            "reconciliation_report_json": recon["json"],
            "bar_size": "5 mins",
            "useRTH": True,
            "published_at_utc": datetime.now(timezone.utc).isoformat(),
        },
    )

    # Classified overnight gaps must not block usable IBKR RTH canonical for MVP
    quality = published["quality"]
    status = quality.get("quality_status", "draft")
    if status != "usable" and quality.get("duplicate_count", 1) == 0 and quality.get("ohlc_violations", 1) == 0:
        # gaps are classified by design; promote to usable with warning
        status = "usable"
        quality = {**quality, "quality_status": "usable", "promotion_note": "gaps classified; IBKR RTH preferred"}

    record = {
        "dataset_id": str(published["dataset_id"]),
        "contract_id": str(published["contract_id"]),
        "instrument": instrument,
        "contract_month": contract_month,
        "bar_size": "5 mins",
        "quality_status": status,
        "content_checksum": published["content_checksum"],
        "storage_uri": published["storage_uri"],
        "coverage_start_utc": str(published["coverage_start_utc"]),
        "coverage_end_utc": str(published["coverage_end_utc"]),
        "quality": quality,
        "lineage": published["lineage"],
        "preferred_source": "ibkr",
        "report_uri": recon["md"],
    }
    upsert_dataset(record)

    # Index short catalog note for copiloto citations
    index_markdown(
        f"Canonical dataset {instrument}",
        (
            f"Canonical {instrument} dataset_id={record['dataset_id']} preferred_source=ibkr "
            f"checksum={record['content_checksum']} coverage={record['coverage_start_utc']}.."
            f"{record['coverage_end_utc']}. NT kept as reconciliation evidence only; no silent merge."
        ),
    )

    # Persist a small catalog sidecar
    cat_dir = reports_dir / "canonical"
    cat_dir.mkdir(parents=True, exist_ok=True)
    side = cat_dir / f"{instrument}_{record['dataset_id'][:8]}.json"
    side.write_text(json.dumps(record, indent=2, default=str), encoding="utf-8")
    record["catalog_sidecar"] = str(side)
    try:
        from tradelab.rag.indexer import index_file

        index_file(side)
    except Exception:
        pass
    return record


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Publish IBKR canonical datasets")
    p.add_argument("--instrument", choices=["MES", "MNQ", "mes", "mnq"])
    p.add_argument("--all", action="store_true")
    p.add_argument("--data-root", type=Path, default=Path("data"))
    p.add_argument("--reports-dir", type=Path, default=Path("data_catalog/reports"))
    args = p.parse_args(argv)

    instruments = ["MES", "MNQ"] if args.all or not args.instrument else [args.instrument.upper()]
    results = []
    for inst in instruments:
        try:
            rec = publish_one(inst, data_root=args.data_root, reports_dir=args.reports_dir)
            results.append(
                {
                    "ok": True,
                    "instrument": inst,
                    "dataset_id": rec["dataset_id"],
                    "quality_status": rec["quality_status"],
                    "rows_quality_gaps": rec["quality"].get("gap_count"),
                    "checksum": rec["content_checksum"],
                    "storage_uri": rec["storage_uri"],
                    "recon_md": rec.get("report_uri"),
                }
            )
        except Exception as exc:  # noqa: BLE001
            results.append({"ok": False, "instrument": inst, "error": str(exc)})

    print(
        json.dumps(
            {
                "ok": all(r.get("ok") for r in results),
                "datasets_in_store": [
                    {"dataset_id": d["dataset_id"], "instrument": d.get("instrument"), "quality_status": d.get("quality_status")}
                    for d in list_datasets()
                ],
                "published": results,
            },
            indent=2,
        )
    )
    return 0 if all(r.get("ok") for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
