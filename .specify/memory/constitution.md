<!--
Sync Impact Report
- Version change: (none/template) → 1.0.0
- Modified principles: placeholders →
  I. Reproducibilidad y Auditoría
  II. Integridad y Linaje del Dato
  III. Honestidad Temporal (Anti Look-Ahead)
  IV. IA Acotada: Cálculo Fuera del LLM
  V. Solo Investigación — Sin Trading Real
- Added sections: Alcance y Recortes Permitidos; Flujo de Desarrollo y Gates
- Removed sections: none (first ratification from template)
- Templates requiring updates:
  - .specify/templates/plan-template.md ✅ updated (Constitution Check + structure)
  - .specify/templates/spec-template.md ✅ updated (constraints + success alignment)
  - .specify/templates/tasks-template.md ✅ updated (paths + mandatory test categories)
  - .cursor/skills/speckit-*/SKILL.md ✅ no outdated agent-specific refs requiring change
- Follow-up TODOs: none deferred
-->

# TradeLab AI Constitution

## Core Principles

### I. Reproducibilidad y Auditoría
Toda ejecución de ingesta, validación, backtest o análisis MUST
ser reproducible a partir de identificadores versionados
(`dataset_id`, `experiment_id`, `analysis_id`). Cada experimento MUST
registrar hash del dataset, código, parámetros y prompt cuando aplique.
Ninguna métrica financiera MAY aparecer en UI, API o respuesta del
agente sin trazabilidad al experimento o tool que la generó.
**Rationale**: La calidad del producto se mide por evidencia y
reproducibilidad, no por rentabilidad de la estrategia.

### II. Integridad y Linaje del Dato
Los ficheros raw MUST ser inmutables (Parquet + manifiesto + checksum).
La normalización MUST producir datasets canónicos versionados con
linaje completo (fuente, request, timezone, sesión, versión de
normalizador, fecha de ingesta). Las discrepancias entre NinjaTrader e
IBKR MUST ir a cuarentena con informe versionable; NUNCA se mezclarán
silenciosamente barras contradictorias. El contrato canónico de barra
MUST cumplirse antes de alimentar backtests o el corpus RAG.
**Rationale**: Sin dato fiable y trazable, el resto del sistema es
teatro cuantitativo.

### III. Honestidad Temporal (Anti Look-Ahead)
Los splits MUST ser temporales (train / validation / holdout), nunca
aleatorios. Todos los indicadores MUST desplazarse para impedir
look-ahead. Los parámetros se eligen en train, se deciden en validation
y el holdout MUST leerse una sola vez al final. Walk-forward y
sensibilidad a costes son obligatorios en experimentos que afirmen
robustez. Cualquier test que detecte uso de barra futura MUST fallar
en CI.
**Rationale**: Un backtest engañoso invalida la demostración académica
y el valor del producto.

### IV. IA Acotada: Cálculo Fuera del LLM
Las barras, trades y métricas MUST consultarse con SQL/Python
determinista; los embeddings se reservan para documentos, políticas e
informes. El LLM MUST NOT calcular Sharpe, drawdown, P&L u otras
métricas financieras: las recibe como resultados estructurados de
tools tipadas. Toda respuesta del agente MUST incluir schema Pydantic
(`answer`, `metrics`, `assumptions`, `warnings`, `sources`,
`confidence`) y pasar verificación de cifras/citas. Ante evidencia
insuficiente, el sistema MUST aclarar o declinar inventar.
**Rationale**: CAG/RAG y el agente aportan interpretación y
navegación; la verdad numérica vive en código probado.

### V. Solo Investigación — Sin Trading Real
TradeLab AI es una plataforma de investigación cuantitativa y análisis
de riesgo. MUST NOT existir tool, endpoint o flujo que envíe órdenes
reales. La demo pública MUST consumir snapshot aprobado o resultados
derivados; los conectores de broker se ejecutan en local y las
credenciales MUST NOT desplegarse en cloud. Predicción de precios por
LLM y trading con dinero real están explícitamente fuera de alcance.
**Rationale**: El enunciado y el riesgo regulatorio/ético exigen un
límite duro entre investigación y ejecución.

## Alcance y Recortes Permitidos

El MVP obligatorio cubre MES/MNQ (o el instrumento común validado en
spike), barras de 5 minutos, reconciliación dual-fuente, una estrategia
determinista ORB+ATR, backtest con costes, copiloto con tools tipadas,
FastAPI, Streamlit, tests/evals, Docker Compose y CI básica.

Orden de sacrificio si el calendario se complica (en este orden):

1. eliminar segundo instrumento;
2. export NinjaTrader reproducible en vez de Add-On completo;
3. eliminar agente crítico (mantener un solo agente);
4. eliminar Redis, SSE y optimizaciones avanzadas;
5. vídeo + Docker local en vez de conectividad cloud a brokers.

NUNCA se recortan: calidad y linaje de datos, backtest determinista,
RAG real, una capa de agente, evals, README y demo comprobable.

## Flujo de Desarrollo y Gates

El desarrollo sigue gates semanales del plan de proyecto. Antes de
avanzar de fase MUST cumplirse el gate correspondiente (muestras
reales, reconciliación end-to-end, experimento hasheado, Recall@5,
happy path UI, matriz de evals).

Criterios de aceptación no negociables para IA (baseline ajustable una
sola vez con registro):

- tool selection accuracy >= 90%;
- schema validity = 100%;
- retrieval Recall@5 >= 85%;
- citation precision >= 95%;
- cero IDs de fuente inexistentes;
- cero cifras financieras no presentes en tool o fuente;
- faithfulness >= 0.90;
- al menos una regresión automatizada por fallo importante.

CI MUST ejecutar lint, unit tests, integration tests sin broker y
evals rápidas. Secrets excluidos del repo; `.env.example` obligatorio.

## Governance

Esta constitución prevalece sobre preferencias ad hoc, prompts y
atajos de implementación. Toda feature, plan y PR MUST pasar el
Constitution Check de `.specify/templates/plan-template.md`.

Enmiendas:

1. Documentar el cambio, el motivo y el impacto en templates/evals.
2. Incrementar versión semántica:
   - MAJOR: eliminación o redefinición incompatible de principios;
   - MINOR: nuevo principio/sección o ampliación material;
   - PATCH: aclaraciones y refinamientos no semánticos.
3. Actualizar `LAST_AMENDED_DATE` y el Sync Impact Report.
4. Propagar cambios a plantillas Spec Kit afectadas.

Revisión de cumplimiento: en cada `/speckit-plan` y antes de
`/speckit-implement`; en CI mediante tests anti-look-ahead,
determinismo y evals de citas/cifras. Complejidad adicional
(multiagente, paper trading, segunda estrategia) solo tras MVP medido
y justificación explícita en Complexity Tracking del plan.

**Version**: 1.0.0 | **Ratified**: 2026-07-22 | **Last Amended**: 2026-07-22
