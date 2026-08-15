# Golden evaluations

Suite: `evals/golden/questions.jsonl` (38 cases).

Runner: `evals/golden/test_golden_eval.py` (marker `fast`).

## Thresholds (constitution)

| Metric | Minimum |
|--------|---------|
| Schema validity | 100% |
| Tool selection | ≥ 90% |
| Status accuracy | ≥ 90% |
| Citation precision (rows with `expect_citation`) | ≥ 95% |

## Run

```bash
pytest evals -q -m fast
```

Uses an isolated `DATA_ROOT`, fixture MES bars, one ORB experiment, and forces
`LLM_API_KEY=""` so CI stays deterministic (tools + verifier + stub synthesis).
