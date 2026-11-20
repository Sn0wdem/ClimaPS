# 📘 Dicionário Didático do Projeto ClimaPS

> **Objetivo deste documento:** explicar, de forma clara, aprofundada e acessível para estudantes, desenvolvedores e pesquisadores, o funcionamento integral do sistema **ClimaPS** — desde a arquitetura de software e fluxos de dados até os conceitos meteorológicos, estatísticos e de código aplicados no projeto.

---

## 📑 Sumário

1. [Visão Geral do Sistema](#1-visão-geral-do-sistema)
2. [Arquitetura em Camadas (Como as Partes Conversam)](#2-arquitetura-em-camadas-como-as-partes-conversam)
3. [Fluxo dos Dados na Prática](#3-fluxo-dos-dados-na-prática)
4. [Conceitos Acadêmicos e de Ciência de Dados Aplicados](#4-conceitos-acadêmicos-e-de-ciência-de-dados-aplicados)
5. [Dicionário de Python Básico e Avançado Usado no Código](#5-dicionário-de-python-básico-e-avançado-usado-no-código)
6. [Dicionário das Bibliotecas Externas](#6-dicionário-das-bibliotecas-externas)
7. [Dicionário Completo dos Módulos e Funções do ClimaPS](#7-dicionário-completo-dos-módulos-e-funções-do-climaps)
8. [Suíte de Testes Automatizados e Garantia de Qualidade](#8-suíte-de-testes-automatizados-e-garantia-de-qualidade)

---

## 1. Visão Geral do Sistema

O **ClimaPS** é uma plataforma analítica e de monitoramento meteorológico desenvolvida em **Python** e **Streamlit**, desenhada para atender a três grandes propósitos:

1. **Monitoramento Climático Global em Tempo Real (`🌍 Mundo Ao Vivo`):**
   - Consulta instantânea de qualquer cidade ou coordenada (`Latitude` / `Longitude`) do mundo sem necessidade de chave de API.
   - Cálculo de índices bioclimáticos em tempo real: **Ponto de Orvalho (*Dew Point*)**, **Índice de Calor (*Heat Index*)**, **Risco Barométrico de Tempestade** e **Qualidade do Ar (*US AQI*, PM2.5, PM10, CO)**.
   - **Calendário Histórico:** consulta de telemetria completa de qualquer dia da história recente humana (reanálise global ERA5).
   - **Gerador de Datasets Anuais:** download e geração de bases completas de 1 ano (8.760 horas) no mesmo formato padrão do INMET para qualquer ponto do globo.
   - **Radar Animado ao Vivo:** integração direta com o radar meteorológico global do Windy.com.

2. **Comparação Interanual e de Séries Temporais (`⚖️ Comparação entre Anos`):**
   - Comparação lado a lado de dois arquivos CSV (Ano A vs. Ano B) ou de duas estações meteorológicas distintas.
   - Confronto direto de chuva anual, temperaturas médias, anomalias térmicas e dias secos/chuvosos.
   - Gráficos interativos com deltas de precipitação mês a mês e amplitudes térmicas sobrepostas.

3. **Análise Forense e Exploração de Séries Históricas do INMET:**
   - Ingestão universal de arquivos de estações convencionais e automáticas do **INMET** e de arquivos exportados pelo próprio ClimaPS.
   - Filtros dinâmicos por período, horário e dias chuvosos.
   - Auditoria rigorosa de qualidade de dados (*Data Quality Report*), detecção de *outliers* pelo método IQR e matriz de correlação de Pearson.
   - Edição interativa de registros na sessão e exportação em **CSV** ou scripts **SQL** (`CREATE TABLE` + `INSERT INTO`).

---

## 2. Arquitetura em Camadas (Como as Partes Conversam)

O projeto adota os princípios de **Clean Architecture** e **Separation of Concerns (SoC)**, mantendo regras matemáticas, acesso a dados e interface visual estritamente desacoplados:

| Camada | Módulos | Papel no sistema |
|---|---|---|
| **Ingestão & Conectores (Data Layer)** | `climaps/core/data_loader.py`<br>`climaps/core/weather_api.py` | Lê CSVs (INMET ou exportados), faz requisições HTTP REST à Open-Meteo (tempo real, ERA5, qualidade do ar), normaliza esquemas e converte em objetos unificados `StationDataset`. |
| **Núcleo Analítico (Domain / Core)** | `climaps/core/analysis.py` | Executa cálculos de física atmosférica (Magnus-Tetens, Steadman/NOAA), avaliação barométrica de tempestades, anomalias climáticas, estatísticas descritivas (KPIs, médias, somas), auditoria de dados e correlação de Pearson. |
| **Apresentação & UI (Interface)** | `app_streamlit.py`<br>`climaps/ui_world.py`<br>`climaps/ui_comparison.py`<br>`climaps/ui_tabs.py`<br>`climaps/ui_styles.py` | Constrói as 7 abas da aplicação, orquestra formulários e inputs, gera gráficos interativos com Plotly, gerencia o tema Dark/Light e estiliza a experiência do usuário com CSS avançado. |
| **Garantia de Qualidade (Tests)** | `tests/test_analysis.py`<br>`tests/test_ui_and_formatting.py` | 20 testes unitários automatizados cobrindo cálculos meteorológicos, ingestão de dados, streams de memória, cálculos de anomalia e integridade de séries temporais. |

---

## 3. Fluxo dos Dados na Prática

### 🔹 Caminho A — Monitoramento Global & Clima Ao Vivo (`🌍 Mundo Ao Vivo`)
1. O usuário digita uma cidade (ex.: `"Manaus"`) ou coordenadas geográficas.
2. `search_city()` consulta o serviço de geocodificação da Open-Meteo e retorna coordenadas e elevação.
3. `fetch_current_point()` busca o pacote completo de telemetria atual (temperatura, umidade, vento, pressão barométrica, índice UV, horários de nascer/pôr do sol e qualidade do ar).
4. `calculate_dew_point()`, `calculate_heat_index()` e `evaluate_storm_risk()` processam as medições físicas instantâneas, categorizando o conforto humano e eventuais alertas meteorológicos.
5. Se uma estação histórica estiver carregada na sessão, `calculate_climate_anomaly()` compara a medição atual com a média histórica do mês correspondente, informando se o dia está atipicamente mais quente ou mais frio.
6. O radar animado do **Windy.com** exibe o deslocamento em tempo real de massas de ar e precipitação.

### 🔹 Caminho B — Calendário Histórico & Datasets Anuais Globais (8.760h)
1. **Consulta por Calendário:** O usuário escolhe qualquer data no passado. `fetch_historical_day()` consulta o modelo de reanálise ERA5, retornando a curva térmica horária de 24h, precipitação, ventos e pressão de qualquer dia da história.
2. **Geração de 1 Ano Completo:** O usuário seleciona um ano (ex.: 2023) para a coordenada escolhida. `fetch_annual_dataset()` faz o download de 8.760 horas, calcula todas as variáveis, gera um arquivo CSV padronizado idêntico ao INMET e o salva automaticamente em `data/importados/`.
3. Com um único clique, o dataset gerado é carregado na sessão do aplicativo, permitindo que qualquer lugar do planeta passe por todas as análises históricas.

### 🔹 Caminho C — Comparação Interanual (`⚖️ Comparação entre Anos`)
1. O usuário seleciona ou faz o upload de dois arquivos CSV diferentes (ex.: Ano 2014 vs. Ano 2023).
2. `_carregar_dataset_ou_erro()` normaliza ambos os conjuntos de dados via `load_station_csv()`.
3. `_extrair_metricas_anuais()` calcula os totais de chuva, temperaturas médias, dias chuvosos e extremos de cada ano.
4. `_construir_tabela_mensal()` gera uma matriz cruzada comparando mês a mês a precipitação e temperatura, calculando variações absolutas e percentuais.
5. Gráficos Plotly sobrepostos exibem a curva de amplitude térmica simultânea dos dois anos e o gráfico de barras comparativo de chuva com indicação de deltas.

### 🔹 Caminho D — Análise Forense de Séries do INMET
1. O usuário envia um arquivo CSV do INMET ou seleciona o arquivo base (`dados_A101_H_2014.csv`).
2. `load_station_csv()` identifica automaticamente o padrão de cabeçalho, trata separadores `;` ou `,`, normaliza decimais e cria colunas temporais estruturadas (`data_hora`, `mes`, `hora_num`).
3. O usuário define filtros na barra lateral (`FilterSpec`), e `apply_filters()` fatia o DataFrame dinamicamente.
4. As abas **Resumo**, **Gráficos** e **Explorador** atualizam instantaneamente seus KPIs, gráficos e relatórios de qualidade.
5. Edições feitas na **Tabela editável** persistem no `st.session_state` e podem ser exportadas como novo CSV ou script SQL.

---

## 4. Conceitos Acadêmicos e de Ciência de Dados Aplicados

| Conceito | O que significa na prática | Onde atua no ClimaPS |
|---|---|---|
| **Ponto de Orvalho (*Dew Point*)** | Temperatura na qual o vapor d'água no ar condensa em líquido. É a medida mais confiável da umidade absoluta e sensação de abafamento. Calculado pela aproximação física de Magnus-Tetens ($a=17.27, b=237.7$). | `calculate_dew_point()` em `analysis.py` |
| **Índice de Calor (*Heat Index*)** | Temperatura aparente percebida pelo corpo humano sob os efeitos combinados de calor e umidade relativa, modelado pelas equações de regressão múltipla de Steadman/NOAA. | `calculate_heat_index()` em `analysis.py` |
| **Alerta Barométrico de Tempestade** | Detecção de gradiente barométrico negativo (pressão atmosférica $< 1005\text{ hPa}$) combinada a alta umidade relativa ($> 75\%$) e rajadas de vento convectivas. | `evaluate_storm_risk()` em `analysis.py` |
| **Reanálise Atmosférica (ERA5)** | Modelo computacional global do Centro Europeu de Previsões Meteorológicas a Médio Prazo (ECMWF) que combina observações do passado com modelos físicos para recriar o clima histórico de qualquer lugar da Terra. | `fetch_historical_day()` e `fetch_annual_dataset()` em `weather_api.py` |
| **Análise de Anomalia Climática** | Comparação entre o valor observado no momento e a média climatológica histórica de referência ($\Delta T = T_{\text{atual}} - \bar{T}_{\text{hist}}$), identificando extremos de calor ou frio. | `calculate_climate_anomaly()` em `analysis.py` |
| **ETL (Extract, Transform, Load)** | Pipeline que ingere dados heterogêneos (CSVs do INMET com metadados no topo, CSVs exportados ou JSONs de APIs) e os transforma em um formato uniforme e limpo. | `data_loader.py` e `weather_api.py` |
| **Auditoria de Qualidade (*Data Quality*)** | Verificação algorítmica de integridade: checagem de 8.760 horas por ano bissexto/não-bissexto, valores nulos, registros duplicados, chuva negativa e violação física ($T_{\max} < T_{\min}$). | `quality_report()` em `analysis.py` |
| **Detecção de Outliers por IQR** | Método não-paramétrico baseado no Intervalo Interquartil ($\text{IQR} = Q_3 - Q_1$). Valores além de $[Q_1 - 1.5 \times \text{IQR}, Q_3 + 1.5 \times \text{IQR}]$ são sinalizados como discrepantes. | `_iqr_outlier_count()` em `analysis.py` |
| **Correlação de Pearson** | Coeficiente $r \in [-1, 1]$ que mede a força e a direção da relação linear entre precipitação, temperatura máxima e mínima. | `correlation_matrix()` em `analysis.py` |
| **Cache com Invalidação por TTL** | Mecanismo de alta performance que armazena respostas de requisições de rede em memória por um Tempo de Vida (*Time-To-Live*) definido (ex.: 1h para dias históricos, 24h para séries anuais). | `@st.cache_data` |

---

## 5. Dicionário de Python Básico e Avançado Usado no Código

| Recurso | Explicação Didática | Exemplo no Código |
|---|---|---|
| `dataclass(frozen=True)` | Decorador do Python que cria classes para estruturar dados imutáveis, gerando automaticamente construtores, representação em texto e comparação de igualdade. | `StationDataset`, `FilterSpec` |
| `type annotations` (`float \| None`) | Notação de tipos estáticos que documenta o que a função espera receber e retornar, prevenindo erros em tempo de desenvolvimento. | `def calculate_dew_point(...) -> float \| None:` |
| `tuple unpacking` | Desempacotamento de múltiplos valores retornados por uma função em variáveis individuais. | `hi_val, hi_desc, hi_alert = calculate_heat_index(...)` |
| `pathlib.Path` | Mapeamento orientado a objetos para o sistema de arquivos, funcionando de forma transparente e idêntica no Windows, Linux e macOS. | `DATA_DIR / "dados_A101_H_2014.csv"` |
| `io.StringIO` / `io.BytesIO` | Criação de fluxos de leitura e escrita diretamente na memória RAM, sem necessidade de salvar arquivos temporários em disco. | Usado no upload e conversão de CSVs no `data_loader.py` |
| `try ... except ... finally` | Estrutura de tratamento de exceções que impede falhas de conexão de rede ou arquivos corrompidos de derrubar a aplicação. | Captura de erros de requisição HTTP em `weather_api.py` |
| `list comprehension` / `generator` | Sintaxe concisa para transformar ou filtrar coleções em uma única linha de código. | `[m for m in MESES_PT if m != "Nenhum"]` |
| `lambda functions` | Funções anônimas de linha única usadas para transformações pontuais em ordenação ou formatação. | `format_func=lambda p: p.name` |
| `st.session_state` | Dicionário de estado persistente do Streamlit que mantém dados, tema e configurações vivos entre as recargas de tela do usuário. | `st.session_state["dataset"]` |
| `math.log` / `math.sqrt` | Funções matemáticas de alta precisão da biblioteca padrão do Python usadas nos algoritmos meteorológicos. | Fórmula de Magnus-Tetens e regressão do Heat Index |

---

## 6. Dicionário das Bibliotecas Externas

| Biblioteca | Papel no ClimaPS | Principais Operações Executadas |
|---|---|---|
| **Pandas (`pd`)** | Motor de manipulação de dados tabulares em alta performance. | `pd.read_csv`, `pd.to_datetime`, `pd.to_numeric`, `.groupby()`, `.agg()`, `.resample()`, `.corr()`, `.to_csv()` |
| **NumPy (`np`)** | Computação numérica vetorial e tratamento de valores matemáticos especiais. | `np.nan`, `np.inf`, cálculos estatísticos de quartis |
| **Requests** | Cliente HTTP síncrono para consumo de APIs REST externas. | `requests.get()`, tratamento de timeout e validação de `status_code` |
| **Plotly (`go`, `px`)** | Motor gráfico interativo baseado em JavaScript/D3.js com renderização vetorial e suporte nativo a temas escuro e claro. | `go.Figure`, `go.Scatter`, `px.bar`, `px.imshow`, formatação de eixos e *hoverlabels* |
| **Streamlit (`st`)** | Framework web reativo que converte código Python puro em interface web com componentes nativos. | `st.tabs`, `st.sidebar`, `st.metric`, `st.dataframe`, `st.radio`, `st.date_input`, `st.download_button` |

---

## 7. Dicionário Completo dos Módulos e Funções do ClimaPS

### 📂 `climaps/core/data_loader.py` — Ingestão e Normalização de Dados
- **`COLUNAS_INTERNAS`**: Dicionário que traduz cabeçalhos longos do INMET para nomes canônicos curtos (`data`, `hora`, `precipitacao_mm`, `temp_max_c`, `temp_min_c`).
- **`StationDataset`**: Classe estruturada (`dataclass`) imutável contendo os metadados da estação (`metadata`), o DataFrame tratado (`data`) e a origem (`source`).
- **`_localizar_cabecalho(linhas)`**: Analisador léxico que inspeciona as primeiras linhas do arquivo e detecta se o arquivo é um CSV bruto do INMET, uma tabela exportada pelo ClimaPS ou uma série temporal com data/hora.
- **`load_station_csv(path)`**: Função universal de carga que aceita caminhos (`Path`, `str`), texto puro, `bytes`, buffers `StringIO` ou arquivos enviados via upload do Streamlit (`UploadedFile`), normalizando tipos numéricos e construindo o índice temporal `data_hora`.

### 📂 `climaps/core/analysis.py` — Núcleo Meteorológico e Estatístico
- **`FilterSpec`**: Estrutura que encapsula os critérios de filtragem do usuário (datas inicial e final, janela de horas e filtro de chuva).
- **`apply_filters(df, spec)`**: Executa o fatiamento temporal e categórico de acordo com as especificações.
- **`calculate_kpis(df)`**: Calcula os indicadores-chave: total de registros, precipitação acumulada, médias das temperaturas máxima e mínima, e porcentagem de integridade temporal.
- **`monthly_summary(df)` / `daily_summary(df)`**: Agrupamentos temporais que sumarizam chuva e temperaturas por mês ou dia.
- **`_iqr_outlier_count(series)`**: Implementação do cálculo de outliers baseado no intervalo interquartil ($Q_3 - Q_1$).
- **`quality_report(df)`**: Auditoria de dados que quantifica buracos temporais, duplicidades, valores nulos, registros atípicos e inconsistências físicas ($T_{\max} < T_{\min}$).
- **`generate_insights(df)`**: Gerador de conclusões descritivas automatizadas (mês mais chuvoso, pico de calor, maior tempestade e dias de estiagem).
- **`correlation_matrix(df)`**: Matriz de covariância e correlação linear de Pearson entre as variáveis climáticas.
- **`calculate_dew_point(temp_c, humidity_pct)`**: Algoritmo de Magnus-Tetens para estimativa do Ponto de Orvalho em graus Celsius.
- **`calculate_heat_index(temp_c, humidity_pct)`**: Implementação completa da equação multivariada do NOAA/Steadman para Sensação Térmica e estresse bioclimático.
- **`evaluate_storm_risk(pressao, umidade, vento, rajadas, chuva)`**: Avaliação ponderada de risco convectivo e tempestade com gatilho barométrico ($< 1005\text{ hPa}$).
- **`calculate_climate_anomaly(df, current_weather)`**: Algoritmo comparativo que cruza o clima em tempo real com a média histórica do mês correspondente na estação carregada.
- **`classify_air_quality(us_aqi, pm2_5)`**: Categorização do índice internacional de qualidade do ar (*US AQI*) e particulados finos decorrentes de queimadas e poluição.
- **`classify_uv(uv_index)`**: Categorização da intensidade da radiação ultravioleta segundo os limites de segurança da OMS.

### 📂 `climaps/core/weather_api.py` — Integração de APIs Globais
- **`GEOCODING_URL` / `FORECAST_URL` / `AIR_QUALITY_URL` / `HISTORICAL_URL`**: Constantes com as rotas REST públicas da Open-Meteo.
- **`WMO_CODES_PT`**: Dicionário de tradução dos códigos de tempo WMO para português com emojis correspondentes.
- **`search_city(city_name)`**: Consulta o serviço de geocodificação para resolução de nomes de cidades e coordenadas mundiais.
- **`fetch_air_quality(lat, lon)`**: Coleta medições atmosféricas de poluentes (PM2.5, PM10, Monóxido de Carbono, Dióxido de Nitrogênio e Ozônio).
- **`fetch_current_point(lat, lon, label)`**: Coleta o pacote em tempo real de telemetria meteorológica da coordenada especificada.
- **`fetch_multiple_points(locations)`**: Coleta concorrente ou em lote do clima atual para múltiplos pontos globais.
- **`fetch_live_weather(lat, lon, label, past_days)`**: Coleta telemetria atual, previsão estendida de 7 dias e série horária recente convertida diretamente em `StationDataset`.
- **`fetch_historical_day(lat, lon, label, target_date)`**: Coleta dados de reanálise horária (ERA5) para uma data histórica específica.
- **`fetch_annual_dataset(lat, lon, label, year)`**: Coleta a série completa de 8.760 horas de um ano inteiro, estrutura os dados em conformidade com as colunas do INMET e gera um arquivo CSV pronto para uso.

### 📂 `climaps/ui_comparison.py` — Comparação Interanual e Séries Históricas
- **`_obter_arquivos_disponiveis()`**: Varre as pastas `data/`, `data/importados/` e `exportacoes/` para listar CSVs disponíveis para o usuário comparar.
- **`_carregar_dataset_ou_erro(origem)`**: Carrega o arquivo selecionado tratando exceções de parsing e exibindo alertas em caso de erro.
- **`_extrair_metricas_anuais(df)`**: Processa as métricas consolidada do ano (chuva total, temperatura média, extremos e contagem de dias com chuva).
- **`_construir_tabela_mensal(df_a, df_b, rotulo_a, rotulo_b)`**: Consolida as médias e somas dos 12 meses para os dois anos, calculando colunas de variação absoluta ($\Delta$) e percentual ($\%$) para cada mês.
- **`render_comparison_tab()`**: Orquestra toda a aba de comparação: formulários de seleção/upload de arquivos, cards de KPIs comparativos, gráficos de barras com deltas de chuva, curvas de amplitude térmica e tabela analítica detalhada.

### 📂 `climaps/ui_styles.py` — Sistema de Design e Temas (Dark & Light)
- **`NAVY` / `BLUE` / `ORANGE`**: Constantes cromáticas corporativas do ClimaPS.
- **`br_number(valor, decimais, sufixo)`**: Formatador numérico que aplica convenções brasileiras (ponto para milhar e vírgula para decimal).
- **`format_datetime_friendly(dt_str)`**: Formatador de data e hora para exibição amigável (`DD/MM/AAAA às HH:MM`).
- **`inject_custom_css()`**: Injeta estilos CSS avançados na página web, gerenciando contraste, bordas, sombras, botões, caixas de seleção, calendários e tipografia adaptados tanto ao Modo Escuro quanto ao Modo Claro (*White Mode*).
- **`render_header(station_meta, source_name)`**: Desenha o banner superior com status da estação meteorológica conectada.

### 📂 `climaps/ui_world.py` — Aba Mundo Ao Vivo e Recursos Globais
- **`cached_current_point` / `cached_historical_day` / `cached_annual_dataset`**: Funções decoradas com `@st.cache_data` para garantir navegação rápida sem redundância de tráfego de rede.
- **`render_world_live_tab()`**: Constrói a aba global integrando a busca de cidades, os seletores de ferramentas (`⚡ Clima Ao Vivo`, `📅 Consultar Qualquer Dia`, `📂 Baixar / Analisar 1 Ano`), cards bioclimáticos, radar interativo do Windy.com, pódio de extremos e tabela comparativa mundial.

### 📂 `climaps/ui_tabs.py` — Abas Analíticas Tradicionais
- **`render_summary_tab(df, spec)`**: Renderiza cards de KPIs, gráficos mensais combinados, insights automatizados e relatório de qualidade.
- **`render_charts_tab(df)`**: Renderiza gráficos de distribuição de chuva, amplitude térmica contínua e matriz de correlação com cores adaptadas ao tema ativo.
- **`render_table_tab(dataset)`**: Disponibiliza a interface de visualização e edição interativa de células da tabela na memória da sessão.
- **`render_explorer_tab(df)`**: Tabela paginada para filtragem rápida e inspeção individual de observações horárias.

### 📂 `app_streamlit.py` — Orquestrador Central da Aplicação
- **`main()`**: Ponto de entrada do sistema. Inicializa o estado da sessão (`st.session_state`), renderiza a barra lateral com seletores de arquivos, filtros e controle de tema (Dark/Light), e instancia as 7 abas principais da plataforma.
- **`build_sql_script(df, table_name)`**: Transforma qualquer subset filtrado de observações meteorológicas em um script SQL executável (`CREATE TABLE` e lotes de `INSERT INTO`).
- **`render_export_tab(df, source_name)`**: Interface que oferece download e cópia direta em disco dos dados em formatos CSV e SQL.

---

## 8. Suíte de Testes Automatizados e Garantia de Qualidade

O projeto conta com **20 testes unitários automatizados** implementados com o framework padrão `unittest` do Python, garantindo que refatorações ou expansões do código não quebrem regras de negócio:

### 🧪 `tests/test_analysis.py` (Testes Analíticos do INMET)
1. `test_metadata_and_shape`: Valida a extração correta de metadados e as 8.760 linhas da série horária anual.
2. `test_missing_values`: Verifica o tratamento rigoroso de valores nulos e ausentes.
3. `test_kpis`: Confere a exatidão matemática dos KPIs de chuva acumulada e médias térmicas.
4. `test_march_is_rainiest`: Valida a regra estatística que identifica março como o mês mais chuvoso na estação de Manaus em 2014.
5. `test_filter_january_afternoon`: Testa a aplicação combinada de filtros de mês e horário.
6. `test_quality_rules`: Valida a detecção de erros físicos, buracos de série e outliers.
7. `test_complete_hourly_timeline`: Garante a continuidade temporal perfeita das 8.760 horas.

### 🧪 `tests/test_ui_and_formatting.py` (Testes de Formatação, Física Atmosférica e Conectores)
8. `test_format_datetime_friendly`: Valida a conversão de timestamps ISO em formatos legíveis.
9. `test_dew_point_calculation`: Valida os cálculos de ponto de orvalho em temperaturas e umidades conhecidas.
10. `test_heat_index_calculation`: Valida a sensação térmica e os limiares de alerta de calor de Steadman/NOAA.
11. `test_storm_risk_evaluation`: Valida o disparo barométrico do alerta de tempestade em baixa pressão.
12. `test_air_quality_and_uv_classification`: Valida a classificação das faixas de poluição (AQI) e radiação UV.
13. `test_climate_anomaly_calculation`: Valida a detecção de anomalias térmicas entre dados ao vivo e médias históricas.
14. `test_parse_point_payload_with_forecast_and_indices`: Valida a transformação completa de payloads JSON da API.
15. `test_load_exported_climaps_csv`: Testa a ingestão de CSVs exportados com separador ponto-e-vírgula.
16. `test_load_exported_climaps_comma_csv`: Testa a ingestão de CSVs exportados com separador vírgula.
17. `test_fetch_historical_day`: Valida a recuperação e formatação de telemetria de um dia histórico no ERA5.
18. `test_fetch_annual_dataset_and_load_station_csv`: Valida o ciclo completo de baixar 1 ano via API e carregá-lo como `StationDataset`.
19. `test_load_station_csv_from_bytes_and_stream`: Testa o carregamento de CSVs a partir de `bytes`, `StringIO` e `UploadedFile`.
20. `test_comparison_metadata_detection`: Testa a identificação automática de anos e estações para a aba de comparação.

---

> 💡 **Dica de Estudo:** Para rodar todos os testes no terminal, execute:
> ```bash
> python -m unittest discover -s tests -v
> ```
