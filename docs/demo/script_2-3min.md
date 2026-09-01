# Guía para grabar el vídeo (2–3 minutos)

Entregable de la propuesta: **vídeo de 2–3 minutos** que cubra
**calidad → backtest → evidencia citada → no hay trading real**.

Guion hablado listo para leer. Ensayo una vez **antes** de grabar (el backtest
largo puede tardar).

| | |
|--|--|
| Duración | 2:00–2:50 (corte duro a 3:00) |
| Resolución | 1920×1080, ventana del navegador a pantalla casi completa |
| Audio | micrófono claro; silencia notificaciones |
| Rama | `finalproject-TLAI` |
| Dataset | MES **real** (`stitch:202512-202609`, cobertura 2024-11 → 2026-08). **Nunca el DEMO.** |
| LLM | deja `LLM_API_KEY` vacío: síntesis determinista, sin VPN ni esperas |

---

## 0. Antes de pulsar grabar (5–10 min)

1. Arranca API + UI (local, como en [`README_evaluador.md`](README_evaluador.md)).
2. Abre **http://127.0.0.1:8501** — sidebar: Catálogo / Backtest / Análisis.
3. Cierra terminales, `.env`, TWS y cualquier pestaña con claves.
4. Zoom del navegador **110–125 %** para que se lean métricas.
5. **Ensayo de backtest:** Catálogo → elige MES real → Backtest →
   `Opening Range Breakout + ATR` → **no** marques holdout → Ejecutar.
   Anota cuántos segundos tarda. Si pasa de ~20 s, en el vídeo narrarás
   sobre el spinner o harás un corte (“el motor ya calculó…”).
6. Deja ese experimento hecho: en Análisis ya existirá al grabar.

Grabar en Windows: **Win + G** (Xbox Game Bar) → Captura, o Clipchamp / OBS.
Un solo archivo MP4. No hace falta edición sofisticada: un corte si el
backtest se alarga.

---

## 1. Guion por bloques (lo que dices / lo que pulsas)

### 0:00–0:18 — Apertura (pantalla: Catálogo)

**Dices:**

> Soy Casildo Caparrós. TradeLab AI es una plataforma académica de
> investigación cuantitativa sobre futuros micro del S&P 500 y del Nasdaq.
> Solo investigación: no envía órdenes reales. El flujo es dato trazable,
> backtest reproducible e IA acotada a evidencia.

### 0:18–0:50 — Catálogo y calidad

**Pulsas:** sidebar **Catálogo** → selector **Dataset** → MES real
(`MES stitch:202512-202609 · real · usable · ibkr · 2024-11-05 → 2026-08-28`).

Señala con el ratón: estado `usable`, duplicados 0, gaps clasificados,
expander **Linaje**.

**Dices:**

> El catálogo muestra datasets canónicos versionados. Este Micro S&P 500 es
> histórico de Interactive Brokers de unos 22 meses en barras de 5 minutos,
> sesión regular. Los huecos están clasificados como cierre de sesión, no
> como fallos de ingesta. La fuente preferida es Interactive Brokers;
> NinjaTrader queda como evidencia de reconciliación, sin mezclar en
> silencio apertura, máximo, mínimo y cierre. Checksum y linaje van con
> el dataset.

No digas: “serie continua de Interactive Brokers” ni “frente líquido desde
2024”. Si te preguntan luego: el stitch es nearest-expiry de vencimientos
explícitos Z5–U6.

### 0:50–1:40 — Backtest

**Pulsas:** **Backtest** → mismo MES real → estrategia
**Opening Range Breakout + ATR** → deja parámetros por defecto →
checkbox holdout **desmarcado** → **Ejecutar backtest**.

Cuando salga el resultado, señala: hash, train / validation,
holdout **bloqueado**, tabla walk-forward, baseline, sensibilidad.

**Dices:**

> Lanzamos la estrategia de ruptura del rango de apertura, con stops
> según el rango verdadero medio, costes incluidos. Splits temporales:
> train, validation y holdout. El holdout está bloqueado: no se usa para
> elegir parámetros. El hash de integridad mezcla dataset, código y
> parámetros: el mismo experimento es reproducible. Abajo, walk-forward
> expanding solo sobre train y validation, un baseline ingenuo y
> sensibilidad a comisión y slippage. La rentabilidad no es el criterio
> de éxito del proyecto; sí lo es que el recuento sea auditable.

Si el spinner se alarga: “El motor es determinista; en CPU local este
histórico tarda unos segundos.” No improvises cifras antes de que salgan.

### 1:40–2:25 — Copiloto (evidencia + citas)

**Pulsas:** **Análisis** → Dataset = MES real → Experimento = el que acabas
de crear (holdout bloqueado) → deja la pregunta por defecto:

`¿Por qué el resultado de validation es distinto de train y qué evidencia lo demuestra?`

→ **Analizar**.

Señala: respuesta, pestaña **Métricas (tools)**, **Fuentes citadas**,
**Tools invocadas**.

**Dices:**

> El copiloto no calcula PnL: llama a tools. La pregunta es por qué
> validation puede diferir de train. Las cifras salen de las tools; las
> fuentes tienen document_id. Si no hay evidencia, el sistema responde
> insuficiente; no inventa IDs.

Si DeepSeek no está: da igual. El fallback determinista es el camino de
evaluación y queda mejor en vídeo (rápido y estable).

### 2:25–2:50 — Cierre: no hay trading real

**Opcional (10 s) si vas sobrado:** cambia la pregunta a
`¿A qué precio cerrará el Micro S&P 500 mañana?` → Analizar → debe salir **Rechazado**.

**Dices (obligatorio, aunque no hagas la pregunta extra):**

> TradeLab AI no predice precios futuros y no envía, modifica ni cancela
> órdenes. La demo corre en local, sin broker. Repositorio en la rama
> finalproject-TLAI. Gracias.

Pantalla final: 1 s en el rechazo o en el sidebar. Stop.

---

## 2. Frases que no debes usar

- “El RAG usa embeddings / pgvector en cada consulta.”
  (El demo es BM25+TF-IDF; pgvector está preparado, no es el runtime.)
- “La estrategia gana dinero / está lista para live.”
- “Hay 24 meses de frente líquido.”
- “Faithfulness la juzga el LLM.”
- Mostrar o leer API keys, cuentas IBKR, `.env`.

---

## 3. Plan B si algo falla en caliente

| Problema | Qué haces en cámara |
|----------|---------------------|
| No aparece MES real | Elige el otro MES usable que no diga DEMO; di “dataset canónico IBKR”. |
| Backtest > 30 s | Corta el vídeo y retoma ya con el resultado. |
| Copiloto lento / error LLM | “Sin API key el copiloto sintetiza en modo determinista.” Reintenta. |
| Holdout se te marcó | Desmárcalo y vuelve a ejecutar; di “holdout solo lectura final”. |
| UI en inglés/labels raras | Sigue; nombra Catálogo, Backtest, Análisis. |

No grabes TWS ni NinjaTrader: el evaluador no los necesita y restan tiempo.

---

## 4. Después de grabar

1. Revisa que se oiga bien y que se lean hash, holdout bloqueado y una cita.
2. Sube el MP4 (Drive, YouTube no listado, o el canal que pida el máster).
3. Deja el enlace en el README de entrega o en la ficha del campus.
4. Opcional: tag `v1.0-final-TLAI` cuando el vídeo esté publicado.

Checklist de contenido (el evaluador debe ver las cuatro):

- [ ] Calidad / catálogo con dataset real
- [ ] Backtest con holdout bloqueado y hash
- [ ] Copiloto con tools y citas
- [ ] Frase explícita: no hay ejecución real de órdenes
