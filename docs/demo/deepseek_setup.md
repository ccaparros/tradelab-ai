# DeepSeek LLM setup

TradeLab usa la API **OpenAI-compatible** de DeepSeek para sintetizar respuestas.
Las cifras financieras siguen saliendo solo de tools tipadas + verificador.

## 1. Crear clave

1. Entra en https://platform.deepseek.com/
2. Crea un API key

## 2. Configurar `.env` (nunca lo subas a git)

```env
LLM_API_KEY=sk-...tu_clave...
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
```

Modelo alternativo: `deepseek-reasoner` (más lento/caro).

## 3. Probar

```powershell
cd C:\ProyectosCurso\Master_Lidr\ProyectoFinCurso
python -c "from tradelab.agents.graph import run_analysis; import json; print(json.dumps(run_analysis(query='Resume el riesgo de overfit train vs validation', dataset_id='c9ad9532-b06c-4501-9b09-d73281b4c030', experiment_id='12a5ebc4-c596-4e4f-ac29-433a7dc03a16'), indent=2, default=str)[:1500])"
```

En la respuesta, `llm.provider` debe ser `openai_compatible` si la clave es válida.

## 4. Reiniciar API

Si uvicorn ya estaba corriendo, reinícialo para cargar el `.env`.
