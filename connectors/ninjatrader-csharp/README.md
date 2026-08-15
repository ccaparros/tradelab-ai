# NinjaTrader connector (fallback-first)

## Preferred path

C# Add-On using `BarsRequest` that writes:

- immutable Parquet (or CSV converted by Python ingest)
- JSON manifest with instrument, contract_month, bar_size, session template,
  timezone, row_count, request params

## MVP fallback (allowed by constitution sacrifice #2)

1. Export bars from NinjaTrader UI for MES/MNQ 5-minute explicit contract.
2. Place files under `data/raw/ninjatrader/<run_id>/`.
3. Create `manifest.json`:

```json
{
  "source": "ninjatrader",
  "instrument": "MES",
  "contract_month": "202609",
  "bar_size": "5 mins",
  "timezone_original": "America/Chicago",
  "row_count": 0,
  "request_params": {
    "session_template": "CME US Index Futures RTH"
  }
}
```

4. Register via API `POST /v1/ingestions` — same contract as IBKR batches.

The Python pipeline MUST NOT special-case NT vs IBKR after registration:
both become `RawBarBatch` with checksum + lineage.
