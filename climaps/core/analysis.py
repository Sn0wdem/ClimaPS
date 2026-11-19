from __future__ import annotations  # Habilita avaliação adiada de type hints

from dataclasses import dataclass  # Importa dataclass para definir especificações de filtro

import numpy as np  # Importa NumPy para constantes/cálculos numéricos (como np.inf e np.nan)
import pandas as pd  # Importa pandas para análise e agregação dos dados


MESES_PT = {  # Dicionário de tradução do número do mês para sigla em português
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",  # Primeiro semestre
    7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez",  # Segundo semestre
}  # Fecha o dicionário de meses


@dataclass(frozen=True)  # Define uma estrutura imutável para armazenar os filtros ativos da interface
class FilterSpec:  # Classe que representa os parâmetros de filtragem escolhidos pelo usuário
    start: pd.Timestamp | None = None  # Data inicial do filtro (opcional)
    end: pd.Timestamp | None = None  # Data final do filtro (opcional)
    hour_start: int = 0  # Hora inicial da faixa horária (padrão 0h)
    hour_end: int = 23  # Hora final da faixa horária (padrão 23h)
    rainy_only: bool = False  # Se True, mantém apenas horas com precipitação > 0


def apply_filters(df: pd.DataFrame, spec: FilterSpec) -> pd.DataFrame:  # Aplica o objeto FilterSpec sobre o DataFrame
    mask = pd.Series(True, index=df.index)  # Cria uma máscara booleana inicialmente True para todas as linhas
    if spec.start is not None:  # Se houver data inicial definida
        mask &= df["data_hora"] >= pd.Timestamp(spec.start).normalize()  # Filtra datas a partir das 00:00 do dia inicial
    if spec.end is not None:  # Se houver data final definida
        fim = pd.Timestamp(spec.end).normalize() + pd.offsets.Day(1)  # Calcula as 00:00 do dia seguinte para incluir todo o dia final
        mask &= df["data_hora"] < fim  # Mantém registros estritamente menores que o início do dia seguinte
    mask &= df["hora_num"].between(spec.hour_start, spec.hour_end)  # Filtra horas dentro do intervalo [hour_start, hour_end]
    if spec.rainy_only:  # Se o usuário marcou "Somente horas com chuva"
        mask &= df["precipitacao_mm"].fillna(0).gt(0)  # Trata NaN como 0 e mantém apenas linhas com chuva maior que zero
    return df.loc[mask].copy()  # Retorna uma cópia do DataFrame apenas com as linhas que passaram em todos os filtros


def calculate_kpis(df: pd.DataFrame) -> dict[str, float | int | str]:  # Calcula os indicadores principais (KPIs) do recorte
    total_cells = len(df) * 3  # Total de células analisadas nas 3 variáveis meteorológicas principais
    valid_cells = int(df[["precipitacao_mm", "temp_max_c", "temp_min_c"]].notna().sum().sum())  # Soma quantas células não são nulas
    completude = 100 * valid_cells / total_cells if total_cells else 0.0  # Calcula percentual de preenchimento (evita divisão por zero)
    return {  # Retorna o dicionário com os 5 KPIs
        "registros": len(df),  # Quantidade total de linhas/horas no recorte
        "precipitacao_total": float(df["precipitacao_mm"].sum()),  # Soma da precipitação acumulada (mm)
        "temp_max_media": float(df["temp_max_c"].mean()),  # Média das temperaturas máximas (°C)
        "temp_min_media": float(df["temp_min_c"].mean()),  # Média das temperaturas mínimas (°C)
        "completude": completude,  # Percentual de dados válidos (%)
    }  # Fecha o dicionário retornado


def monthly_summary(df: pd.DataFrame) -> pd.DataFrame:  # Gera tabela resumida agrupada por mês
    resumo = (  # Inicia a pipeline de agrupamento mensal
        df.dropna(subset=["data_hora"])  # Descarta linhas sem timestamp válido
        .groupby("mes", as_index=False)  # Agrupa pelo número do mês mantendo "mes" como coluna normal
        .agg(  # Define as agregações para cada coluna
            registros=("data_hora", "size"),  # Conta quantos registros existem no mês
            precipitacao_mm=("precipitacao_mm", "sum"),  # Soma total de chuva no mês
            temp_max_media=("temp_max_c", "mean"),  # Média da temperatura máxima no mês
            temp_min_media=("temp_min_c", "mean"),  # Média da temperatura mínima no mês
            horas_com_chuva=("precipitacao_mm", lambda s: int(s.fillna(0).gt(0).sum())),  # Conta quantas horas tiveram chuva > 0
        )  # Fecha as agregações
    )  # Finaliza o DataFrame resumo
    resumo["mes_nome"] = resumo["mes"].map(MESES_PT)  # Adiciona a coluna com o nome abreviado do mês em português
    return resumo  # Retorna o resumo mensal


def daily_summary(df: pd.DataFrame) -> pd.DataFrame:  # Gera tabela resumida agrupada por dia
    return (  # Retorna diretamente o resultado do agrupamento diário
        df.dropna(subset=["dia"])  # Remove linhas sem data diária válida
        .groupby("dia", as_index=False)  # Agrupa pela coluna "dia"
        .agg(  # Define as métricas diárias
            precipitacao_mm=("precipitacao_mm", "sum"),  # Total de chuva acumulada no dia
            temp_max_media=("temp_max_c", "mean"),  # Média das máximas horárias do dia
            temp_min_media=("temp_min_c", "mean"),  # Média das mínimas horárias do dia
        )  # Fecha agg
    )  # Fecha retorno


def _iqr_outlier_count(series: pd.Series) -> int:  # Conta outliers usando o método do Intervalo Interquartil (IQR)
    limpa = series.dropna()  # Remove valores ausentes antes de calcular quartis
    if limpa.empty:  # Se não houver nenhum dado válido na série
        return 0  # Retorna zero outliers
    q1, q3 = limpa.quantile([0.25, 0.75])  # Calcula o primeiro quartil (25%) e o terceiro quartil (75%)
    iqr = q3 - q1  # Calcula o intervalo interquartil (Q3 - Q1)
    if iqr == 0:  # Caso especial em que Q1 e Q3 são iguais (ex.: chuva = 0 na maior parte do tempo)
        return int((limpa != limpa.median()).sum())  # Considera outlier tudo que for diferente da mediana
    return int(((limpa < q1 - 1.5 * iqr) | (limpa > q3 + 1.5 * iqr)).sum())  # Conta valores abaixo/acima de 1,5 * IQR dos quartis


def quality_report(df: pd.DataFrame) -> dict[str, object]:  # Gera um diagnóstico de qualidade dos dados
    valid_dt = df["data_hora"].dropna()  # Separa apenas os timestamps válidos
    if valid_dt.empty:  # Se não houver nenhum timestamp válido
        missing_timestamps = 0  # Não há referência temporal para calcular lacunas
    else:  # Caso existam datas válidas
        expected = pd.date_range(valid_dt.min(), valid_dt.max(), freq="h")  # Gera a grade horária contínua esperada do início ao fim
        missing_timestamps = len(expected.difference(pd.DatetimeIndex(valid_dt)))  # Conta quantas horas esperadas faltam no DataFrame

    numeric = ["precipitacao_mm", "temp_max_c", "temp_min_c"]  # Lista das colunas numéricas auditadas
    nulls = {col: int(df[col].isna().sum()) for col in numeric}  # Conta valores ausentes (NaN) por coluna
    outliers = {col: _iqr_outlier_count(df[col]) for col in numeric}  # Conta outliers (IQR) por coluna
    return {  # Retorna dicionário completo com todas as métricas de qualidade
        "linhas": len(df),  # Total de linhas da base
        "duplicadas": int(df.duplicated().sum()),  # Quantidade de linhas inteiramente repetidas
        "timestamps_duplicados": int(df["data_hora"].duplicated().sum()),  # Quantidade de datas/horas repetidas
        "timestamps_ausentes": int(missing_timestamps),  # Quantidade de buracos (horas faltantes) na série
        "datas_invalidas": int(df["data_hora"].isna().sum()),  # Quantidade de datas que falharam no parsing
        "valores_ausentes": nulls,  # Dicionário com contagem de nulos por variável
        "outliers_iqr": outliers,  # Dicionário com contagem de outliers por variável
        "chuva_negativa": int(df["precipitacao_mm"].lt(0).sum()),  # Verifica inconsistência física: precipitação < 0
        "temp_inconsistente": int(df["temp_max_c"].lt(df["temp_min_c"]).sum()),  # Verifica inconsistência: máx < mín
    }  # Fecha o dicionário de diagnóstico


def generate_insights(df: pd.DataFrame) -> list[str]:  # Gera frases automáticas com destaques do recorte filtrado
    if df.empty:  # Se o recorte não tiver registros
        return ["Nenhum registro atende aos filtros atuais."]  # Retorna mensagem única explicativa
    mensal = monthly_summary(df)  # Calcula o resumo mensal do recorte
    diario = daily_summary(df)  # Calcula o resumo diário do recorte
    chuva_mes = mensal.loc[mensal["precipitacao_mm"].idxmax()]  # Seleciona a linha do mês com maior chuva acumulada
    quente = mensal.loc[mensal["temp_max_media"].idxmax()]  # Seleciona a linha do mês com maior temperatura máxima média
    pico_idx = df["precipitacao_mm"].idxmax() if df["precipitacao_mm"].notna().any() else None  # Obtém o índice do maior pico horário de chuva
    insights = [  # Cria a lista inicial de insights textuais
        f"{chuva_mes['mes_nome']} foi o mês mais chuvoso do recorte, com {chuva_mes['precipitacao_mm']:.1f} mm.",  # Frase do mês mais chuvoso
        f"{quente['mes_nome']} teve a maior temperatura máxima média: {quente['temp_max_media']:.1f} °C.",  # Frase do mês mais quente
    ]  # Fecha a lista inicial
    if pico_idx is not None:  # Se houver ao menos um valor válido de precipitação
        pico = df.loc[pico_idx]  # Recupera a linha do registro de pico
        insights.append(  # Adiciona a frase sobre o recorde horário de chuva
            f"O maior registro horário de chuva foi {pico['precipitacao_mm']:.1f} mm em "  # Valor do pico
            f"{pico['data_hora']:%d/%m/%Y às %H:%M}."  # Data e hora formatadas no padrão brasileiro
        )  # Fecha append
    dias_secos = int(diario["precipitacao_mm"].eq(0).sum())  # Conta quantos dias tiveram soma diária de chuva igual a zero
    insights.append(f"O recorte contém {dias_secos} dias sem precipitação registrada.")  # Adiciona a frase sobre dias secos
    return insights  # Retorna a lista final de insights


def correlation_matrix(df: pd.DataFrame) -> pd.DataFrame:  # Calcula a matriz de correlação de Pearson entre as variáveis
    cols = ["precipitacao_mm", "temp_max_c", "temp_min_c"]  # Seleciona as três variáveis meteorológicas
    return df[cols].corr().replace([np.inf, -np.inf], np.nan)  # Calcula .corr() e troca eventuais infinitos por NaN