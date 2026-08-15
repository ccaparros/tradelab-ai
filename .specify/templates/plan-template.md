# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]

**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

[Extract from feature spec: primary requirement + technical approach from research]

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: [e.g., Python 3.11, Swift 5.9, Rust 1.75 or NEEDS CLARIFICATION]

**Primary Dependencies**: [e.g., FastAPI, UIKit, LLVM or NEEDS CLARIFICATION]

**Storage**: [if applicable, e.g., PostgreSQL, CoreData, files or N/A]

**Testing**: [e.g., pytest, XCTest, cargo test or NEEDS CLARIFICATION]

**Target Platform**: [e.g., Linux server, iOS 15+, WASM or NEEDS CLARIFICATION]

**Project Type**: [e.g., library/cli/web-service/mobile-app/compiler/desktop-app or NEEDS CLARIFICATION]

**Performance Goals**: [domain-specific, e.g., 1000 req/s, 10k lines/sec, 60 fps or NEEDS CLARIFICATION]

**Constraints**: [domain-specific, e.g., <200ms p95, <100MB memory, offline-capable or NEEDS CLARIFICATION]

**Scale/Scope**: [domain-specific, e.g., 10k users, 1M LOC, 50 screens or NEEDS CLARIFICATION]

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*
*Source: `.specify/memory/constitution.md` (TradeLab AI v1.0.0+)*

- [ ] **I. Reproducibilidad**: ¿La feature genera o consume IDs/hashes
      versionados (`dataset_id` / `experiment_id` / `analysis_id`) y
      deja métricas trazables?
- [ ] **II. Linaje del dato**: ¿Raw inmutable + manifiesto/checksum?
      ¿Discrepancias a cuarentena (nunca merge silencioso)?
- [ ] **III. Honestidad temporal**: ¿Splits temporales, sin look-ahead,
      holdout protegido? ¿Tests anti-fuga cuando toque indicadores?
- [ ] **IV. IA acotada**: ¿Cifras solo vía tools/código? ¿Schema tipado
      + citas verificables? ¿Sin embeddings de series numéricas?
- [ ] **V. Sin trading real**: ¿Ninguna tool/endpoint de envío de
      órdenes? ¿Credenciales de broker solo en local?
- [ ] **Alcance**: ¿Cabe en MVP o está en la lista de recortes/opcionales?
      Si añade complejidad post-MVP, rellenar Complexity Tracking.
- [ ] **Evals/CI**: ¿Hay criterio de aceptación medible alineado con
      umbrales de constitución cuando la feature toque IA o quant?

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Keep or trim paths to those touched by this feature.
  Default layout follows TradeLab AI monorepo (constitution / plan).
-->

```text
apps/
├── api/                 # FastAPI
└── ui/                  # Streamlit
connectors/
├── ibkr/
└── ninjatrader-csharp/
src/tradelab/
├── ingestion/
├── quality/
├── datasets/
├── backtesting/
├── rag/
├── agents/
├── prompts/
└── observability/
migrations/
data_catalog/
evals/
├── golden/
└── regression/
tests/
docs/
├── architecture/
├── adr/
└── demo/
```

**Structure Decision**: [Document the selected structure and reference the real
directories captured above]

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
