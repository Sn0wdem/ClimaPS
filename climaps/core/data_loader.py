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
        if linha.lstrip("\ufeff").startswith("Data Medicao;"):  # Remove possível caractere BOM (\ufeff) e checa se começa com "Data Medicao;"
            return indice  # Retorna o índice da linha onde o cabeçalho da tabela foi encontrado
    raise ValueError("Cabeçalho 'Data Medicao' não encontrado no arquivo.")  # Lança erro se o arquivo não tiver o cabeçalho esperado


def load_station_csv(path: str | Path) -> StationDataset:  # Função principal que lê e normaliza um CSV do INMET
    """Lê o CSV do INMET, separando metadados e observações horárias.

    O arquivo tem metadados antes da tabela, usa ponto e vírgula como
    separador e vírgula como separador decimal. A função trata esses três
    detalhes e devolve nomes de colunas curtos, adequados ao código.
    """  # Docstring explicando o funcionamento da função

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
    df = pd.read_csv(  # Lê a tabela usando pandas.read_csv
        StringIO(tabela),  # Passa a string da tabela embrulhada em StringIO para simular um arquivo
        sep=";",  # Define ponto e vírgula como separador de colunas (padrão INMET)
        decimal=",",  # Define vírgula como separador decimal (padrão brasileiro)
        na_values=["", "-9999", "-9999,0", "null", "NULL"],  # Lista de valores que devem ser interpretados como NaN (ausentes)
    )  # Finaliza a leitura do CSV para o DataFrame
    df = df.dropna(axis=1, how="all")  # Remove colunas inteiramente vazias (comum pelo ";" extra no fim das linhas do INMET)

    ausentes = [nome for nome in COLUNAS_INTERNAS if nome not in df.columns]  # Lista quaisquer colunas obrigatórias que faltem no CSV
    if ausentes:  # Verifica se houve alguma coluna obrigatória ausente
        raise ValueError(f"Colunas obrigatórias ausentes: {', '.join(ausentes)}")  # Interrompe com erro informando quais colunas faltaram

    df = df.rename(columns=COLUNAS_INTERNAS)[list(COLUNAS_INTERNAS.values())]  # Renomeia as colunas e mantém apenas as definidas em COLUNAS_INTERNAS
    df["data"] = pd.to_datetime(df["data"], errors="coerce")  # Converte a coluna "data" para datetime (valores inválidos viram NaT)
    hora_texto = (  # Inicia a formatação da coluna numérica de hora para string com 4 dígitos (ex.: 0 -> "0000")
        df["hora"]  # Seleciona a coluna "hora"
        .astype("Int64")  # Converte para inteiro anulável do pandas (aceita valores ausentes)
        .astype(str)  # Converte os números para string
        .str.replace("<NA>", "", regex=False)  # Substitui a representação de nulo "<NA>" por string vazia
        .str.zfill(4)  # Preenche com zeros à esquerda até completar 4 caracteres (ex.: "100" -> "0100")
    )  # Finaliza a construção da série hora_texto
    df["data_hora"] = pd.to_datetime(  # Cria a coluna combinada de data e hora como Timestamp
        df["data"].dt.strftime("%Y-%m-%d")  # Formata a data como "AAAA-MM-DD"
        + " "  # Concatena um espaço separador
        + hora_texto.str[:2]  # Pega os dois primeiros dígitos (horas)
        + ":"  # Concatena dois-pontos
        + hora_texto.str[2:],  # Pega os dois últimos dígitos (minutos)
        errors="coerce",  # Converte falhas de parsing em NaT em vez de lançar exceção
    )  # Finaliza a criação da coluna "data_hora"

    numericas = ["precipitacao_mm", "temp_max_c", "temp_min_c"]  # Lista as colunas que devem ser numéricas
    for coluna in numericas:  # Itera por cada coluna numérica
        df[coluna] = pd.to_numeric(df[coluna], errors="coerce")  # Garante conversão para tipo numérico (erros viram NaN)

    df["hora_num"] = df["data_hora"].dt.hour  # Extrai a hora inteira (0 a 23) como coluna auxiliar para filtros
    df["mes"] = df["data_hora"].dt.month  # Extrai o número do mês (1 a 12) para agrupamentos mensais
    df["dia"] = df["data_hora"].dt.floor("D")  # Trunca "data_hora" para meia-noite do dia (agrupamento diário)
    df = df.sort_values("data_hora", na_position="last").reset_index(drop=True)  # Ordena cronologicamente (nulos no fim) e refaz o índice
    return StationDataset(metadata=metadata, data=df, source=source)  # Retorna o objeto StationDataset completo