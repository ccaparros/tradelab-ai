# Conectores de mercado — cómo bajar datos

## IBKR (automático) ✅

Instala primero la dependencia opcional del conector:

```powershell
pip install -e ".[broker]"
```

El script detecta el socket: **7497** (paper TWS), **7496** (live TWS), **4002/4001** (Gateway).
La descarga es **solo lectura** (`readonly=True`); no envía órdenes.

`ContFuture` no permite paginar (`endDateTime`). El cliente pide cada vencimiento
trimestral (`includeExpired`) y cose una serie nearest-expiry.

### Ajustes en TWS (una vez)

1. **File → Global Configuration → API → Settings**
2. Marca **Enable ActiveX and Socket Clients**
3. Socket port: **7497** (paper) o **7496** (live)
4. Añade `127.0.0.1` a Trusted IPs si lo pide
5. Acepta el popup “Accept incoming connection” al primer script

### Comandos

```powershell
cd C:\ProyectosCurso\Master_Lidr\ProyectoFinCurso
python -m connectors.ibkr.download_history --symbol MES --days 5
python -m connectors.ibkr.download_history --symbol MNQ --days 5 --client-id 72
```

Histórico largo (12–24 meses, paginado; depende de los contratos que IBKR aún sirva):

```powershell
python -m connectors.ibkr.download_history --symbol MES --days 730 --client-id 101
python -m connectors.ibkr.download_history --symbol MNQ --days 730 --client-id 102
python -m connectors.publish_canonical --all
```

Salida: `data/raw/ibkr/<run_id>/` (Parquet + `manifest.json`).

---

## NinjaTrader 8 (semi-automático)

NT no expone una API Python estable como TWS; el camino MVP es un
**indicador NinjaScript** que exporta CSV y un importador Python.

### 1. Instalar el indicador

El archivo `TradeLabExportBars.cs` debe estar en:

`Documents\NinjaTrader 8\bin\Custom\Indicators\TradeLabExportBars.cs`

(si el script de setup pudo, ya se copió solo).

### 2. Compilar en NinjaTrader

1. Abre **New → NinjaScript Editor**
2. Pulsa **Compile** (F5) — sin errores
3. Abre un gráfico **MES** o **MNQ**, timeframe **5 minutos**, contrato explícito
4. Click derecho → **Indicators** → añade **TradeLabExportBars**
5. `ExportOnLoad = true`, `MaxBars = 5000` (o más)
6. Acepta — en el log de NT verás `TradeLabExportBars wrote ...`

CSV en:

`Documents\TradeLabAI\ninjatrader_exports\`

### 3. Importar a TradeLab

```powershell
python connectors\ninjatrader-csharp\import_csv.py --latest --instrument MES --contract-month 202609
python connectors\ninjatrader-csharp\import_csv.py --latest --instrument MNQ --contract-month 202609
```

Salida: `data/raw/ninjatrader/<run_id>/`.

### Alternativa sin indicador

Exporta manualmente desde NT (click derecho en gráfico → Export) a CSV con
columnas `timestamp_exchange,open,high,low,close,volume` y pásalo con `--csv`.

---

## Registrar en el catálogo (API)

Con la API levantada:

```powershell
# ejemplo IBKR
python -c "import json,httpx,pathlib; m=json.loads(pathlib.Path(r'data/raw/ibkr/<run_id>/manifest.json').read_text()); print(httpx.post('http://localhost:8000/v1/ingestions', json={'source':'ibkr','instrument':m['instrument'],'contract_month':m['contract_month'],'parquet_uri':m['parquet_uri'],'manifest_uri':str(pathlib.Path(r'data/raw/ibkr/<run_id>/manifest.json').resolve()),'checksum':m['checksum'],'publish':True}).json())"
```

O usa la UI Catálogo tras un pequeño script de registro (siguiente paso).
