from datetime import datetime  # Usado para gerar carimbos de data/hora ao salvar arquivos importados e exportados
from pathlib import Path  # Manipulação multiplataforma de diretórios e arquivos
import re  # Expressões regulares para sanitizar nomes de arquivos enviados pelo usuário

import pandas as pd  # Manipulação de DataFrames e timestamps
import streamlit as st  # Framework principal da aplicação web

from climaps.core.analysis import FilterSpec, apply_filters  # Estrutura de filtro e função que filtra o DataFrame
from climaps.core.data_loader import StationDataset, load_station_csv  # Leitor de CSVs do INMET e tipo StationDataset
from climaps.ui_styles import inject_custom_css, render_header  # Estilização CSS e renderização do banner superior
from climaps.ui_tabs import (  # Funções que renderizam as abas de análise histórica
    render_charts_tab,  # Aba de gráficos
    render_explorer_tab,  # Aba de tabela filtrada
    render_summary_tab,  # Aba de resumo, KPIs e qualidade
    render_table_tab,  # Aba de editor de dados
)  # Fecha importação de ui_tabs
from climaps.ui_world import render_world_live_tab  # Função que renderiza a aba Mundo Ao Vivo


BASE_DIR = Path(__file__).resolve().parent  # Pasta raiz do projeto (onde está o app_streamlit.py)
DATA_DIR = BASE_DIR / "data"  # Subpasta data/
IMPORT_DIR = DATA_DIR / "importados"  # Subpasta data/importados/ onde ficam os CSVs enviados pela interface
EXPORT_DIR = BASE_DIR / "exportacoes"  # Subpasta exportacoes/ para cópias locais de CSV e SQL
SAMPLE_CSV = DATA_DIR / "dados_A101_H_2014.csv"  # Caminho do dataset de exemplo (Manaus A101 - 2014)


def safe_filename(name: str) -> str:  # Limpa o nome de um arquivo enviado para evitar caracteres inválidos ou path traversal
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", Path(name).name).strip("._")  # Pega só o nome do arquivo, troca chars especiais por "_" e limpa pontas
    return safe or "dados.csv"  # Retorna o nome seguro ou "dados.csv" caso fique vazio


def sql_value(value, is_date_only: bool = False) -> str:  # Converte um valor Python/pandas para literal SQL válido
    if pd.isna(value):  # Se for NaN, NaT ou None
        return "NULL"  # Retorna a palavra-chave SQL NULL
    if isinstance(value, pd.Timestamp):  # Se for um Timestamp do pandas
        fmt = "%Y-%m-%d" if is_date_only else "%Y-%m-%d %H:%M:%S"  # Escolhe formato só de data ou data + hora
        return f"'{value.strftime(fmt)}'"  # Retorna string entre aspas simples no padrão ISO
    if hasattr(value, "strftime"):  # Se for outro objeto date/datetime do Python
        return f"'{value:%Y-%m-%d}'"  # Formata como data ISO entre aspas simples
    if isinstance(value, str):  # Se for texto
        return "'" + value.replace("'", "''") + "'"  # Escapa aspas simples internas duplicando-as e envolve em aspas
    return str(float(value)) if isinstance(value, float) else str(value)  # Converte float/int para string numérica sem aspas


def build_sql_script(df: pd.DataFrame) -> str:  # Gera o script SQL completo (DROP, CREATE TABLE e INSERTs) a partir do DataFrame
    columns = [  # Lista ordenada das 9 colunas que compõem a tabela SQL
        "data",  # Data da medição
        "hora",  # Hora no padrão inteiro INMET
        "data_hora",  # Timestamp completo
        "precipitacao_mm",  # Precipitação (mm)
        "temp_max_c",  # Temperatura máxima (°C)
        "temp_min_c",  # Temperatura mínima (°C)
        "hora_num",  # Hora numérica (0..23)
        "mes",  # Mês (1..12)
        "dia",  # Dia truncado
    ]  # Fecha lista de colunas
    sql_lines = [  # Começa a lista de linhas do arquivo .sql com o DDL da tabela
        "DROP TABLE IF EXISTS observacoes_meteorologicas;",  # Remove a tabela anterior se já existir
        "CREATE TABLE observacoes_meteorologicas (",  # Inicia definição da tabela
        "    data DATE,",  # Coluna data do tipo DATE
        "    hora INTEGER,",  # Coluna hora do tipo INTEGER
        "    data_hora TIMESTAMP,",  # Coluna data_hora do tipo TIMESTAMP
        "    precipitacao_mm REAL,",  # Coluna precipitacao_mm do tipo REAL
        "    temp_max_c REAL,",  # Coluna temp_max_c do tipo REAL
        "    temp_min_c REAL,",  # Coluna temp_min_c do tipo REAL
        "    hora_num INTEGER,",  # Coluna hora_num do tipo INTEGER
        "    mes INTEGER,",  # Coluna mes do tipo INTEGER
        "    dia DATE",  # Coluna dia do tipo DATE
        ");",  # Fecha CREATE TABLE
        "",  # Linha em branco separando DDL dos INSERTs
    ]  # Fecha cabeçalho SQL
    for _, row in df[columns].iterrows():  # Itera sobre cada linha do DataFrame nas colunas definidas
        values = ", ".join(  # Junta todos os valores da linha separados por vírgula
            sql_value(row[col], is_date_only=(col in {"data", "dia"})) for col in columns  # Formata cada célula (data/dia sem horário)
        )  # Fecha join de valores
        sql_lines.append(  # Adiciona a instrução INSERT correspondente à linha
            f"INSERT INTO observacoes_meteorologicas ({', '.join(columns)}) VALUES ({values});"  # Comando INSERT completo
        )  # Fecha append
    return "\n".join(sql_lines) + "\n"  # Junta todas as linhas com quebra de linha final e retorna o script


def load_into_session(path: Path) -> None:  # Carrega um arquivo CSV do disco para o estado de sessão do Streamlit
    dataset: StationDataset = load_station_csv(path)  # Lê e normaliza o CSV usando data_loader
    st.session_state["dataset"] = dataset  # Armazena o objeto StationDataset completo na sessão
    st.session_state["df"] = dataset.data.copy()  # Armazena uma cópia editável do DataFrame na sessão


def render_sidebar() -> FilterSpec | None:  # Renderiza a barra lateral (upload, seleção de arquivos e filtros)
    with st.sidebar:  # Entra no contexto da barra lateral
        st.header("📂 Dados históricos (CSV)")  # Título da seção de carregamento
        uploaded = st.file_uploader("Importar CSV do INMET", type=["csv"])  # Componente de upload aceitando apenas .csv
        if uploaded is not None:  # Se o usuário enviou um arquivo
            sig = (uploaded.name, uploaded.size)  # Cria assinatura (nome, tamanho) para não reprocessar o mesmo upload a cada rerun
            if st.session_state.get("last_upload_sig") != sig:  # Só importa se for um arquivo novo/diferente
                IMPORT_DIR.mkdir(parents=True, exist_ok=True)  # Garante que data/importados/ exista
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # Gera carimbo de data/hora para evitar sobrescrever arquivos
                dest = IMPORT_DIR / f"{stamp}_{safe_filename(uploaded.name)}"  # Define caminho final seguro do arquivo salvo
                dest.write_bytes(uploaded.getvalue())  # Grava os bytes do arquivo enviado no disco
                load_into_session(dest)  # Carrega o CSV recém-salvo na sessão
                st.session_state["last_upload_sig"] = sig  # Registra assinatura para evitar reimportação repetida
                st.toast(f"Arquivo importado: {dest.name}", icon="✅")  # Exibe notificação de sucesso

        available_files: list[Path] = []  # Lista de arquivos CSV já disponíveis localmente
        if SAMPLE_CSV.exists():  # Se o CSV de exemplo existir
            available_files.append(SAMPLE_CSV)  # Adiciona o arquivo de exemplo à lista
        if IMPORT_DIR.exists():  # Se a pasta de importados existir
            available_files.extend(sorted(IMPORT_DIR.glob("*.csv"), reverse=True))  # Adiciona CSVs importados do mais recente ao mais antigo

        if available_files:  # Se houver ao menos um arquivo local disponível
            chosen = st.selectbox(  # Caixa de seleção para escolher um arquivo salvo
                "Ou carregar arquivo salvo",  # Rótulo do selectbox
                options=available_files,  # Lista de objetos Path
                format_func=lambda p: f"{p.parent.name}/{p.name}",  # Exibe no formato "pasta/arquivo.csv"
            )  # Fecha selectbox
            if st.button("Carregar arquivo selecionado", width="stretch"):  # Botão para confirmar o carregamento do arquivo escolhido
                load_into_session(chosen)  # Carrega o arquivo escolhido na sessão
                st.rerun()  # Recarrega a página para atualizar cabeçalho, filtros e abas

        df: pd.DataFrame | None = st.session_state.get("df")  # Recupera o DataFrame ativo da sessão
        if df is None or df.empty:  # Se ainda não houver dados carregados
            return None  # Não renderiza filtros e retorna None

        st.divider()  # Linha divisória separando carregamento de arquivos e filtros
        st.header("🎛️ Filtros de análise")  # Título da seção de filtros

        valid_dt = df["data_hora"].dropna()  # Obtém todos os timestamps válidos do DataFrame ativo
        min_date = valid_dt.min().date()  # Menor data disponível (limite inferior do seletor)
        max_date = valid_dt.max().date()  # Maior data disponível (limite superior do seletor)

        date_range = st.date_input(  # Seletor de intervalo de datas
            "Período",  # Rótulo
            value=(min_date, max_date),  # Inicia selecionando todo o período disponível
            min_value=min_date,  # Data mínima permitida
            max_value=max_date,  # Data máxima permitida
            key=f"period_{min_date}_{max_date}",  # Chave dinâmica para resetar o widget quando uma nova base é carregada
        )  # Fecha st.date_input
        if isinstance(date_range, tuple) and len(date_range) == 2:  # Se o usuário selecionou início e fim (tupla com 2 datas)
            start_d, end_d = date_range  # Desempacota início e fim
        else:  # Se o usuário ainda selecionou apenas 1 data intermediária
            start_d = end_d = date_range[0] if isinstance(date_range, tuple) else date_range  # Usa a mesma data para início e fim

        hour_start, hour_end = st.slider("Faixa de horário", 0, 23, (0, 23))  # Slider duplo para filtrar faixa de horas (0h a 23h)
        rainy_only = st.checkbox("Somente horas com chuva", value=False)  # Checkbox para filtrar apenas registros com precipitação > 0

        return FilterSpec(  # Cria e retorna a especificação de filtro montada
            start=pd.Timestamp(start_d),  # Converte data inicial para Timestamp
            end=pd.Timestamp(end_d),  # Converte data final para Timestamp
            hour_start=hour_start,  # Hora inicial selecionada
            hour_end=hour_end,  # Hora final selecionada
            rainy_only=rainy_only,  # Flag de filtro de chuva
        )  # Fecha retorno FilterSpec


def render_export_tab(full_df: pd.DataFrame, filtered: pd.DataFrame) -> None:  # Renderiza a aba "⬇️ Exportar"
    scope = st.radio(  # Seletor do escopo dos dados a exportar
        "Dados para exportação",  # Rótulo
        ["Base completa (com edições)", "Apenas recorte filtrado"],  # Opções
        horizontal=True,  # Lado a lado
    )  # Fecha st.radio
    target_df = full_df if scope.startswith("Base") else filtered  # Escolhe base inteira ou apenas os dados filtrados
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # Carimbo de data/hora para nomear os arquivos exportados

    csv_bytes = target_df.to_csv(  # Serializa o DataFrame alvo para CSV em memória
        sep=";",  # Separador ponto e vírgula (padrão Excel PT-BR)
        decimal=",",  # Separador decimal vírgula
        index=False,  # Não exporta a coluna de índice do pandas
        date_format="%Y-%m-%d %H:%M",  # Formata datas/horas de forma legível
    ).encode("utf-8-sig")  # Codifica com BOM UTF-8 para abrir com acentuação correta no Excel

    sql_text = build_sql_script(target_df)  # Gera o script SQL completo do DataFrame alvo

    col1, col2 = st.columns(2)  # Duas colunas para os botões de download
    with col1:  # Coluna esquerda: download de CSV
        st.download_button(  # Botão de download do navegador para o CSV
            "⬇️ Baixar CSV",  # Texto do botão
            data=csv_bytes,  # Conteúdo em bytes
            file_name=f"climaps_dados_{stamp}.csv",  # Nome sugerido ao baixar
            mime="text/csv",  # Tipo MIME
            width="stretch",  # Ocupa toda a largura da coluna
        )  # Fecha download_button CSV
    with col2:  # Coluna direita: download de SQL
        st.download_button(  # Botão de download do navegador para o script SQL
            "🗄️ Baixar Script SQL",  # Texto do botão
            data=sql_text.encode("utf-8"),  # Script SQL codificado em UTF-8
            file_name=f"climaps_dados_{stamp}.sql",  # Nome sugerido ao baixar
            mime="application/sql",  # Tipo MIME
            width="stretch",  # Ocupa toda a largura da coluna
        )  # Fecha download_button SQL

    if st.button("Salvar cópias também na pasta exportacoes/"):  # Botão opcional para gravar cópias no servidor/disco local
        EXPORT_DIR.mkdir(exist_ok=True)  # Cria a pasta exportacoes/ se ainda não existir
        csv_path = EXPORT_DIR / f"dados_editados_{stamp}.csv"  # Caminho do CSV local
        sql_path = EXPORT_DIR / f"dados_meteorologicos_{stamp}.sql"  # Caminho do SQL local
        csv_path.write_bytes(csv_bytes)  # Salva o CSV no disco
        sql_path.write_text(sql_text, encoding="utf-8")  # Salva o SQL no disco
        st.success(f"Arquivos salvos em `exportacoes/`: `{csv_path.name}` e `{sql_path.name}`.")  # Confirma os nomes salvos


def main() -> None:  # Função principal que organiza todo o ciclo de execução do app Streamlit
    st.set_page_config(  # Configura metadados da aba do navegador e layout da página (deve ser a primeira chamada Streamlit)
        page_title="ClimaPS - Dados Meteorológicos",  # Título na aba do navegador
        page_icon="☁️",  # Ícone (favicon) da aba
        layout="wide",  # Usa largura total da tela
    )  # Fecha st.set_page_config
    inject_custom_css()  # Injeta os estilos CSS personalizados
    render_header()  # Desenha o banner superior
    filter_spec = render_sidebar()  # Renderiza barra lateral e captura os filtros (ou None se sem base)

    df: pd.DataFrame | None = st.session_state.get("df")  # Recupera DataFrame ativo da sessão
    has_dataset = df is not None and not df.empty and filter_spec is not None  # Verifica se há dataset válido e filtro pronto

    tab_mundo, tab_resumo, tab_graficos, tab_tabela, tab_explorador, tab_exportar = st.tabs(  # Cria as 6 abas principais do app
        ["🌍 Mundo Ao Vivo", "📊 Resumo", "📈 Gráficos", "✏️ Tabela editável", "🔍 Explorador", "⬇️ Exportar"]  # Rótulos das abas
    )  # Fecha st.tabs

    with tab_mundo:  # Conteúdo da primeira aba (funciona sempre, mesmo sem CSV)
        render_world_live_tab()  # Renderiza consultas ao vivo, mapas e tabela global

    if has_dataset:  # Se já existir uma base histórica carregada (via CSV ou botão de 30 dias)
        filtered = apply_filters(df, filter_spec)  # Aplica os filtros da barra lateral sobre o DataFrame da sessão
        with tab_resumo:  # Aba Resumo
            render_summary_tab(filtered, df)  # Renderiza KPIs, insights, resumo mensal e qualidade
        with tab_graficos:  # Aba Gráficos
            render_charts_tab(filtered)  # Renderiza gráficos de chuva, temperatura e correlação
        with tab_tabela:  # Aba Tabela editável
            render_table_tab(df)  # Renderiza editor da base completa da sessão
        with tab_explorador:  # Aba Explorador
            render_explorer_tab(filtered)  # Renderiza tabela filtrada somente leitura
        with tab_exportar:  # Aba Exportar
            render_export_tab(df, filtered)  # Renderiza opções de exportação CSV e SQL
    else:  # Se ainda não houver base histórica carregada na sessão
        for tab in (tab_resumo, tab_graficos, tab_tabela, tab_explorador, tab_exportar):  # Percorre as 5 abas dependentes de dataset
            with tab:  # Entra em cada aba
                st.info("Importe um CSV na barra lateral ou clique em **Carregar 30 dias nas abas** na aba Mundo Ao Vivo.")  # Orienta o usuário


if __name__ == "__main__":  # Garante que main() seja executada apenas quando este script for rodado diretamente
    main()  # Inicia a aplicação