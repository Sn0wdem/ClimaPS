# 📘 Dicionário Didático do Projeto ClimaPS

> **Objetivo deste documento:** explicar, de forma clara e acessível para estudantes e pesquisadores, como funciona o sistema **ClimaPS** — desde a lógica geral da arquitetura até o significado prático de cada termo de Python, biblioteca e função do projeto.

---

## 📑 Sumário

1. [Visão Geral do Sistema](#1-visão-geral-do-sistema)
2. [Arquitetura em Camadas (Como as Partes Conversam)](#2-arquitetura-em-camadas-como-as-partes-conversam)
3. [Fluxo dos Dados na Prática](#3-fluxo-dos-dados-na-prática)
4. [Conceitos Acadêmicos e de Ciência de Dados Aplicados](#4-conceitos-acadêmicos-e-de-ciência-de-dados-aplicados)
5. [Dicionário de Python Básico Usado no Código](#5-dicionário-de-python-básico-usado-no-código)
6. [Dicionário das Bibliotecas Externas](#6-dicionário-das-bibliotecas-externas)
7. [Dicionário dos Módulos e Funções do ClimaPS](#7-dicionário-dos-módulos-e-funções-do-climaps)

---

## 1. Visão Geral do Sistema

O **ClimaPS** é uma aplicação web em Python voltada para duas frentes:

1. **Monitoramento climático ao vivo (global):** consulta condições meteorológicas atuais de qualquer cidade ou coordenada do planeta via API pública *Open-Meteo* e exibe mapas interativos (*Plotly* e *Windy.com*).
2. **Análise de séries históricas (INMET):** importa arquivos horários de estações meteorológicas brasileiras, aplica filtros, audita a qualidade dos dados, gera gráficos, permite edição em tela e exporta os resultados em **CSV** ou **SQL**.

---

## 2. Arquitetura em Camadas (Como as Partes Conversam)

O projeto adota uma organização modular para separar **dados**, **cálculos** e **interface**:

| Camada | Arquivos | Papel no sistema (em termos simples) |
|---|---|---|
| **Ingestão de Dados** | `climaps/core/data_loader.py` e `weather_api.py` | Lê arquivos CSV do INMET ou busca dados na API e entrega tudo padronizado. |
| **Núcleo Analítico** | `climaps/core/analysis.py` | Executa filtros, médias, somas, correlações e auditoria de qualidade. |
| **Interface Visual** | `app_streamlit.py`, `ui_styles.py`, `ui_tabs.py`, `ui_world.py` | Desenha as abas, cartões, tabelas e gráficos no navegador. |
| **Validação** | `tests/test_analysis.py` | Testa automaticamente se os cálculos continuam exatos após alterações. |

---

## 3. Fluxo dos Dados na Prática

### 🔹 Caminho A — Consulta Ao Vivo (`🌍 Mundo Ao Vivo`)
1. O usuário digita o nome de uma cidade (ou informa latitude e longitude).
2. `search_city()` consulta a API de geocodificação para descobrir as coordenadas do local.
3. `fetch_current_point()` busca temperatura, sensação térmica, umidade, vento, pressão, chuva, índice UV e horários do sol.
4. O botão **"📥 Carregar 30 dias nas abas"** chama `fetch_live_weather()`, que baixa os últimos 30 dias horários daquela cidade e os converte para o **mesmo formato padrão do INMET** (`StationDataset`), habilitando todas as abas de análise histórica.

### 🔹 Caminho B — Análise de Arquivo CSV do INMET
1. O usuário envia um `.csv` pela barra lateral ou escolhe o arquivo de exemplo (`data/dados_A101_H_2014.csv`, com 8.760 horas de Manaus em 2014).
2. `load_station_csv()` separa o cabeçalho de metadados da tabela numérica, corrige o separador `;` e a vírgula decimal `,`, unifica data e hora em `data_hora` e cria colunas auxiliares (`hora_num`, `mes`, `dia`).
3. Os dados ficam salvos na memória da sessão (`st.session_state`), permitindo filtrar período, faixa horária e dias de chuva (`FilterSpec` + `apply_filters()`).
4. O usuário pode corrigir valores na aba **Tabela editável** e baixar a base em **CSV** ou script **SQL** na aba **Exportar**.

---

## 4. Conceitos Acadêmicos e de Ciência de Dados Aplicados

| Conceito | Explicação simples | Onde aparece no projeto |
|---|---|---|
| **ETL (Extração, Transformação e Carga)** | Processo de pegar dados brutos/heterogêneos (CSV do INMET ou JSON da API), limpar e padronizar em uma única estrutura confiável. | `data_loader.py` e `weather_api.py` |
| **Esquema Unificado (Adapter)** | Tanto o CSV quanto a API da Open-Meteo produzem um objeto `StationDataset` idêntico, evitando duplicar o código das abas analíticas. | `StationDataset` |
| **Qualidade de Dados (*Data Quality*)** | Auditoria para achar falhas antes de concluir análises: lacunas de horário, duplicatas, nulos, chuva negativa e $T_{\max} < T_{\min}$. | `quality_report()` |
| **Detecção de Outliers por IQR** | Método estatístico baseado em quartis ($Q_1$ e $Q_3$). Valores muito distantes do miolo dos dados ($1{,}5 \times \text{IQR}$) são contados como discrepantes. | `_iqr_outlier_count()` |
| **Correlação de Pearson** | Mede, de $-1$ a $+1$, a relação linear entre chuva, temperatura máxima e temperatura mínima. | `correlation_matrix()` |
| **Cache com TTL** | Guarda temporariamente respostas da internet por 5 minutos (`ttl=300`), evitando lentidão e excesso de requisições à API. | `@st.cache_data` em `ui_world.py` |
| **Testes Unitários** | Conjunto de verificações automáticas que garantem reprodutibilidade matemática dos resultados (ex.: total de chuva e mês mais chuvoso de 2014). | `tests/test_analysis.py` |

---

## 5. Dicionário de Python Básico Usado no Código

| Termo / Recurso | O que significa de forma simples | Exemplo prático no projeto |
|---|---|---|
| `import` / `from ... import` | Traz ferramentas prontas de outros arquivos ou bibliotecas para uso no script atual. | `import pandas as pd` |
| `def funcao():` | Cria um bloco de código reutilizável com nome próprio (uma função). | `def calculate_kpis(df):` |
| `class` / `@dataclass` | Cria um molde de objeto para agrupar dados relacionados de forma organizada e imutável (`frozen=True`). | `StationDataset`, `FilterSpec` |
| `if` / `elif` / `else` | Toma decisões lógicas conforme uma condição seja verdadeira ou falsa. | `if filtered.empty:` |
| `for ... in ...` | Repete uma ação para cada item de uma lista ou coluna. | `for coluna in numericas:` |
| `try ... except` | Tenta rodar um trecho arriscado (ex.: conexão com internet) e trata o erro sem travar o programa. | Consultas à Open-Meteo em `ui_world.py` |
| `with` | Abre um contexto visual ou de formulário e fecha automaticamente ao terminar. | `with st.sidebar:`, `with st.form(...):` |
| `lambda` | Função curta escrita em uma única linha, útil para formatar textos de menus. | `lambda p: f"{p.parent.name}/{p.name}"` |
| `f"texto {var}"` (*f-string*) | Permite misturar texto fixo com variáveis e formatar casas decimais (`:.1f`) ou datas (`:%d/%m/%Y`). | `f"{kpis['precipitacao_total']:.1f} mm"` |
| `list` (`[...]`) | Lista ordenada de itens que pode crescer ou mudar. | `WORLD_DEFAULTS`, `insights` |
| `dict` (`{chave: valor}`) | Tabela de consulta rápida que liga uma chave a um valor (como um dicionário real). | `MESES_PT`, `WMO_CODES_PT` |
| `tuple` (`(...)`) | Lista fixa/imutável, usada para retornar pares de datas ou coordenadas. | `(-3.10, -60.02)` |
| `set` (`{...}`) | Conjunto sem itens repetidos, ideal para checar rapidamente se algo está incluído. | `{"data", "dia"}` |
| `None` / `True` / `False` | `None` representa ausência de valor; `True` e `False` representam verdadeiro e falso. | `rainy_only: bool = False` |
| `Path` (`pathlib`) | Forma moderna e segura de lidar com pastas e arquivos sem se preocupar com `/` ou `\`. | `DATA_DIR / "dados_A101_H_2014.csv"` |

---

## 6. Dicionário das Bibliotecas Externas

| Biblioteca | Para que serve no projeto | Principais comandos usados |
|---|---|---|
| **Pandas (`pd`)** | Coração da manipulação tabular: lê CSVs, trata datas, filtra linhas, agrupa meses/dias e calcula estatísticas. | `pd.read_csv`, `pd.to_datetime`, `pd.to_numeric`, `.groupby()`, `.agg()`, `.loc[]`, `.corr()`, `.to_csv()` |
| **NumPy (`np`)** | Suporte numérico de baixo nível usado junto ao Pandas para tratar infinitos e valores nulos. | `np.inf`, `np.nan` |
| **Requests** | Faz chamadas HTTP na internet para buscar cidades e previsões na API Open-Meteo. | `requests.get()`, `.raise_for_status()`, `.json()` |
| **Plotly (`px`, `go`)** | Gera gráficos interativos (barras de chuva, amplitude térmica preenchida, heatmap de correlação e mapa mundial). | `px.bar`, `go.Figure`, `go.Scatter`, `px.imshow`, `px.scatter_geo` |
| **Streamlit (`st`)** | Transforma o código Python em um aplicativo web interativo com abas, barra lateral, filtros e botões de download. | `st.tabs`, `st.sidebar`, `st.metric`, `st.dataframe`, `st.data_editor`, `st.session_state`, `st.download_button` |

---

## 7. Dicionário dos Módulos e Funções do ClimaPS

### 📂 `climaps/core/data_loader.py` — Leitura do CSV do INMET
- **`COLUNAS_INTERNAS`**: mapa que traduz os nomes extensos das colunas do INMET para nomes curtos (`data`, `hora`, `precipitacao_mm`, `temp_max_c`, `temp_min_c`).
- **`StationDataset`**: pacote imutável que guarda os metadados da estação (`metadata`), a tabela limpa (`data`) e o arquivo de origem (`source`).
- **`_normalizar_chave()`**: limpa os nomes das informações de cabeçalho (ex.: `"Codigo Estacao"` vira `"codigo_estacao"`).
- **`_localizar_cabecalho()`**: descobre em qual linha termina o texto informativo do INMET e começa a tabela de medições.
- **`load_station_csv()`**: executa toda a leitura, limpeza, conversão numérica e criação da coluna `data_hora`.

### 📂 `climaps/core/analysis.py` — Regras Analíticas e Estatística
- **`MESES_PT`**: traduz números de `1` a `12` para `"Jan"` até `"Dez"`.
- **`FilterSpec`**: guarda os filtros escolhidos na barra lateral (data inicial, data final, faixa de hora e filtro de chuva).
- **`apply_filters()`**: recorta o DataFrame mantendo apenas as linhas que atendem ao `FilterSpec`.
- **`calculate_kpis()`**: calcula os 5 indicadores principais (registros, chuva acumulada, médias de máxima/mínima e % de completude).
- **`monthly_summary()` / `daily_summary()`**: agrupam os dados horários por mês ou por dia.
- **`_iqr_outlier_count()`**: conta valores estatisticamente discrepantes pelo critério do Intervalo Interquartil.
- **`quality_report()`**: gera o diagnóstico de qualidade da base (buracos na série horária, duplicados, nulos, outliers e erros físicos).
- **`generate_insights()`**: escreve frases automáticas destacando o mês mais chuvoso, o mês mais quente, o maior pico horário de chuva e a quantidade de dias secos.
- **`correlation_matrix()`**: calcula a matriz de correlação 3×3 entre chuva, temperatura máxima e mínima.
- **`calculate_dew_point()`**: calcula o Ponto de Orvalho (*Dew Point*) pela fórmula de Magnus-Tetens, medindo o abafamento e a umidade real do ar.
- **`calculate_heat_index()`**: calcula o Índice de Calor (*Heat Index*) de Steadman/NOAA e classifica o risco de desconforto térmico, fadiga ou insolação.
- **`evaluate_storm_risk()`**: gatilho barométrico que detecta queda brusca de pressão (< 1005 hPa) associada a alta umidade e rajadas de vento, emitindo alertas visuais de tempestade.
- **`calculate_climate_anomaly()`**: cruza os dados ao vivo da Open-Meteo com a série histórica do INMET carregada na sessão, medindo o desvio de temperatura e chuva frente à média do mês.
- **`classify_air_quality()`**: classifica o índice de qualidade do ar (*US AQI*) e material particulado fino (*PM2.5* e *PM10*), com foco no monitoramento de fumaça de queimadas.
- **`classify_uv()`**: categoriza a radiação ultravioleta diária de acordo com as faixas de proteção da OMS.

### 📂 `climaps/core/weather_api.py` — Conexão com a Open-Meteo
- **`GEOCODING_URL` / `FORECAST_URL` / `AIR_QUALITY_URL`**: endereços públicos das APIs de previsão, geocodificação e qualidade do ar da Open-Meteo.
- **`WMO_CODES_PT`**: traduz códigos meteorológicos internacionais (WMO) para descrições com emojis em português.
- **`LiveWeatherBundle`**: estrutura que reúne condições atuais, previsão diária e série horária recente (`StationDataset`).
- **`weather_description()`**: converte um código numérico WMO em texto amigável.
- **`search_city()`**: busca cidades pelo nome e retorna opções com latitude e longitude.
- **`fetch_air_quality()`**: consulta concentrações de PM2.5, PM10, CO, NO2 e ozônio na API de qualidade do ar.
- **`_parse_point_payload()`**: organiza a resposta JSON da API em um dicionário padronizado em português, calculando índices derivados e estruturando as previsões horária e diária.
- **`fetch_current_point()` / `fetch_multiple_points()`**: buscam o clima atual de um local ou de várias cidades em lote.
- **`fetch_live_weather()`**: baixa clima atual, previsão de 7 dias e últimos 30 dias horários prontos para análise nas abas.

### 📂 `climaps/ui_styles.py`, `ui_tabs.py` e `ui_world.py` — Interface Gráfica
- **`NAVY` / `BLUE` / `ORANGE`**: cores principais da identidade visual do painel.
- **`br_number()`**: formata números para o padrão brasileiro (ponto para milhar e vírgula para decimal).
- **`inject_custom_css()` / `render_header()`**: aplicam o visual CSS personalizado e o banner superior dinâmico.
- **`render_summary_tab()` / `render_charts_tab()` / `render_table_tab()` / `render_explorer_tab()`**: desenham as abas *Resumo*, *Gráficos*, *Tabela editável* e *Explorador*.
- **`WORLD_DEFAULTS`**: lista das 10 cidades globais carregadas por padrão no mapa comparativo.
- **`cached_search_city()` / `cached_current_point()` / `cached_world_defaults()`**: versões com cache de 5 minutos das chamadas à API.
- **`render_world_live_tab()`**: monta toda a aba *Mundo Ao Vivo* (busca, cartão principal, mapa Plotly/Windy, pódio de extremos e tabela comparativa).

### 📂 `app_streamlit.py` e `tests/test_analysis.py` — Orquestração e Testes
- **`BASE_DIR` / `DATA_DIR` / `IMPORT_DIR` / `EXPORT_DIR` / `SAMPLE_CSV`**: definem os caminhos das pastas do projeto e do CSV de exemplo.
- **`safe_filename()`**: limpa nomes de arquivos enviados pelo usuário para evitar caracteres inválidos.
- **`sql_value()` / `build_sql_script()`**: transformam a tabela em comandos SQL (`DROP TABLE`, `CREATE TABLE` e `INSERT INTO`).
- **`load_into_session()`**: grava o dataset carregado na memória da sessão (`st.session_state`).
- **`render_sidebar()` / `render_export_tab()` / `main()`**: organizam barra lateral, exportação e criação das 6 abas principais.
- **`StationAnalysisTests` e `FormattingAndUiTests`**: suíte completa de 14 testes automatizados que validam metadados, integridade das 8.760 horas, nulos, KPIs, mês mais chuvoso (março), filtros, regras de qualidade, formatação de datas, ponto de orvalho, índice de calor, risco de tempestade e anomalias climáticas.
