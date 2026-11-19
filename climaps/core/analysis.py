from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


MESES_PT = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
}


@dataclass(frozen=True)
class FilterSpec:
    start: pd.Timestamp | None = None
    end: pd.Timestamp | None = None
    hour_start: int = 0
    hour_end: int = 23
    rainy_only: bool = False


def apply_filters(df: pd.DataFrame, spec: FilterSpec) -> pd.DataFrame:
    mask = pd.Series(True, index=df.index)
    if spec.start is not None:
        mask &= df["data_hora"] >= pd.Timestamp(spec.start).normalize()
    if spec.end is not None:
        fim = pd.Timestamp(spec.end).normalize() + pd.offsets.Day(1)
        mask &= df["data_hora"] < fim
    mask &= df["hora_num"].between(spec.hour_start, spec.hour_end)
    if spec.rainy_only:
        mask &= df["precipitacao_mm"].fillna(0).gt(0)
    return df.loc[mask].copy()


def calculate_kpis(df: pd.DataFrame) -> dict[str, float | int | str]:
    total_cells = len(df) * 3
    valid_cells = int(df[["precipitacao_mm", "temp_max_c", "temp_min_c"]].notna().sum().sum())
    completude = 100 * valid_cells / total_cells if total_cells else 0.0
    return {
        "registros": len(df),
        "precipitacao_total": float(df["precipitacao_mm"].sum()),
        "temp_max_media": float(df["temp_max_c"].mean()),
        "temp_min_media": float(df["temp_min_c"].mean()),
        "completude": completude,
    }


def monthly_summary(df: pd.DataFrame) -> pd.DataFrame:
    resumo = (
        df.dropna(subset=["data_hora"])
        .groupby("mes", as_index=False)
        .agg(
            registros=("data_hora", "size"),
            precipitacao_mm=("precipitacao_mm", "sum"),
            temp_max_media=("temp_max_c", "mean"),
            temp_min_media=("temp_min_c", "mean"),
            horas_com_chuva=("precipitacao_mm", lambda s: int(s.fillna(0).gt(0).sum())),
        )
    )
    resumo["mes_nome"] = resumo["mes"].map(MESES_PT)
    return resumo


def daily_summary(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.dropna(subset=["dia"])
        .groupby("dia", as_index=False)
        .agg(
            precipitacao_mm=("precipitacao_mm", "sum"),
            temp_max_media=("temp_max_c", "mean"),
            temp_min_media=("temp_min_c", "mean"),
        )
    )


def _iqr_outlier_count(series: pd.Series) -> int:
    limpa = series.dropna()
    if limpa.empty:
        return 0
    q1, q3 = limpa.quantile([0.25, 0.75])
    iqr = q3 - q1
    if iqr == 0:
        return int((limpa != limpa.median()).sum())
    return int(((limpa < q1 - 1.5 * iqr) | (limpa > q3 + 1.5 * iqr)).sum())


def quality_report(df: pd.DataFrame) -> dict[str, object]:
    valid_dt = df["data_hora"].dropna()
    if valid_dt.empty:
        missing_timestamps = 0
    else:
        expected = pd.date_range(valid_dt.min(), valid_dt.max(), freq="h")
        missing_timestamps = len(expected.difference(pd.DatetimeIndex(valid_dt)))

    numeric = ["precipitacao_mm", "temp_max_c", "temp_min_c"]
    nulls = {col: int(df[col].isna().sum()) for col in numeric}
    outliers = {col: _iqr_outlier_count(df[col]) for col in numeric}
    return {
        "linhas": len(df),
        "duplicadas": int(df.duplicated().sum()),
        "timestamps_duplicados": int(df["data_hora"].duplicated().sum()),
        "timestamps_ausentes": int(missing_timestamps),
        "datas_invalidas": int(df["data_hora"].isna().sum()),
        "valores_ausentes": nulls,
        "outliers_iqr": outliers,
        "chuva_negativa": int(df["precipitacao_mm"].lt(0).sum()),
        "temp_inconsistente": int(df["temp_max_c"].lt(df["temp_min_c"]).sum()),
    }


def generate_insights(df: pd.DataFrame) -> list[str]:
    if df.empty:
        return ["Nenhum registro atende aos filtros atuais."]
    mensal = monthly_summary(df)
    diario = daily_summary(df)
    chuva_mes = mensal.loc[mensal["precipitacao_mm"].idxmax()]
    quente = mensal.loc[mensal["temp_max_media"].idxmax()]
    pico_idx = df["precipitacao_mm"].idxmax() if df["precipitacao_mm"].notna().any() else None
    insights = [
        f"{chuva_mes['mes_nome']} foi o mês mais chuvoso do recorte, com {chuva_mes['precipitacao_mm']:.1f} mm.",
        f"{quente['mes_nome']} teve a maior temperatura máxima média: {quente['temp_max_media']:.1f} °C.",
    ]
    if pico_idx is not None:
        pico = df.loc[pico_idx]
        insights.append(
            f"O maior registro horário de chuva foi {pico['precipitacao_mm']:.1f} mm em "
            f"{pico['data_hora']:%d/%m/%Y às %H:%M}."
        )
    dias_secos = int(diario["precipitacao_mm"].eq(0).sum())
    insights.append(f"O recorte contém {dias_secos} dias sem precipitação registrada.")
    return insights


def correlation_matrix(df: pd.DataFrame) -> pd.DataFrame:
    cols = ["precipitacao_mm", "temp_max_c", "temp_min_c"]
    return df[cols].corr().replace([np.inf, -np.inf], np.nan)
