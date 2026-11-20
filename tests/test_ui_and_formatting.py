from pathlib import Path
import sys
import unittest

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from climaps.core.analysis import (
    calculate_climate_anomaly,
    calculate_dew_point,
    calculate_heat_index,
    classify_air_quality,
    classify_uv,
    evaluate_storm_risk,
)
from climaps.core.data_loader import load_station_csv
from climaps.core.weather_api import _parse_point_payload
from climaps.ui_styles import format_datetime_friendly


class FormattingAndUiTests(unittest.TestCase):
    def test_format_datetime_friendly(self):
        # Test standard ISO string
        self.assertEqual(format_datetime_friendly("2026-11-19T16:00"), "19/11/2026 às 16:00")
        self.assertEqual(format_datetime_friendly("2026-11-19T16:00:00"), "19/11/2026 às 16:00")
        self.assertEqual(format_datetime_friendly("2026-11-19 16:00"), "19/11/2026 às 16:00")

        # Test Timestamp object
        ts = pd.Timestamp("2026-11-19 16:00")
        self.assertEqual(format_datetime_friendly(ts), "19/11/2026 às 16:00")

        # Test idempotence
        self.assertEqual(format_datetime_friendly("19/11/2026 às 16:00"), "19/11/2026 às 16:00")

        # Test null / empty
        self.assertEqual(format_datetime_friendly(None), "-")
        self.assertEqual(format_datetime_friendly(""), "-")
        self.assertEqual(format_datetime_friendly(pd.NaT), "-")

    def test_dew_point_calculation(self):
        # Hot and humid (e.g. Manaus 32 °C, 75% RH)
        dew = calculate_dew_point(32.0, 75.0)
        self.assertIsNotNone(dew)
        self.assertAlmostEqual(dew, 27.0, places=0)

        # Moderate (25 °C, 50% RH)
        dew_mod = calculate_dew_point(25.0, 50.0)
        self.assertAlmostEqual(dew_mod, 13.8, places=0)

        # None / Missing
        self.assertIsNone(calculate_dew_point(None, 75.0))
        self.assertIsNone(calculate_dew_point(30.0, None))

    def test_heat_index_calculation(self):
        # High heat index (32 °C, 75% RH)
        hi, desc, level = calculate_heat_index(32.0, 75.0)
        self.assertIsNotNone(hi)
        self.assertGreater(hi, 40.0)
        self.assertIn("Perigo", desc)

        # Mild temperature (< 27 °C)
        hi_mild, desc_mild, level_mild = calculate_heat_index(22.0, 60.0)
        self.assertLess(hi_mild, 27.0)
        self.assertIn("Normal", desc_mild)

        # Missing input
        hi_none, desc_none, _ = calculate_heat_index(None, 50.0)
        self.assertIsNone(hi_none)

    def test_storm_risk_evaluation(self):
        # High storm risk: Low pressure < 1005 + high humidity + strong gusts
        risk_high = evaluate_storm_risk(pressao_hpa=1001.0, umidade_pct=88.0, vento_kmh=25.0, rajadas_kmh=45.0, precipitacao_mm=2.5)
        self.assertEqual(risk_high["nivel"], "Alto Risco de Tempestade")
        self.assertEqual(risk_high["icone"], "⚡")

        # Moderate instability
        risk_med = evaluate_storm_risk(pressao_hpa=1007.0, umidade_pct=72.0, vento_kmh=15.0, rajadas_kmh=20.0)
        self.assertEqual(risk_med["nivel"], "Alerta de Instabilidade")

        # Stable atmosphere (normal pressure)
        risk_low = evaluate_storm_risk(pressao_hpa=1016.0, umidade_pct=55.0, vento_kmh=10.0, rajadas_kmh=15.0)
        self.assertEqual(risk_low["nivel"], "Atmosfera Estável")
        self.assertEqual(risk_low["icone"], "🟢")

    def test_air_quality_and_uv_classification(self):
        # Good air quality
        aqi_good = classify_air_quality(us_aqi=35, pm2_5=8.5)
        self.assertEqual(aqi_good["status"], "Boa")

        # Sensitive air quality (e.g. burning season smoke)
        aqi_sens = classify_air_quality(us_aqi=125, pm2_5=45.0)
        self.assertIn("Sensíveis", aqi_sens["status"])

        # Unhealthy
        aqi_bad = classify_air_quality(us_aqi=175, pm2_5=90.0)
        self.assertEqual(aqi_bad["status"], "Não Saudável")

        # UV classification
        uv_low = classify_uv(2.0)
        self.assertEqual(uv_low["status"], "Baixo")
        uv_very_high = classify_uv(9.5)
        self.assertEqual(uv_very_high["status"], "Muito Alto")

    def test_climate_anomaly_calculation(self):
        dataset = load_station_csv(ROOT / "data" / "dados_A101_H_2014.csv")
        df = dataset.data

        current_weather = {
            "local": "Manaus (BR)",
            "horario_raw": "2026-11-20T14:00",
            "temperatura_c": 31.8,
            "precipitacao_mm": 5.2,
        }

        anomaly = calculate_climate_anomaly(df, current_weather)
        self.assertIsNotNone(anomaly)
        self.assertTrue(anomaly["has_history"])
        self.assertEqual(anomaly["mes_nome"], "Novembro")
        self.assertGreater(anomaly["delta_temp"], 2.0)
        self.assertIn("acima da média histórica", anomaly["summary_text"])

    def test_parse_point_payload_with_forecast_and_indices(self):
        payload = {
            "latitude": -3.1,
            "longitude": -60.0,
            "timezone": "America/Manaus",
            "current": {
                "time": "2026-11-19T16:00",
                "temperature_2m": 32.5,
                "apparent_temperature": 38.0,
                "relative_humidity_2m": 75,
                "is_day": 1,
                "precipitation": 0.0,
                "weather_code": 0,
                "cloud_cover": 20,
                "pressure_msl": 1003.0,
                "wind_speed_10m": 15.0,
                "wind_gusts_10m": 35.0,
            },
            "daily": {
                "uv_index_max": [8.5],
                "sunrise": ["2026-11-19T05:45"],
                "sunset": ["2026-11-19T18:05"],
                "time": ["2026-11-19", "2026-11-20"],
                "temperature_2m_max": [33.0, 32.5],
                "temperature_2m_min": [24.0, 24.5],
                "precipitation_probability_max": [40, 60],
                "precipitation_sum": [0.5, 3.2],
                "weather_code": [0, 80],
            },
            "hourly": {
                "time": ["2026-11-19T16:00", "2026-11-19T17:00"],
                "temperature_2m": [32.5, 31.0],
                "precipitation_probability": [20, 45],
                "precipitation": [0.0, 1.2],
                "weather_code": [0, 80],
            },
        }
        res = _parse_point_payload(payload, "Manaus (BR)", -3.1, -60.0)
        self.assertEqual(res["horario"], "19/11/2026 às 16:00")
        self.assertEqual(res["local"], "Manaus (BR)")
        self.assertEqual(res["temperatura_c"], 32.5)

        # Derived indices
        self.assertIsNotNone(res["ponto_orvalho_c"])
        self.assertIsNotNone(res["indice_calor_c"])
        self.assertIn("risco_tempestade", res)

        # Forecast arrays
        self.assertEqual(len(res["forecast_hourly"]), 2)
        self.assertEqual(len(res["forecast_daily"]), 2)
        self.assertEqual(res["forecast_hourly"][0]["hora_label"], "16:00")
        self.assertEqual(res["forecast_daily"][0]["temp_max_c"], 33.0)

    def test_load_exported_climaps_csv(self):
        import tempfile
        from climaps.core.data_loader import load_station_csv

        # Simula DataFrame como exportado pelo ClimaPS
        dates = pd.date_range("2026-10-01", periods=48, freq="h")
        mock_df = pd.DataFrame(
            {
                "data": dates.floor("D"),
                "hora": dates.hour * 100,
                "precipitacao_mm": [0.0 if i % 2 == 0 else 2.5 for i in range(len(dates))],
                "temp_max_c": [28.0 + (i % 5) * 0.5 for i in range(len(dates))],
                "temp_min_c": [23.0 + (i % 3) * 0.4 for i in range(len(dates))],
                "data_hora": dates,
                "hora_num": dates.hour,
                "mes": dates.month,
                "dia": dates.floor("D"),
            }
        )

        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False, encoding="utf-8-sig") as tmp:
            tmp_path = Path(tmp.name)
            # Salva no padrão exato de exportação do ClimaPS (sep=;, decimal=,)
            mock_df.to_csv(tmp_path, sep=";", decimal=",", index=False, date_format="%Y-%m-%d %H:%M")

        try:
            dataset = load_station_csv(tmp_path)
            self.assertIsNotNone(dataset)
            self.assertEqual(len(dataset.data), 48)
            self.assertIn("precipitacao_mm", dataset.data.columns)
            self.assertIn("temp_max_c", dataset.data.columns)
            self.assertIn("data_hora", dataset.data.columns)
            self.assertEqual(dataset.data["precipitacao_mm"].iloc[1], 2.5)
            self.assertEqual(dataset.metadata["codigo_estacao"], "EXPORT")
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_load_exported_climaps_comma_csv(self):
        import tempfile
        from climaps.core.data_loader import load_station_csv

        # Simula exportação simples com vírgula e ponto decimal
        dates = pd.date_range("2026-11-01", periods=24, freq="h")
        mock_df = pd.DataFrame(
            {
                "data_hora": dates,
                "precipitacao_mm": [1.2] * len(dates),
                "temp_max_c": [31.5] * len(dates),
                "temp_min_c": [24.0] * len(dates),
            }
        )

        with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False, encoding="utf-8") as tmp:
            tmp_path = Path(tmp.name)
            mock_df.to_csv(tmp_path, sep=",", decimal=".", index=False)

        try:
            dataset = load_station_csv(tmp_path)
            self.assertIsNotNone(dataset)
            self.assertEqual(len(dataset.data), 24)
            self.assertEqual(dataset.data["temp_max_c"].iloc[0], 31.5)
            self.assertEqual(dataset.data["precipitacao_mm"].iloc[0], 1.2)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()


if __name__ == "__main__":
    unittest.main()
