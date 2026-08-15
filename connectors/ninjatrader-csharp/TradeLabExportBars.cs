#region Using declarations
using System;
using System.IO;
using System.Text;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
#endregion

// TradeLab AI — export 5-minute bars to CSV for Python ingest.
// IMPORTANT: on the chart set "Days to load" >= 60 (or more) BEFORE adding the indicator.
// 1) Copy/overwrite:
//    Documents\NinjaTrader 8\bin\Custom\Indicators\TradeLabExportBars.cs
// 2) NinjaScript Editor → Compile (F5)
// 3) MES/MNQ chart, 5-minute, Days to load = 60+
// 4) Add indicator TradeLabExportBars (ExportOnLoad=true, MaxBars=20000)
namespace NinjaTrader.NinjaScript.Indicators
{
	public class TradeLabExportBars : Indicator
	{
		private bool exported;

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description = "TradeLab AI CSV bar exporter (research-only)";
				Name = "TradeLabExportBars";
				Calculate = Calculate.OnBarClose;
				IsOverlay = true;
				DisplayInDataBox = false;
				DrawOnPricePanel = false;
				ExportOnLoad = true;
				MaxBars = 20000;
				OutputFolder = Path.Combine(
					Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),
					"TradeLabAI", "ninjatrader_exports");
			}
			else if (State == State.DataLoaded)
			{
				exported = false;
			}
			else if (State == State.Realtime && ExportOnLoad && !exported)
			{
				// Historical load finished — export full series once.
				TryExport();
			}
		}

		protected override void OnBarUpdate()
		{
			// Fallback if Realtime transition already passed on reload
			if (!ExportOnLoad || exported)
				return;
			if (State == State.Historical && CurrentBar >= Bars.Count - 2 && CurrentBar > 50)
				TryExport();
		}

		private void TryExport()
		{
			if (exported)
				return;
			try
			{
				Directory.CreateDirectory(OutputFolder);
				string instrument = Instrument.MasterInstrument.Name;
				string stamp = DateTime.UtcNow.ToString("yyyyMMddTHHmmss");
				string path = Path.Combine(OutputFolder, instrument + "_5m_" + stamp + ".csv");

				var sb = new StringBuilder();
				sb.AppendLine("timestamp_exchange,open,high,low,close,volume");

				int count = Math.Min(MaxBars, CurrentBar + 1);
				for (int barsAgo = count - 1; barsAgo >= 0; barsAgo--)
				{
					sb.Append(Time[barsAgo].ToString("yyyy-MM-dd HH:mm:ss"));
					sb.Append(',');
					sb.Append(Open[barsAgo].ToString(System.Globalization.CultureInfo.InvariantCulture));
					sb.Append(',');
					sb.Append(High[barsAgo].ToString(System.Globalization.CultureInfo.InvariantCulture));
					sb.Append(',');
					sb.Append(Low[barsAgo].ToString(System.Globalization.CultureInfo.InvariantCulture));
					sb.Append(',');
					sb.Append(Close[barsAgo].ToString(System.Globalization.CultureInfo.InvariantCulture));
					sb.Append(',');
					sb.Append(Volume[barsAgo].ToString(System.Globalization.CultureInfo.InvariantCulture));
					sb.AppendLine();
				}

				File.WriteAllText(path, sb.ToString(), Encoding.UTF8);
				exported = true;
				Print("TradeLabExportBars wrote " + path + " bars=" + count);
			}
			catch (Exception ex)
			{
				Print("TradeLabExportBars error: " + ex.Message);
			}
		}

		#region Properties
		[NinjaScriptProperty]
		public bool ExportOnLoad { get; set; }

		[NinjaScriptProperty]
		public int MaxBars { get; set; }

		[NinjaScriptProperty]
		public string OutputFolder { get; set; }
		#endregion
	}
}
