# Feature Specification: TradeLab AI MVP

**Feature Branch**: `001-tradelab-mvp`

**Created**: 2026-07-22

**Status**: Draft

**Input**: User description: "Plataforma auditable de investigación cuantitativa y análisis de riesgo para futuros micro de índices (MES/MNQ): ingesta dual de histórico, validación/reconciliación, backtest determinista ORB+ATR, y copiloto de investigación que explica resultados con evidencias citables — sin trading real ni predicción de precios por IA. Basado en PLAN_PROYECTO_TRADING_AI.md y constitución TradeLab AI v1.0.0."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Confiar en el histórico de dos fuentes (Priority: P1)

Un investigador sistemático necesita cargar histórico de barras de 5 minutos para contratos explícitos de MES y/o MNQ procedentes de dos proveedores de mercado, comprobar si los datos son coherentes entre sí y obtener un informe de calidad antes de usarlos en ningún experimento.

**Why this priority**: Sin dato fiable y comparable no hay investigación válida; es el prerrequisito de todo el resto del producto.

**Independent Test**: Con muestras históricas preparadas de ambas fuentes (o una sola si el spike de permisos lo impone), el investigador puede completar la carga, ver cobertura/gaps/discrepancias y decidir si el dataset es usable — sin ejecutar backtests ni hablar con el copiloto.

**Acceptance Scenarios**:

1. **Given** histórico permitido de una fuente para un instrumento y periodo, **When** el investigador registra la carga, **Then** obtiene un dataset versionado con linaje (origen, periodo, contrato, checksum) y un informe de calidad (duplicados, gaps clasificados, violaciones de OHLC).
2. **Given** el mismo instrumento/periodo disponible en ambas fuentes, **When** solicita reconciliación, **Then** ve cobertura común, discrepancias por campo dentro de tolerancia de tick y periodos problemáticos enviados a cuarentena — sin mezclar barras contradictorias en silencio.
3. **Given** un gap o inconsistencia, **When** revisa el informe, **Then** cada incidencia está clasificada (sesión cerrada, mantenimiento, dato no disponible o error) y es recuperable más tarde como evidencia.

---

### User Story 2 - Ejecutar un experimento reproducible (Priority: P2)

El investigador selecciona un dataset canónico aprobado y lanza la estrategia intradía Opening Range Breakout con filtro de volatilidad (ATR), stop, objetivo, salida horaria y como máximo una entrada por sesión, con comisión y slippage explícitos, para obtener métricas, operaciones e informe del experimento.

**Why this priority**: El núcleo de valor cuantitativo del MVP; demuestra método científico (splits temporales, costes, determinismo) sin depender de rentabilidad.

**Independent Test**: A partir de un `dataset` ya validado (fixture o catálogo), el investigador reproduce un experimento completo y obtiene el mismo resultado e identificador de integridad al repetir la misma entrada.

**Acceptance Scenarios**:

1. **Given** un dataset canónico y parámetros permitidos de la estrategia, **When** lanza el backtest, **Then** recibe trades, curva de equity, drawdown, métricas netas (con costes) e identificadores de experimento y hash de integridad.
2. **Given** el mismo dataset, mismos parámetros y misma versión del método, **When** vuelve a ejecutar, **Then** obtiene el mismo resultado y el mismo hash.
3. **Given** el flujo de investigación, **When** elige parámetros, **Then** solo puede hacerlo sobre el periodo de entrenamiento; el holdout permanece bloqueado hasta la lectura final única prevista.
4. **Given** un experimento completado, **When** revisa el informe, **Then** ve al menos un baseline simple y/o sensibilidad a costes o parámetros cercanos documentada, además del resultado agregado.

---

### User Story 3 - Explicación auditada sin cifras inventadas (Priority: P3)

El investigador pregunta en lenguaje natural por qué un resultado de validación difiere del de entrenamiento, qué dice el informe de calidad o qué evidencias respaldan una métrica, y recibe una respuesta estructurada con supuestos, avisos, fuentes citables y nivel de confianza — sin poder enviar órdenes reales.

**Why this priority**: Diferencia el producto de un backtester mudo y cumple el requisito de IA aplicada con evidencia; depende de datos y experimentos previos pero aporta el flujo demo principal.

**Independent Test**: Con un corpus de informes de calidad/experimentos ya indexados y al menos un experimento persistido, el investigador formula 5–10 preguntas del conjunto de evaluación y obtiene respuestas con citas navegables y cero cifras no respaldadas.

**Acceptance Scenarios**:

1. **Given** un experimento existente, **When** pregunta por métricas o trades, **Then** la respuesta solo incluye cifras que existen en resultados recuperados del sistema y cita la fuente.
2. **Given** una pregunta ambigua o sin evidencia suficiente, **When** el copiloto no puede respaldar la afirmación, **Then** pide aclaración o declara evidencia insuficiente en lugar de inventar.
3. **Given** cualquier interacción del copiloto, **When** se inspecciona el registro de análisis, **Then** queda un identificador de análisis que enlaza pregunta, herramientas usadas, fuentes y respuesta.
4. **Given** el alcance del producto, **When** el usuario intenta o el sistema ofrece acciones de trading, **Then** no existe ninguna acción de envío de órdenes reales.

---

### User Story 4 - Recorrido de investigación de extremo a extremo (Priority: P4)

Un evaluador o el propio investigador completa el happy path de producto: catálogo → calidad → backtest → explicación citada → comprobación de que la demo funciona sin credenciales de broker en el entorno de evaluación.

**Why this priority**: Cierra la entrega académica y la demo de 2–3 minutos; integra las historias anteriores en un recorrido demostrable.

**Independent Test**: Siguiendo solo la guía de uso (sin conocimiento interno), un tercero ejecuta el recorrido feliz con el snapshot preparado y obtiene pantallas/resultados comprensibles en menos de 15 minutos.

**Acceptance Scenarios**:

1. **Given** el entorno de demo con snapshot aprobado, **When** el evaluador abre el espacio de trabajo, **Then** ve catálogo de datasets, informe de reconciliación (o de una fuente), lanzamiento de backtest y respuesta citada del copiloto.
2. **Given** un error de datos insuficientes, timeout o fuente no disponible, **When** ocurre en el recorrido, **Then** el sistema muestra un estado comprensible y no deja resultados parciales presentados como definitivos.
3. **Given** la entrega final, **When** se presenta la demo, **Then** existe vídeo de 2–3 minutos y/o URL pública que cubre el guion: calidad → backtest → evidencia → ausencia de trading real.

---

### Edge Cases

- Una de las dos fuentes no tiene permisos o histórico común para MES/MNQ: el sistema permite continuar con un solo instrumento/fuente validada y deja constancia en el informe de alcance.
- Barras con OHLC inválido o tick desalinea: se rechazan o se cuarentenan; no entran al dataset canónico usado en backtest.
- Periodo solicitado parcialmente disponible: se reporta cobertura real y se bloquea afirmar un histórico completo.
- Reejecución con parámetros fuera de la lista permitida: se rechaza antes de calcular.
- Pregunta del copiloto que pide predicción de precios futuros: se rechaza o se redirige a evidencia histórica disponible.
- Snapshot de demo sin acceso a brokers: el happy path sigue siendo usable con datos preparados.
- Discrepancia de volumen entre fuentes (normal entre proveedores): se informa como diferencia relativa, no como fallo automático de todo el dataset.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST permitir registrar histórico de barras de 5 minutos para contratos explícitos de futuros micro de índices (MES y MNQ, o el instrumento común validado tras el spike de permisos).
- **FR-002**: El sistema MUST aceptar histórico procedente de dos proveedores de mercado distintos y conservar ambos originales de forma inmutable con manifiesto de procedencia e integridad.
- **FR-003**: El sistema MUST validar el contrato canónico de barra (precios positivos, OHLC coherente, timestamps ordenados en UTC, sesión, tick) antes de publicar un dataset canónico.
- **FR-004**: El sistema MUST clasificar el 100% de los gaps detectados o reportarlos explícitamente; no MAY dejar gaps sin categoría.
- **FR-005**: El sistema MUST reconciliar timestamps comunes entre fuentes, comparar precios frente a tolerancia de tick, producir informe de cobertura/discrepancias y enviar conflictos a cuarentena sin fusión silenciosa.
- **FR-006**: El sistema MUST exponer un catálogo de datasets versionados con linaje consultable (origen, periodo, instrumento, contrato, calidad).
- **FR-007**: El sistema MUST ejecutar una única familia de estrategia intradía Opening Range Breakout con filtro ATR, stop, objetivo, salida obligatoria antes del cierre y máximo una entrada por sesión.
- **FR-008**: El sistema MUST aplicar comisión, slippage y tamaño de tick/multiplicador configurables en todas las métricas netas presentadas.
- **FR-009**: El sistema MUST separar periodos en entrenamiento, validación y holdout de forma temporal (nunca aleatoria) y proteger el holdout de uso durante la selección de parámetros.
- **FR-010**: El sistema MUST garantizar determinismo: misma entrada + misma versión de método = mismo resultado e mismo hash de integridad.
- **FR-011**: El sistema MUST impedir look-ahead en indicadores (solo datos estrictamente anteriores al momento de decisión) y fallar las pruebas de aceptación si se detecta uso de barra futura.
- **FR-012**: El sistema MUST persistir experimentos con trades, métricas, informe y enlaces al dataset y parámetros usados.
- **FR-013**: El sistema MUST ofrecer un copiloto de investigación que consulte calidad de datos, lance backtests con parámetros permitidos y explique resultados usando solo evidencias recuperadas.
- **FR-014**: El copiloto MUST devolver respuestas estructuradas con respuesta, métricas, supuestos, avisos, fuentes y confianza, y MUST verificar que cada cifra y cita existe en evidencias recuperadas.
- **FR-015**: El sistema MUST NOT ofrecer ni ejecutar envío de órdenes reales en ningún flujo.
- **FR-016**: El sistema MUST permitir el recorrido feliz de evaluación sin credenciales de broker, usando un snapshot o resultados derivados aprobados.
- **FR-017**: El sistema MUST registrar trazas de análisis (herramientas usadas, coste estimado cuando aplique, errores) correlacionadas con un identificador de análisis.
- **FR-018**: El sistema MUST mantener un corpus documental de investigación (política, especificación de estrategia, informes de calidad/experimentos, decisiones) recuperable con citas hasta el documento original.
- **FR-019**: El sistema MUST publicar una matriz de evaluación del copiloto (selección de herramientas, validez de esquema, recuperación, precisión de citas, fidelidad y regresiones) con umbrales documentados.
- **FR-020**: Usuarios MUST poder completar el flujo catálogo → calidad → backtest → explicación citada desde el espacio de trabajo de producto sin escribir código.

### Key Entities

- **Instrumento/Contrato**: Identifica el futuro micro, vencimiento, exchange y reglas de tick/sesión aplicables.
- **Carga de origen (raw)**: Lote inmutable de barras de un proveedor, con manifiesto e integridad.
- **Dataset canónico**: Serie normalizada versionada apta para investigación, con linaje y estado de calidad.
- **Informe de calidad/reconciliación**: Evidencia de cobertura, gaps, discrepancias y cuarentena.
- **Estrategia parametrizada**: Definición ORB+ATR y parámetros permitidos (rango de apertura, múltiplos de riesgo, horarios).
- **Experimento**: Ejecución reproducible de backtest ligada a dataset, parámetros, hash, trades y métricas.
- **Documento de investigación**: Unidad del corpus (informe, política, especificación) citable por el copiloto.
- **Análisis asistido**: Conversación/consulta con evidencias, herramientas invocadas y respuesta estructurada.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un investigador completa la carga y revisión de calidad de un periodo de muestra en menos de 20 minutos y obtiene un informe accionable (usable / cuarentena / insuficiente).
- **SC-002**: Ante el mismo dataset y parámetros, 100% de reejecuciones del experimento producen el mismo hash de integridad y las mismas métricas netas.
- **SC-003**: El 100% de gaps en datasets canónicos publicados están clasificados o reportados; cero duplicados en el dataset canónico.
- **SC-004**: Ninguna métrica financiera mostrada al usuario carece de enlace al experimento o evidencia que la originó (auditoría manual de 20 métricas al azar = 0 huérfanas).
- **SC-005**: En el conjunto de evaluación del copiloto (30–40 preguntas), precisión de selección de herramientas ≥ 90%, validez de esquema = 100%, Recall@5 de recuperación ≥ 85%, precisión de citas ≥ 95%, fidelidad ≥ 0,90, y cero cifras o IDs de fuente inventados.
- **SC-006**: Un evaluador externo completa el happy path de demo sin credenciales de broker en menos de 15 minutos siguiendo solo la guía de uso.
- **SC-007**: El 100% de intentos de acción de trading real están bloqueados o son inexistentes en la interfaz y en las capacidades del copiloto (verificación de aceptación = cero rutas de orden).
- **SC-008**: La demo entregable (vídeo de 2–3 minutos y/o entorno público) cubre calidad, backtest, evidencia citada y declaración explícita de no ejecución real.

## Assumptions

- El usuario primario es un único investigador/evaluador; no se requiere multiusuario empresarial ni roles complejos en el MVP.
- El spike de permisos confirmará disponibilidad real; si no hay histórico común para ambos instrumentos/fuentes, se reduce alcance a un instrumento (y/o una fuente + snapshot) sin invalidar el MVP.
- El rango de apertura por defecto es de 15 minutos, configurable dentro de parámetros permitidos (15 o 30).
- El histórico objetivo mínimo demostrable es de 12 meses cuando los permisos lo permitan; periodos menores son aceptables si quedan documentados tras el spike.
- Comisión, slippage y tick se configuran con valores explícitos documentados; no se ocultan costes.
- La rentabilidad de la estrategia no es criterio de éxito del producto ni de la entrega académica.
- La demo pública usa solo datos/resultados cuya redistribución esté permitida o sea sintética/derivada aprobada.
- Autenticación avanzada, app móvil, alta frecuencia y multiagente crítico quedan fuera del MVP.

## Constitution Constraints *(mandatory for TradeLab AI)*

- **No live trading**: Feature MUST NOT send real orders or expose order tools.
- **Numeric truth outside LLM**: Financial figures MUST come from typed tools or
  deterministic code; LLM synthesizes with citations only.
- **Temporal integrity**: Any backtest/indicator work MUST forbid look-ahead and
  protect holdout.
- **Data lineage**: Ingestion/mutation of market data MUST preserve raw
  immutability, checksums, and quarantine for conflicts.
- **Out of MVP** (unless explicitly approved): multi-agent critique, paper
  trading, second strategy family, HFT/order-book, cloud broker credentials.

## Success Criteria Notes

Los umbrales de SC-005 alinean con la constitución TradeLab AI v1.0.0. Pueden
ajustarse una sola vez tras el baseline inicial dejando registro de la decisión
en el diario de investigación / ADR.
