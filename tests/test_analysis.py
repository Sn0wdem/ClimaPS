from pathlib import Path
import sys
import unittest

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from climaps.core.analysis import FilterSpec, apply_filters, calculate_kpis, monthly_summary, quality_report
from climaps.core.data_loader import load_station_csv


class StationAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dataset = load_station_csv(ROOT / "data" / "dados_A101_H_2014.csv")
        cls.df = cls.dataset.data

    def test_metadata_and_shape(self):
        self.assertEqual(self.dataset.metadata["nome"], "MANAUS")
        self.assertEqual(self.dataset.metadata["codigo_estacao"], "A101")
        self.assertEqual(len(self.df), 8760)

    def test_complete_hourly_timeline(self):
        self.assertEqual(self.df["data_hora"].min(), pd.Timestamp("2014-01-01 00:00"))
        self.assertEqual(self.df["data_hora"].max(), pd.Timestamp("2014-12-31 23:00"))
        self.assertEqual(self.df["data_hora"].nunique(), 8760)

    def test_missing_values(self):
        self.assertEqual(int(self.df["precipitacao_mm"].isna().sum()), 92)
        self.assertEqual(int(self.df["temp_max_c"].isna().sum()), 95)
        self.assertEqual(int(self.df["temp_min_c"].isna().sum()), 95)

    def test_kpis(self):
        kpis = calculate_kpis(self.df)
        self.assertAlmostEqual(kpis["precipitacao_total"], 2123.8, places=1)
        self.assertAlmostEqual(kpis["temp_max_media"], 28.2192, places=3)
        self.assertGreater(kpis["completude"], 98.0)

    def test_march_is_rainiest(self):
        resumo = monthly_summary(self.df)
        rainiest = resumo.loc[resumo["precipitacao_mm"].idxmax()]
        self.assertEqual(int(rainiest["mes"]), 3)
        self.assertAlmostEqual(rainiest["precipitacao_mm"], 458.0, places=1)

    def test_filter_january_afternoon(self):
        spec = FilterSpec(
            start=pd.Timestamp("2014-01-01"),
            end=pd.Timestamp("2014-01-31"),
            hour_start=12,
            hour_end=17,
        )
        result = apply_filters(self.df, spec)
        self.assertEqual(len(result), 31 * 6)
        self.assertTrue(result["hora_num"].between(12, 17).all())

    def test_quality_rules(self):
        report = quality_report(self.df)
        self.assertEqual(report["timestamps_ausentes"], 0)
        self.assertEqual(report["timestamps_duplicados"], 0)
        self.assertEqual(report["chuva_negativa"], 0)
        self.assertEqual(report["temp_inconsistente"], 0)


if __name__ == "__main__":
    unittest.main()
