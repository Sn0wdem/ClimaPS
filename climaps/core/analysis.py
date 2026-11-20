from __future__ import annotations  # Habilita avaliação adiada de type hints

from dataclasses import dataclass  # Importa dataclass para definir especificações de filtro
import math  # Operações matemáticas para índices meteorológicos (logaritmo, raiz quadrada)

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


def calculate_dew_point(temp_c: float | int | None, humidity_pct: float | int | None) -> float | None:
    """Calcula o Ponto de Orvalho (Dew Point) usando a aproximação de Magnus-Tetens."""
    if temp_c is None or humidity_pct is None:
        return None
    try:
        t = float(temp_c)
        rh = max(1.0, min(100.0, float(humidity_pct)))
        a, b = 17.27, 237.7
        alpha = ((a * t) / (b + t)) + math.log(rh / 100.0)
        return round((b * alpha) / (a - alpha), 1)
    except Exception:
        return None


def calculate_heat_index(temp_c: float | int | None, humidity_pct: float | int | None) -> tuple[float | None, str, str]:
    """Calcula o Índice de Calor (Heat Index) e classifica o desconforto térmico (NOAA / Steadman).

    Retorna tupla: (indice_c, descricao_categoria, nivel_alerta).
    """
    if temp_c is None or humidity_pct is None:
        return None, "Indisponível", "baixo"
    try:
        t_c = float(temp_c)
        rh = max(1.0, min(100.0, float(humidity_pct)))
        t_f = t_c * 9.0 / 5.0 + 32.0

        if t_f < 80.0:
            hi_f = 0.5 * (t_f + 61.0 + ((t_f - 68.0) * 1.2) + (rh * 0.094))
        else:
            hi_f = (
                -42.379
                + 2.04901523 * t_f
                + 10.14333127 * rh
                - 0.22475541 * t_f * rh
                - 0.00683783 * (t_f**2)
                - 0.05481717 * (rh**2)
                + 0.00122874 * (t_f**2) * rh
                + 0.00085282 * t_f * (rh**2)
                - 0.00000199 * (t_f**2) * (rh**2)
            )
            if rh < 13.0 and 80.0 <= t_f <= 112.0:
                hi_f -= ((13.0 - rh) / 4.0) * math.sqrt((17.0 - abs(t_f - 95.0)) / 17.0)
            elif rh > 85.0 and 80.0 <= t_f <= 87.0:
                hi_f += ((rh - 85.0) / 10.0) * ((87.0 - t_f) / 5.0)

        hi_c = round((hi_f - 32.0) * 5.0 / 9.0, 1)
        if hi_c < 27.0:
            cat, level = "Normal / Confortável", "baixo"
        elif hi_c < 32.0:
            cat, level = "Atenção (Fadiga com exposição)", "cuidado"
        elif hi_c < 41.0:
            cat, level = "Cuidado Extremo (Cãibras/Insolação)", "cuidado_extremo"
        elif hi_c < 54.0:
            cat, level = "Perigo (Insolação Provável)", "perigo"
        else:
            cat, level = "Perigo Extremo (Alto Risco Térmico)", "perigo_extremo"

        return hi_c, cat, level
    except Exception:
        return None, "Indisponível", "baixo"


def evaluate_storm_risk(
    pressao_hpa: float | int | None,
    umidade_pct: float | int | None,
    vento_kmh: float | int | None,
    rajadas_kmh: float | int | None,
    precipitacao_mm: float | int | None = 0.0,
) -> dict[str, str]:
    """Avalia o risco de tempestade com base em queda barométrica, umidade e vento."""
    if pressao_hpa is None:
        return {
            "nivel": "Atmosfera Estável",
            "cor": "#10B981",
            "classe": "storm-low",
            "icone": "🟢",
            "detalhe": "Sem leitura barométrica no momento.",
        }

    try:
        p = float(pressao_hpa)
        rh = float(umidade_pct or 0.0)
        v = float(vento_kmh or 0.0)
        gust = float(rajadas_kmh or v)
        rain = float(precipitacao_mm or 0.0)

        # Queda barométrica crítica (< 1005 hPa) + umidade alta + vento forte ou chuva
        if (p < 1005.0 and rh >= 75.0 and (gust >= 30.0 or v >= 20.0 or rain > 0.5)) or (p < 1002.0 and gust >= 25.0):
            return {
                "nivel": "Alto Risco de Tempestade",
                "cor": "#EF4444",
                "classe": "storm-high",
                "icone": "⚡",
                "detalhe": f"Queda barométrica crítica ({p:.0f} hPa) combinada com umidade elevada ({rh:.0f}%) e rajadas ({gust:.1f} km/h). Risco de temporal severo.",
            }
        elif p < 1008.0 and (rh >= 70.0 or gust >= 35.0):
            return {
                "nivel": "Alerta de Instabilidade",
                "cor": "#F59E0B",
                "classe": "storm-med",
                "icone": "⚠️",
                "detalhe": f"Baixa pressão barométrica ({p:.0f} hPa) indicando instabilidade atmosférica e potencial para pancadas de chuva.",
            }
        elif gust >= 45.0:
            return {
                "nivel": "Alerta de Rajadas Intensas",
                "cor": "#F59E0B",
                "classe": "storm-med",
                "icone": "💨",
                "detalhe": f"Rajadas intensas de vento ({gust:.1f} km/h) detectadas nas proximidades.",
            }
        else:
            return {
                "nivel": "Atmosfera Estável",
                "cor": "#10B981",
                "classe": "storm-low",
                "icone": "🟢",
                "detalhe": f"Pressão atmosférica estável ({p:.0f} hPa) e sem indicativo de tempestades severas imediatas.",
            }
    except Exception:
        return {
            "nivel": "Atmosfera Estável",
            "cor": "#10B981",
            "classe": "storm-low",
            "icone": "🟢",
            "detalhe": "Condições atmosféricas regulares.",
        }


def calculate_climate_anomaly(
    df: pd.DataFrame | None,
    current_weather: dict[str, object] | None,
) -> dict[str, object] | None:
    """Calcula anomalias climáticas comparando a medição ao vivo com a média histórica daquele mês/dia no dataset."""
    if df is None or df.empty or current_weather is None:
        return None

    raw_dt = current_weather.get("horario_raw") or current_weather.get("horario")
    try:
        now_dt = pd.to_datetime(raw_dt)
        mes_atual = int(now_dt.month)
    except Exception:
        mes_atual = 11

    meses_extenso = {
        1: "janeiro", 2: "fevereiro", 3: "março", 4: "abril", 5: "maio", 6: "junho",
        7: "julho", 8: "agosto", 9: "setembro", 10: "outubro", 11: "novembro", 12: "dezembro",
    }
    nome_mes = meses_extenso.get(mes_atual, str(mes_atual))

    df_mes = df[df["mes"] == mes_atual] if "mes" in df.columns else df
    if df_mes.empty:
        df_mes = df

    hist_max = float(df_mes["temp_max_c"].dropna().mean()) if df_mes["temp_max_c"].notna().any() else 0.0
    hist_min = float(df_mes["temp_min_c"].dropna().mean()) if df_mes["temp_min_c"].notna().any() else 0.0
    hist_temp_mean = (hist_max + hist_min) / 2.0 if (hist_max and hist_min) else (hist_max or hist_min)

    days_count = max(1, df_mes["dia"].nunique()) if "dia" in df_mes.columns else 30
    total_rain = float(df_mes["precipitacao_mm"].dropna().sum()) if df_mes["precipitacao_mm"].notna().any() else 0.0
    hist_rain_daily_avg = total_rain / days_count

    curr_temp = current_weather.get("temperatura_c")
    curr_rain = float(current_weather.get("precipitacao_mm") or 0.0)
    local = str(current_weather.get("local", "O local"))

    if curr_temp is None or not hist_temp_mean:
        return None

    temp_val = float(curr_temp)
    delta_temp = temp_val - hist_temp_mean
    delta_rain = curr_rain - hist_rain_daily_avg

    sinal_temp = "+" if delta_temp >= 0 else ""
    adjetivo = "acima da" if delta_temp >= 0 else "abaixo da"

    summary_text = (
        f"{local} está {sinal_temp}{delta_temp:.1f} °C {adjetivo} média histórica para {nome_mes} "
        f"({temp_val:.1f} °C atual vs. {hist_temp_mean:.1f} °C média histórica)."
    )

    return {
        "has_history": True,
        "mes_num": mes_atual,
        "mes_nome": nome_mes.capitalize(),
        "hist_temp_mean": round(hist_temp_mean, 1),
        "hist_max_mean": round(hist_max, 1),
        "hist_min_mean": round(hist_min, 1),
        "hist_rain_daily_avg": round(hist_rain_daily_avg, 1),
        "curr_temp": round(temp_val, 1),
        "curr_rain": round(curr_rain, 1),
        "delta_temp": round(delta_temp, 1),
        "delta_rain": round(delta_rain, 1),
        "summary_text": summary_text,
        "status": "quente" if delta_temp > 0.5 else ("frio" if delta_temp < -0.5 else "neutro"),
    }


def classify_air_quality(us_aqi: float | int | None, pm2_5: float | int | None) -> dict[str, str]:
    """Classifica a qualidade do ar segundo o padrão US AQI e PM2.5 (essencial para fumaça/queimadas)."""
    if us_aqi is None and pm2_5 is None:
        return {
            "status": "Sem Dados",
            "cor": "#94A3B8",
            "badge_class": "aqi-unknown",
            "icone": "⚪",
            "recomendacao": "Dados de qualidade do ar não disponíveis para esta coordenada.",
        }

    val = float(us_aqi) if us_aqi is not None else (float(pm2_5) * 3.0 if pm2_5 is not None else 0.0)

    if val <= 50:
        return {
            "status": "Boa",
            "cor": "#10B981",
            "badge_class": "aqi-good",
            "icone": "🟢",
            "recomendacao": "Qualidade do ar satisfatória; sem risco à saúde da população.",
        }
    elif val <= 100:
        return {
            "status": "Moderada",
            "cor": "#F59E0B",
            "badge_class": "aqi-moderate",
            "icone": "🟡",
            "recomendacao": "Qualidade aceitável. Indivíduos hipersensíveis a partículas devem monitorar sintomas.",
        }
    elif val <= 150:
        return {
            "status": "Alerta p/ Grupos Sensíveis",
            "cor": "#F97316",
            "badge_class": "aqi-sensitive",
            "icone": "🟠",
            "recomendacao": "Fumaça / material particulado perceptível. Crianças, idosos e pessoas com asma devem evitar esforço externo prolongado.",
        }
    elif val <= 200:
        return {
            "status": "Não Saudável",
            "cor": "#EF4444",
            "badge_class": "aqi-unhealthy",
            "icone": "🔴",
            "recomendacao": "Fumaça densa de queimadas. Toda a população pode sofrer irritação ocular e respiratória. Evite exercícios ao ar livre.",
        }
    else:
        return {
            "status": "Muito Prejudicial / Crítico",
            "cor": "#7C3AED",
            "badge_class": "aqi-hazardous",
            "icone": "🟣",
            "recomendacao": "Alerta de emergência de saúde por poluição severa. Permaneça em ambientes fechados com purificadores ou use máscaras de proteção.",
        }


def classify_uv(uv_index: float | int | None) -> dict[str, str]:
    """Classifica o índice UV de acordo com as normas da OMS (Organização Mundial da Saúde)."""
    if uv_index is None:
        return {"status": "Indisponível", "cor": "#94A3B8", "icone": "⚪", "recomendacao": "Sem leitura UV."}
    try:
        val = float(uv_index)
        if val < 3.0:
            return {"status": "Baixo", "cor": "#10B981", "icone": "🟢", "recomendacao": "Baixo risco. Proteção mínima."}
        elif val < 6.0:
            return {"status": "Moderado", "cor": "#F59E0B", "icone": "🟡", "recomendacao": "Use protetor solar e óculos de sol."}
        elif val < 8.0:
            return {"status": "Alto", "cor": "#F97316", "icone": "🟠", "recomendacao": "Proteção necessária: filtro solar FPS 30+, boné e sombra ao meio-dia."}
        elif val < 11.0:
            return {"status": "Muito Alto", "cor": "#EF4444", "icone": "🔴", "recomendacao": "Risco elevado de queimaduras. Evite exposição direta entre 10h e 16h."}
        else:
            return {"status": "Extremo", "cor": "#7C3AED", "icone": "🟣", "recomendacao": "Risco extremo à pele e aos olhos em poucos minutos. Procure sombra."}
    except Exception:
        return {"status": "Indisponível", "cor": "#94A3B8", "icone": "⚪", "recomendacao": "Sem leitura UV."}
