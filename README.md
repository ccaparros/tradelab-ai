# TradeLab AI

Plataforma auditable de investigación cuantitativa y análisis de riesgo para
futuros micro de índices (**MES/MNQ**). Investigación únicamente: **no envía
órdenes reales**.

## Requisitos

- Python 3.11+
- Docker + Docker Compose (API, UI, PostgreSQL + pgvector)

## Instalación rápida (local)

```bash
python -m venv .venv
# Windows: .\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env
```

## Docker Compose

```bash
docker compose up -d --build
curl http://localhost:8000/health
```

- API: http://localhost:8000  
- UI: http://localhost:8501  
- Docs OpenAPI: http://localhost:8000/docs  

## Validación

Sigue el quickstart de la feature:

- [`specs/001-tradelab-mvp/quickstart.md`](specs/001-tradelab-mvp/quickstart.md)

Indexar informes para el copiloto (RAG):

```bash
tradelab-index-rag
```

Detalle: [`docs/demo/rag_setup.md`](docs/demo/rag_setup.md)

## Spec Kit

Constitución, spec, plan y tareas viven en `.specify/` y `specs/001-tradelab-mvp/`.

Contraste propuesta vs implementación (qué se pidió y qué hay):

- [`docs/demo/README_evaluador.md`](docs/demo/README_evaluador.md) — recorrido único sin broker
- [`docs/demo/cobertura_requisitos.md`](docs/demo/cobertura_requisitos.md)

## Aviso legal / alcance

TradeLab AI es un proyecto académico de investigación. No es un bot de trading
con dinero real. Las credenciales de broker solo se usan en conectores locales;
la demo usa un snapshot aprobado.
