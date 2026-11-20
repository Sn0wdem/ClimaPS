from __future__ import annotations  # Permite usar anotações de tipo modernas (como str | Path) como strings avaliadas tardiamente

from dataclasses import dataclass  # Importa o decorador dataclass para criar classes de dados enxutas
from io import StringIO  # Permite tratar uma string em memória como se fosse um arquivo de texto
from pathlib import Path  # Classe orientada a objetos para manipular caminhos de arquivos e pastas
import re  # Módulo de expressões regulares para limpar/normalizar textos

import pandas as pd  # Importa a biblioteca pandas para leitura e manipulação de tabelas (DataFrames)


COLUNAS_INTERNAS = {  # Dicionário que mapeia os nomes longos das colunas do CSV do INMET para nomes curtos internos
    "Data Medicao": "data",  # Coluna de data da medição -> "data"
    "Hora Medicao": "hora",  # Coluna de hora da medição (ex.: 0000, 1300) -> "hora"
    "PRECIPITACAO TOTAL, HORARIO(mm)": "precipitacao_mm",  # Coluna de chuva horária -> "precipitacao_mm"
    "TEMPERATURA MAXIMA NA HORA ANT. (AUT)(°C)": "temp_max_c",  # Temperatura máxima da hora anterior -> "temp_max_c"
    "TEMPERATURA MINIMA NA HORA ANT. (AUT)(°C)": "temp_min_c",  # Temperatura mínima da hora anterior -> "temp_min_c"
}  # Fecha o dicionário de mapeamento de colunas


@dataclass(frozen=True)  # Cria uma classe de dados imutável (frozen=True impede alterar seus atributos após criada)
class StationDataset:  # Define a estrutura que agrupa metadados, tabela e caminho do arquivo carregado
    """Dados normalizados e metadados extraídos do arquivo do INMET."""  # Docstring explicando o papel da classe

    metadata: dict[str, str]  # Dicionário com informações do cabeçalho do INMET (ex.: nome, latitude, altitude)
    data: pd.DataFrame  # DataFrame do pandas contendo as medições horárias já tratadas
    source: Path  # Caminho completo do arquivo CSV de origem


def _normalizar_chave(texto: str) -> str:  # Função auxiliar privada para padronizar chaves dos metadados
    texto = texto.strip().lower()  # Remove espaços nas pontas e converte todo o texto para minúsculas
    texto = re.sub(r"[^a-z0-9]+", "_", texto)  # Substitui qualquer sequência que não seja letra/número por "_"
    return texto.strip("_")  # Remove eventuais "_" sobrando no início ou no fim e retorna a chave limpa


def _localizar_cabecalho(linhas: list[str]) -> int:  # Função auxiliar para achar em qual linha começa a tabela no CSV
    for indice, linha in enumerate(linhas):  # Percorre todas as linhas do arquivo mantendo o índice (número da linha)
        limpa = linha.lstrip("\ufeff").strip().lower()  # Remove BOM UTF-8 e espaços nas pontas em minúsculas
        # 1. Padrão original de arquivos de estações do INMET
        if limpa.startswith("data medicao") or "data medicao;" in limpa or "data medicao," in limpa:
            return indice
        # 2. Padrão exportado pelo ClimaPS ou tabelas normalizadas com colunas principais
        if "precipitacao_mm" in limpa and ("temp_max_c" in limpa or "data" in limpa):
            return indice
        # 3. Padrão com timestamp completo e variáveis climáticas
        if "data_hora" in limpa and ("temp" in limpa or "precipitacao" in limpa or "chuva" in limpa):
            return indice
    raise ValueError(
        "Cabeçalho de dados meteorológicos não encontrado no arquivo CSV. "
        "O arquivo deve conter o padrão do INMET ('Data Medicao') ou o padrão exportado do ClimaPS ('data_hora', 'precipitacao_mm')."
    )


def load_station_csv(path: str | Path) -> StationDataset:  # Função principal que lê e normaliza um CSV do INMET ou exportado
    """Lê o CSV do INMET ou exportado pelo ClimaPS, separando metadados e observações horárias.

    Suporta tanto os arquivos brutos do INMET (com metadados no topo e colunas
    longas) quanto arquivos exportados pela aplicação (com cabeçalho direto e
    colunas normalizadas).
    """

    source = Path(path).expanduser().resolve()  # Converte o caminho para Path, expande "~" se houver e resolve o caminho absoluto
    if not source.exists():  # Verifica se o arquivo realmente existe no disco
        raise FileNotFoundError(f"Arquivo não encontrado: {source}")  # Lança exceção caso o arquivo não exista

    texto = source.read_text(encoding="utf-8-sig")  # Lê todo o conteúdo do CSV removendo o BOM UTF-8 se existir
    linhas = texto.splitlines()  # Quebra o texto lido em uma lista de linhas
    header_index = _localizar_cabecalho(linhas)  # Descobre o índice da linha em que a tabela de dados começa

    metadata: dict[str, str] = {}  # Inicializa o dicionário que guardará os metadados do topo do arquivo
    for linha in linhas[:header_index]:  # Percorre apenas as linhas anteriores ao cabeçalho da tabela
        if ":" in linha:  # Verifica se a linha tem o formato "Chave: Valor"
            chave, valor = linha.split(":", 1)  # Divide a linha apenas no primeiro ":" em chave e valor
            metadata[_normalizar_chave(chave)] = valor.strip()  # Normaliza a chave, limpa espaços do valor e salva no dicionário

    tabela = "\n".join(linhas[header_index:])  # Junta novamente em uma única string apenas as linhas da tabela (do cabeçalho em diante)
    header_line = linhas[header_index]  # Linha com os nomes das colunas
    sep = ";" if ";" in header_line else ","  # Detecta automaticamente separador ponto-e-vírgula ou vírgula
    decimal = "," if sep == ";" else "."  # Define separador decimal conforme o delimitador de colunas

    df = pd.read_csv(  # Lê a tabela usando pandas.read_csv
        StringIO(tabela),  # Passa a string da tabela embrulhada em StringIO para simular um arquivo
        sep=sep,  # Separador detectado
        decimal=decimal,  # Separador decimal apropriado
        na_values=["", "-9999", "-9999,0", "null", "NULL", "NaN", "nan"],  # Valores interpretados como ausentes
    )  # Finaliza a leitura do CSV para o DataFrame
    df = df.dropna(axis=1, how="all")  # Remove colunas inteiramente vazias (comum pelo ";" extra no fim das linhas do INMET)

    # Caso 1: CSV original do INMET com colunas longas
    inmet_matches = [k for k in COLUNAS_INTERNAS if k in df.columns]
    if len(inmet_matches) == len(COLUNAS_INTERNAS):
        df = df.rename(columns=COLUNAS_INTERNAS)

    # Caso 2: CSV exportado ou com nomes alternativos
    alias_map = {
        "chuva_mm": "precipitacao_mm",
        "chuva": "precipitacao_mm",
        "temperatura_c": "temp_max_c",
        "temp_c": "temp_max_c",
    }
    for alt, standard in alias_map.items():
        if alt in df.columns and standard not in df.columns:
            df[standard] = df[alt]

    if "temp_min_c" not in df.columns and "temp_max_c" in df.columns:
        df["temp_min_c"] = df["temp_max_c"]

    # Garante que as 3 colunas numéricas essenciais existam
    required = ["precipitacao_mm", "temp_max_c", "temp_min_c"]
    for req in required:
        if req not in df.columns:
            raise ValueError(f"Coluna obrigatória ausente no CSV: '{req}'")
        df[req] = pd.to_numeric(df[req], errors="coerce")

    # Tratamento e montagem de data e hora
    if "data_hora" in df.columns and df["data_hora"].notna().any():
        df["data_hora"] = pd.to_datetime(df["data_hora"], errors="coerce")
    elif "data" in df.columns and "hora" in df.columns:
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
    elif "data" in df.columns:
        df["data_hora"] = pd.to_datetime(df["data"], errors="coerce")
    else:
        raise ValueError("O CSV precisa conter uma coluna de data/hora ('data_hora' ou 'data').")

    df = df.dropna(subset=["data_hora"]).copy()  # Remove eventuais linhas com timestamp inválido
    df["hora_num"] = df["data_hora"].dt.hour  # Extrai a hora inteira (0 a 23) como coluna auxiliar para filtros
    df["hora"] = df["hora_num"] * 100  # Mantém compatibilidade com hora inteira do padrão INMET (ex.: 1400)
    df["mes"] = df["data_hora"].dt.month  # Extrai o número do mês (1 a 12) para agrupamentos mensais
    df["dia"] = df["data_hora"].dt.floor("D")  # Trunca "data_hora" para meia-noite do dia (agrupamento diário)
    df["data"] = df["dia"]  # Mantém compatibilidade com a coluna "data"

    df = df.sort_values("data_hora", na_position="last").reset_index(drop=True)  # Ordena cronologicamente e refaz o índice

    if not metadata:  # Se não houver metadados no topo do arquivo (ex.: CSV exportado diretamente)
        clean_name = source.stem.replace("climaps_dados_", "").replace("dados_editados_", "").replace("_", " ").strip()
        metadata = {
            "nome": clean_name.upper() if clean_name else "ARQUIVO CSV",
            "codigo_estacao": "EXPORT",
            "fonte": "ClimaPS / Exportação",
        }

    return StationDataset(metadata=metadata, data=df, source=source)  # Retorna o objeto StationDataset completo