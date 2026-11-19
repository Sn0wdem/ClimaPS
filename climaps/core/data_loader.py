from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
from pathlib import Path
import re

import pandas as pd


COLUNAS_INTERNAS = {
    "Data Medicao": "data",
    "Hora Medicao": "hora",
    "PRECIPITACAO TOTAL, HORARIO(mm)": "precipitacao_mm",
    "TEMPERATURA MAXIMA NA HORA ANT. (AUT)(°C)": "temp_max_c",
    "TEMPERATURA MINIMA NA HORA ANT. (AUT)(°C)": "temp_min_c",
}


@dataclass(frozen=True)
class StationDataset:
    """Dados normalizados e metadados extraídos do arquivo do INMET."""

    metadata: dict[str, str]
    data: pd.DataFrame
    source: Path


def _normalizar_chave(texto: str) -> str:
    texto = texto.strip().lower()
    texto = re.sub(r"[^a-z0-9]+", "_", texto)
    return texto.strip("_")


def _localizar_cabecalho(linhas: list[str]) -> int:
    for indice, linha in enumerate(linhas):
        if linha.lstrip("\ufeff").startswith("Data Medicao;"):
            return indice
    raise ValueError("Cabeçalho 'Data Medicao' não encontrado no arquivo.")


def load_station_csv(path: str | Path) -> StationDataset:
    """Lê o CSV do INMET, separando metadados e observações horárias.

    O arquivo tem metadados antes da tabela, usa ponto e vírgula como
    separador e vírgula como separador decimal. A função trata esses três
    detalhes e devolve nomes de colunas curtos, adequados ao código.
    """

    source = Path(path).expanduser().resolve()
    if not source.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {source}")

    texto = source.read_text(encoding="utf-8-sig")
    linhas = texto.splitlines()
    header_index = _localizar_cabecalho(linhas)

    metadata: dict[str, str] = {}
    for linha in linhas[:header_index]:
        if ":" in linha:
            chave, valor = linha.split(":", 1)
            metadata[_normalizar_chave(chave)] = valor.strip()

    tabela = "\n".join(linhas[header_index:])
    df = pd.read_csv(
        StringIO(tabela),
        sep=";",
        decimal=",",
        na_values=["", "-9999", "-9999,0", "null", "NULL"],
    )
    df = df.dropna(axis=1, how="all")

    ausentes = [nome for nome in COLUNAS_INTERNAS if nome not in df.columns]
    if ausentes:
        raise ValueError(f"Colunas obrigatórias ausentes: {', '.join(ausentes)}")

    df = df.rename(columns=COLUNAS_INTERNAS)[list(COLUNAS_INTERNAS.values())]
    df["data"] = pd.to_datetime(df["data"], errors="coerce")
    hora_texto = (
        df["hora"]
        .astype("Int64")
        .astype(str)
        .str.replace("<NA>", "", regex=False)
        .str.zfill(4)
    )
    df["data_hora"] = pd.to_datetime(
        df["data"].dt.strftime("%Y-%m-%d")
        + " "
        + hora_texto.str[:2]
        + ":"
        + hora_texto.str[2:],
        errors="coerce",
    )

    numericas = ["precipitacao_mm", "temp_max_c", "temp_min_c"]
    for coluna in numericas:
        df[coluna] = pd.to_numeric(df[coluna], errors="coerce")

    df["hora_num"] = df["data_hora"].dt.hour
    df["mes"] = df["data_hora"].dt.month
    df["dia"] = df["data_hora"].dt.floor("D")
    df = df.sort_values("data_hora", na_position="last").reset_index(drop=True)
    return StationDataset(metadata=metadata, data=df, source=source)
