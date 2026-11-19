from pathlib import Path  # Manipulação de caminhos para localizar a raiz do projeto e o CSV de teste
import sys  # Acesso ao sys.path para garantir a importação do pacote climaps
import unittest  # Framework padrão de testes unitários do Python

import pandas as pd  # Usado para criar Timestamps esperados nas asserções


ROOT = Path(__file__).resolve().parents[1]  # Sobe dois níveis a partir de tests/test_analysis.py para achar a raiz do projeto
sys.path.insert(0, str(ROOT))  # Insere a raiz no início do sys.path para permitir "from climaps..." mesmo rodando de outra pasta

from climaps.core.analysis import FilterSpec, apply_filters, calculate_kpis, monthly_summary, quality_report  # Funções sob teste
from climaps.core.data_loader import load_station_csv  # Função de leitura de CSV sob teste


class StationAnalysisTests(unittest.TestCase):  # Define a suíte de testes herdando de unittest.TestCase
    @classmethod  # Método de classe executado uma única vez antes de todos os testes desta classe
    def setUpClass(cls):  # Carrega o dataset de exemplo uma só vez para acelerar os testes
        cls.dataset = load_station_csv(ROOT / "data" / "dados_A101_H_2014.csv")  # Lê o CSV de Manaus (2014)
        cls.df = cls.dataset.data  # Guarda o DataFrame normalizado em cls.df

    def test_metadata_and_shape(self):  # Testa metadados extraídos e quantidade total de linhas
        self.assertEqual(self.dataset.metadata["nome"], "MANAUS")  # Confirma nome da estação
        self.assertEqual(self.dataset.metadata["codigo_estacao"], "A101")  # Confirma código da estação
        self.assertEqual(len(self.df), 8760)  # Confirma 8.760 horas (365 dias × 24 horas)

    def test_complete_hourly_timeline(self):  # Testa continuidade da linha do tempo horária
        self.assertEqual(self.df["data_hora"].min(), pd.Timestamp("2014-01-01 00:00"))  # Primeiro registro em 01/01 00:00
        self.assertEqual(self.df["data_hora"].max(), pd.Timestamp("2014-12-31 23:00"))  # Último registro em 31/12 23:00
        self.assertEqual(self.df["data_hora"].nunique(), 8760)  # Confirma 8.760 timestamps únicos (sem repetição ou falta)

    def test_missing_values(self):  # Testa a contagem esperada de valores ausentes ("null") no CSV de exemplo
        self.assertEqual(int(self.df["precipitacao_mm"].isna().sum()), 92)  # 92 valores nulos em precipitação
        self.assertEqual(int(self.df["temp_max_c"].isna().sum()), 95)  # 95 valores nulos em temp. máxima
        self.assertEqual(int(self.df["temp_min_c"].isna().sum()), 95)  # 95 valores nulos em temp. mínima

    def test_kpis(self):  # Testa o cálculo dos KPIs gerais sobre todo o ano de 2014
        kpis = calculate_kpis(self.df)  # Calcula os KPIs
        self.assertAlmostEqual(kpis["precipitacao_total"], 2123.8, places=1)  # Chuva total esperada: 2123,8 mm
        self.assertAlmostEqual(kpis["temp_max_media"], 28.2192, places=3)  # Média das máximas: ~28,219 °C
        self.assertGreater(kpis["completude"], 98.0)  # Completude acima de 98%

    def test_march_is_rainiest(self):  # Testa se o resumo mensal identifica março como o mês mais chuvoso
        resumo = monthly_summary(self.df)  # Gera resumo mensal
        rainiest = resumo.loc[resumo["precipitacao_mm"].idxmax()]  # Pega o mês com maior soma de precipitação
        self.assertEqual(int(rainiest["mes"]), 3)  # Confirma mês 3 (Março)
        self.assertAlmostEqual(rainiest["precipitacao_mm"], 458.0, places=1)  # Confirma acumulado de 458,0 mm

    def test_filter_january_afternoon(self):  # Testa o filtro por período (janeiro) e faixa horária (12h às 17h)
        spec = FilterSpec(  # Cria especificação de filtro
            start=pd.Timestamp("2014-01-01"),  # Início em 1º de janeiro
            end=pd.Timestamp("2014-01-31"),  # Fim em 31 de janeiro
            hour_start=12,  # A partir das 12h
            hour_end=17,  # Até as 17h
        )  # Fecha FilterSpec
        result = apply_filters(self.df, spec)  # Aplica filtro
        self.assertEqual(len(result), 31 * 6)  # Espera 31 dias × 6 horas (12, 13, 14, 15, 16, 17) = 186 linhas
        self.assertTrue(result["hora_num"].between(12, 17).all())  # Confirma que todas as linhas estão entre 12h e 17h

    def test_quality_rules(self):  # Testa o relatório de qualidade no dataset de exemplo
        report = quality_report(self.df)  # Executa auditoria
        self.assertEqual(report["timestamps_ausentes"], 0)  # Sem lacunas de horário
        self.assertEqual(report["timestamps_duplicados"], 0)  # Sem horários duplicados
        self.assertEqual(report["chuva_negativa"], 0)  # Sem chuva negativa
        self.assertEqual(report["temp_inconsistente"], 0)  # Sem máxima menor que mínima


if __name__ == "__main__":  # Permite executar os testes rodando o arquivo diretamente
    unittest.main()  # Executa o runner de testes do unittest