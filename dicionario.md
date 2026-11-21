# 📘 Dicionário Didático do Projeto ClimaPS

> **Objetivo deste documento:** explicar, de forma clara, aprofundada e acessível para estudantes, desenvolvedores e pesquisadores, o funcionamento integral do sistema **ClimaPS** — desde a arquitetura frontend em React e TypeScript até os fluxos de dados, modelos físicos meteorológicos, métodos estatísticos e módulos do código.

---

## 📑 Sumário

1. [Visão Geral do Sistema](#1-visão-geral-do-sistema)
2. [Arquitetura em Camadas (Como as Partes Conversam)](#2-arquitetura-em-camadas-como-as-partes-conversam)
3. [Fluxo dos Dados na Prática](#3-fluxo-dos-dados-na-prática)
4. [Conceitos Acadêmicos e de Ciência de Dados Aplicados](#4-conceitos-acadêmicos-e-de-ciência-de-dados-aplicados)
5. [Dicionário de TypeScript, React e CSS Usados no Código](#5-dicionário-de-typescript-react-e-css-usados-no-código)
6. [Dicionário das Bibliotecas e Ferramentas Externas](#6-dicionário-das-bibliotecas-e-ferramentas-externas)
7. [Dicionário Completo dos Módulos e Funções do ClimaPS](#7-dicionário-completo-dos-módulos-e-funções-do-climaps)
8. [Garantia de Qualidade, Tipagem e Build](#8-garantia-de-qualidade-tipagem-e-build)

---

## 1. Visão Geral do Sistema

O **ClimaPS** é uma aplicação web SPA (*Single Page Application*) de monitoramento meteorológico e análise de séries históricas desenvolvida em **React 19**, **TypeScript**, **Vite**, **Tailwind CSS v4** e **Recharts**, executada integralmente no navegador do usuário e estruturada em torno de três pilares:

1. **Monitoramento Climático Global em Tempo Real (`Mundo Ao Vivo`):**
   - Consulta instantânea de qualquer cidade ou coordenada (`Latitude` / `Longitude`) do globo sem necessidade de chave de API.
   - Cálculo em tempo real de índices bioclimáticos: **Ponto de Orvalho (*Dew Point*)**, **Índice de Calor (*Heat Index*)**, **Risco Barométrico de Tempestade**, **Radiação UV** e **Qualidade do Ar (*US AQI*, PM2.5, PM10, CO, NO₂ e O₃)**.
   - **Calendário Histórico (ERA5):** consulta da curva horária de 24h de qualquer data no passado via reanálise atmosférica global.
   - **Gerador de Datasets Anuais (8.760h):** geração e download de séries horárias completas de 1 ano no padrão compatível com o INMET para qualquer ponto do planeta.
   - **Radar Animado ao Vivo:** integração direta com o radar meteorológico interativo do **Windy.com**.

2. **Comparação Interanual e Entre Estações (`Comparar Anos`):**
   - Confronto lado a lado entre dois conjuntos de dados (Ano A vs. Ano B ou duas estações diferentes), com suporte a arquivos salvos na sessão, upload de CSVs locais ou busca instantânea de anos históricos via **ERA5**.
   - Comparação de precipitação acumulada, médias térmicas, recordes, amplitude e dias chuvosos.
   - Gráficos comparativos mês a mês e matriz detalhada com variações absolutas ($\Delta$) e percentuais ($\%$).

3. **Análise Forense de Séries Históricas do INMET (`Análise Histórica`):**
   - Ingestão universal de arquivos CSV horários do **INMET** e arquivos exportados pelo próprio **ClimaPS** (com separador `;` ou `,`).
   - Filtros dinâmicos na barra lateral por intervalo de datas, janela horária e ocorrência de precipitação.
   - Auditoria de qualidade de dados (*Data Quality Report*), detecção de *outliers* pelo método **IQR** e **matriz de correlação de Pearson**.
   - Edição interativa de medições diretamente na tabela da sessão e exportação em **CSV (UTF-8-SIG)** ou scripts **SQL** (`CREATE TABLE` + `INSERT INTO`).

---

## 2. Arquitetura em Camadas (Como as Partes Conversam)

O projeto aplica **Separação de Responsabilidades (*Separation of Concerns*)**, mantendo contratos de tipos, lógica matemática/meteorológica, conectores HTTP e componentes de interface desacoplados:

| Camada | Diretórios / Arquivos | Papel no sistema |
|---|---|---|
| **Contratos de Dados (Types)** | `src/types/weather.ts` | Define todas as interfaces TypeScript do domínio (`WeatherRecord`, `StationDataset`, `FilterSpec`, `LivePointWeather`, `KpiResult`, `QualityReport`, etc.), garantindo segurança de tipos em toda a aplicação. |
| **Ingestão & Conectores (Data Layer)** | `src/core/dataLoader.ts`<br>`src/core/weatherApi.ts` | Faz o parsing universal de CSVs do INMET/ClimaPS, gera exportações CSV/SQL e consome os endpoints públicos REST da **Open-Meteo** (Geocoding, Forecast, Air Quality e Archive/ERA5) com cache TTL em memória. |
| **Núcleo Analítico (Domain / Core)** | `src/core/analysis.ts`<br>`src/core/formatters.ts`<br>`src/core/weatherIcons.tsx` | Executa algoritmos de física atmosférica (Magnus-Tetens, Steadman/NOAA), avaliação barométrica de tempestades, anomalias climáticas, filtros, KPIs, auditoria IQR, correlação de Pearson, formatação PT-BR e mapeamento de ícones WMO. |
| **Apresentação & Workspace (UI)** | `src/App.tsx`<br>`src/index.css`<br>`src/components/Sidebar.tsx`<br>`src/components/HeaderBanner.tsx`<br>`src/components/MetricCard.tsx`<br>`src/components/WorldLiveTab.tsx`<br>`src/components/ComparisonTab.tsx`<br>`src/components/AnalyticsTabs.tsx` | Gerencia o estado global da sessão, alternância de tema Escuro/Claro, barra lateral de navegação e filtros, cabeçalho contextual, painéis de telemetria, gráficos interativos com Recharts e tabelas de alta densidade. |

---

## 3. Fluxo dos Dados na Prática

### 🔹 Caminho A — Monitoramento Global & Clima Ao Vivo (`Mundo Ao Vivo`)
1. O usuário informa uma cidade (ex.: `"Manaus"`) ou coordenadas geográficas.
2. `searchCity()` consulta a API de geocodificação da Open-Meteo e retorna a lista de correspondências com latitude, longitude e elevação.
3. `fetchCurrentPoint()` (com suporte de `fetchAirQuality()`) busca telemetria em tempo real, previsão horária de 24h, previsão diária estendida (7 a 14 dias) e poluentes atmosféricos.
4. `calculateDewPoint()`, `calculateHeatIndex()`, `evaluateStormRisk()`, `classifyAirQuality()` e `classifyUv()` transformam os dados brutos em indicadores bioclimáticos e alertas interpretáveis.
5. Caso haja uma base histórica carregada na sessão, `calculateClimateAnomaly()` compara a temperatura atual com a média climatológica do mês correspondente na estação carregada.
6. O iframe integrado do **Windy.com** exibe o radar meteorológico animado na coordenada selecionada, com seletor de camadas (chuva, vento, temperatura, nuvens e pressão).

### 🔹 Caminho B — Calendário Histórico & Datasets Anuais Globais (8.760h)
1. **Consulta por Calendário:** O usuário escolhe uma data passada e `fetchHistoricalDay()` consulta a reanálise **ERA5**, retornando a evolução horária completa de 24h (temperatura, sensação, umidade, chuva, vento e pressão).
2. **Geração de 1 Ano Completo:** O usuário escolhe um ano para a coordenada ativa. `fetchAnnualDataset()` coleta as 8.760 horas do ano na API de arquivo ERA5, converte o resultado em `StationDataset` e constrói um CSV padronizado via `buildCsvExport()`.
3. O dataset pode ser baixado imediatamente em `.csv` ou injetado direto na sessão do aplicativo (`onLoadDatasetIntoSession`) para análise completa em todas as abas históricas.

### 🔹 Caminho C — Comparação Interanual (`Comparar Anos`)
1. Para cada lado (**Série A** e **Série B**), o usuário escolhe entre: arquivo já salvo na sessão, upload de um CSV local ou download direto de um ano via reanálise **ERA5**.
2. `parseStationCsv()` normaliza os CSVs para `StationDataset` e `identifyYearAndName()` detecta automaticamente estação e ano de referência.
3. `calculateKpis()` e `monthlySummary()` extraem totais de precipitação, médias térmicas, recordes e dias chuvosos para os 12 meses de cada série.
4. Os componentes **Recharts** exibem gráficos comparativos de precipitação mensal e curvas térmicas sobrepostas, acompanhados da tabela de variações mensais ($\Delta$ absoluto e $\%$).

### 🔹 Caminho D — Análise Forense de Séries Históricas do INMET
1. O usuário abre o arquivo de exemplo (`public/data/dados_A101_H_2014.csv` — Manaus A101, 2014) ou envia um CSV do INMET/ClimaPS na barra lateral (por botão ou *drag-and-drop*).
2. `parseStationCsv()` lê metadados do cabeçalho, identifica separador (`;` ou `,`), converte decimais com vírgula para ponto flutuante e monta a coleção tipada de `WeatherRecord`.
3. O usuário ajusta os controles de filtro (`FilterSpec`) na barra lateral; `useMemo` reexecuta `applyFilters()` de forma reativa sem travar a interface.
4. As visões **Resumo e Qualidade**, **Gráficos e Correlação**, **Explorador** e **Exportar** atualizam instantaneamente com base no recorte filtrado.
5. Edições feitas na **Tabela Editável** atualizam o estado da sessão em `App.tsx` e ficam imediatamente disponíveis para gráficos, auditoria e exportação em CSV ou SQL.

---

## 4. Conceitos Acadêmicos e de Ciência de Dados Aplicados

| Conceito | O que significa na prática | Onde atua no ClimaPS |
|---|---|---|
| **Ponto de Orvalho (*Dew Point*)** | Temperatura na qual o vapor d'água contido no ar atinge saturação e condensa em gotículas. É um indicador mais fiel de abafamento do que a umidade relativa isolada. Calculado via aproximação de **Magnus-Tetens** ($a = 17{,}27,\; b = 237{,}7$). | `calculateDewPoint()` em `src/core/analysis.ts` |
| **Índice de Calor (*Heat Index*)** | Temperatura aparente sentida pelo corpo humano sob a combinação de temperatura do ar e umidade relativa, segundo a equação de regressão múltipla de **Steadman / NOAA** com ajustes para faixas extremas de umidade. | `calculateHeatIndex()` em `src/core/analysis.ts` |
| **Risco Barométrico de Tempestade** | Avaliação combinada de queda de pressão atmosférica ($< 1005\text{ hPa}$), umidade elevada, rajadas de vento e precipitação ativa para classificar o nível de risco convectivo. | `evaluateStormRisk()` em `src/core/analysis.ts` |
| **Reanálise Atmosférica (ERA5)** | Conjunto global de dados do ECMWF que assimila observações históricas em modelos físicos numéricos para reconstruir o estado horário da atmosfera em qualquer coordenada do planeta. | `fetchHistoricalDay()` e `fetchAnnualDataset()` em `src/core/weatherApi.ts` |
| **Anomalia Climática** | Diferença entre a temperatura observada no instante atual e a média histórica de referência do mesmo mês ($\Delta T = T_{\text{atual}} - \bar{T}_{\text{hist}}$), classificando desvios quentes, frios ou dentro da normalidade. | `calculateClimateAnomaly()` em `src/core/analysis.ts` |
| **ETL no Navegador (Client-Side ETL)** | Pipeline que extrai dados de formatos heterogêneos (CSV bruto do INMET com cabeçalho de metadados, CSV exportado ou JSON REST), transforma tipos/datas e carrega em estruturas tipadas uniformes. | `src/core/dataLoader.ts` e `src/core/weatherApi.ts` |
| **Auditoria de Qualidade (*Data Quality*)** | Verificação sistemática da integridade temporal e física da série: continuidade horária (lacunas), contagem de valores nulos, registros duplicados, chuva negativa e violação física ($T_{\max} < T_{\min}$). | `qualityReport()` em `src/core/analysis.ts` |
| **Detecção de Outliers por IQR** | Método estatístico robusto baseado no Intervalo Interquartil ($\text{IQR} = Q_3 - Q_1$). Medições fora de $[Q_1 - 1{,}5 \times \text{IQR},\; Q_3 + 1{,}5 \times \text{IQR}]$ são contabilizadas como atípicas. | `iqrOutlierCount()` / `qualityReport()` em `src/core/analysis.ts` |
| **Correlação de Pearson ($r$)** | Medida adimensional no intervalo $[-1, 1]$ que quantifica a força e a direção da associação linear entre precipitação, temperatura máxima e temperatura mínima. | `correlationMatrix()` em `src/core/analysis.ts` |
| **Cache em Memória com TTL** | Armazenamento temporário de respostas HTTP indexado por chave de consulta com tempo de expiração (*Time-To-Live*), reduzindo latência e requisições repetidas à Open-Meteo. | `cacheGet()` / `cacheSet()` em `src/core/weatherApi.ts` |

---

## 5. Dicionário de TypeScript, React e CSS Usados no Código

| Recurso | Explicação Didática | Exemplo no Código |
|---|---|---|
| `interface` / `type` | Contratos estáticos do TypeScript que definem exatamente quais propriedades e tipos cada objeto possui, evitando erros de acesso a campos inexistentes em tempo de execução. | `WeatherRecord`, `StationDataset`, `TabKey` |
| `Union Types` (`number \| null`) | Permite declarar explicitamente quando um sensor pode retornar ausência de medição (`null`), obrigando o código a tratar valores faltantes antes de calcular médias ou somas. | `precipitacao_mm: number \| null` |
| `useState` | Hook do React que armazena estado reativo de um componente (como o dataset ativo, a aba selecionada, os filtros e o modo Escuro/Claro). | `const [isDark, setIsDark] = useState(true);` |
| `useEffect` | Hook usado para sincronizar efeitos colaterais externos ao ciclo de renderização, como aplicar a classe `.dark` no `<html>` ou disparar buscas na API quando a cidade muda. | `document.documentElement.classList.toggle('dark', isDark)` |
| `useMemo` | Memoriza o resultado de cálculos pesados (como filtrar 8.760 registros ou gerar matrizes mensais), recalculando apenas quando suas dependências mudam. | `const filteredRecords = useMemo(() => applyFilters(...), [records, filterSpec])` |
| `useCallback` | Preserva a identidade de funções passadas como propriedades (*props*) para componentes filhos, evitando re-renderizações desnecessárias. | `handleLoadSavedFile`, `handleUploadCsv` |
| `async` / `await` & `Promise.all` | Sintaxe assíncrona do JavaScript/TypeScript para realizar chamadas HTTP sem travar a interface e buscar múltiplas cidades ou endpoints em paralelo. | `fetchCurrentPoint()`, `fetchMultiplePoints()` |
| `Blob` & `URL.createObjectURL` | APIs nativas do navegador que permitem gerar e baixar arquivos `.csv` e `.sql` localmente direto da memória RAM, sem precisar de um servidor backend. | Exportação em `ExportTab` e `WorldLiveTab` |
| CSS Custom Properties & `@custom-variant dark` | Tokens semânticos (`--bg-canvas`, `--bg-surface`, `--text-primary`, `--accent`) definidos em `:root` e `.dark`, permitindo troca instantânea entre tema Claro e Escuro com consistência de contraste. | `src/index.css` |
| `tabular-nums` (`JetBrains Mono`) | Recurso tipográfico em que todos os dígitos ocupam exatamente a mesma largura horizontal, garantindo alinhamento vertical perfeito em tabelas, KPIs e séries numéricas. | Classe `.font-mono-tabular` em `src/index.css` |

---

## 6. Dicionário das Bibliotecas e Ferramentas Externas

| Tecnologia | Papel no ClimaPS | Principais Recursos Utilizados |
|---|---|---|
| **React 19** | Biblioteca de interface declarativa baseada em componentes funcionais e hooks. | Composição de telas, gerenciamento de estado da sessão e renderização reativa de dados. |
| **TypeScript 5.7** | Superset tipado do JavaScript com verificação estática rigorosa (`tsc --noEmit`). | Tipagem forte de payloads da Open-Meteo, registros INMET, filtros e props dos componentes. |
| **Vite 6** | Bundler e servidor de desenvolvimento ultrarrápido baseado em ES Modules nativos. | Dev server instantâneo na porta `3000` e build otimizado de produção. |
| **Tailwind CSS v4** | Framework CSS *utility-first* integrado via `@tailwindcss/vite`. | Layout responsivo, grids analíticos, espaçamento consistente e variante `.dark`. |
| **Recharts** | Biblioteca de visualização de dados declarativa baseada em React e SVG. | `ResponsiveContainer`, `ComposedChart`, `AreaChart`, `BarChart`, `LineChart`, eixos formatados e tooltips dinâmicos. |
| **Lucide React** | Biblioteca de ícones vetoriais SVG com traço limpo e uniforme. | Ícones de navegação, controles de upload/exportação e condições meteorológicas WMO. |
| **Open-Meteo API** | Plataforma aberta de dados meteorológicos, qualidade do ar e reanálise ECMWF ERA5. | Geocoding API, Forecast API, Air Quality API e Historical Archive API (sem necessidade de chave). |
| **Windy.com Embed** | Serviço interativo de radar e mapas meteorológicos em tempo real. | Visualização incorporada de radar de chuva, vento, temperatura, nuvens e pressão atmosférica. |

---

## 7. Dicionário Completo dos Módulos e Funções do ClimaPS

### 📂 `src/types/weather.ts` — Contratos e Interfaces de Domínio
- **`WeatherRecord`**: Representa uma observação horária padronizada (`data`, `dia`, `hora`, `hora_num`, `data_hora`, `mes`, `precipitacao_mm`, `temp_max_c`, `temp_min_c`).
- **`StationDataset`**: Agrupa `metadata` da estação, array de `WeatherRecord` (`data`) e `sourceName`.
- **`SavedFileEntry`**: Descreve um arquivo disponível na barra lateral (arquivo de exemplo em `/public/data/`, CSV importado ou cópia exportada na sessão).
- **`FilterSpec`**: Encapsula o recorte ativo do usuário (`start`, `end`, `hourStart`, `hourEnd`, `rainyOnly`).
- **`LivePointWeather` / `HistoricalDayWeather` / `LiveWeatherBundle`**: Tipagens dos dados normalizados de telemetria atual, previsão, qualidade do ar e reanálise ERA5.
- **`KpiResult` / `MonthlySummaryRow` / `DailySummaryRow` / `QualityReport`**: Estruturas de saída do núcleo analítico.

### 📂 `src/core/dataLoader.ts` — Ingestão Universal e Exportação
- **`parseStationCsv(csvText, sourceName)`**: Detecta automaticamente o formato do CSV (INMET oficial com cabeçalho de metadados nas linhas iniciais ou CSV tabular exportado pelo ClimaPS), identifica separador (`;` ou `,`), normaliza números com vírgula decimal e gera um `StationDataset` ordenado cronologicamente.
- **`buildCsvExport(records, headerMeta)`**: Serializa os registros em CSV compatível com Excel e com o próprio ClimaPS (UTF-8 com BOM e separador `;`).
- **`buildSqlScript(records)`**: Gera script SQL completo (`CREATE TABLE IF NOT EXISTS observacoes_meteorologicas` + comandos `INSERT INTO` com tratamento de `NULL`) pronto para PostgreSQL, MySQL ou SQLite.
- **`identifyYearAndName(dataset)`**: Infere automaticamente o nome legível da estação e o ano predominante da série para rotular comparações interanuais.

### 📂 `src/core/analysis.ts` — Núcleo Meteorológico e Estatístico
- **`MESES_PT` / `MESES_NOMES` / `MESES_EXTENSO`**: Mapas de localização de meses em português.
- **`applyFilters(records, spec)`**: Filtra registros por intervalo de datas, janela horária e ocorrência de precipitação.
- **`calculateKpis(records)`**: Calcula total de registros, chuva acumulada, médias de $T_{\max}$ e $T_{\min}$, extremos e taxa de integridade temporal.
- **`monthlySummary(records)` / `dailySummary(records)`**: Agregadores mensais e diários de precipitação, médias térmicas, extremos e contagem de dias com chuva.
- **`qualityReport(records)`**: Executa auditoria completa: completude temporal, buracos na linha do tempo, duplicatas, valores ausentes, chuvas negativas, violações físicas ($T_{\max} < T_{\min}$) e contagem de *outliers* por IQR.
- **`generateInsights(records)`**: Sintetiza achados automáticos sobre a série (mês mais chuvoso, pico térmico, maior volume horário de chuva e proporção de dias secos).
- **`correlationMatrix(records)`**: Calcula a matriz de correlação linear de Pearson entre precipitação, temperatura máxima e temperatura mínima.
- **`calculateDewPoint(tempC, humidityPct)`**: Aproximação de Magnus-Tetens para o Ponto de Orvalho.
- **`calculateHeatIndex(tempC, humidityPct)`**: Equação de Steadman/NOAA para sensação térmica sob calor e umidade, com classificação de faixa de alerta.
- **`evaluateStormRisk(...)`**: Classifica o risco barométrico e convectivo de tempestade a partir de pressão, umidade, vento, rajadas e chuva.
- **`calculateClimateAnomaly(records, currentWeather)`**: Compara a temperatura em tempo real com a média histórica do mesmo mês na estação ativa.
- **`classifyAirQuality(usAqi, pm25)` / `classifyUv(uvIndex)`**: Classificadores padronizados de qualidade do ar (*US AQI*) e radiação ultravioleta (OMS).

### 📂 `src/core/weatherApi.ts` — Conectores Open-Meteo e ERA5
- **`WORLD_DEFAULTS`**: Lista inicial de cidades de referência global para monitoramento comparativo.
- **`WMO_CODES_PT` / `weatherDescription(code)`**: Dicionário e utilitário de tradução de códigos meteorológicos WMO para português.
- **`searchCity(cityName, count)`**: Geocodificação global por nome de cidade.
- **`fetchAirQuality(latitude, longitude)`**: Coleta de índice US AQI e concentrações de PM2.5, PM10, CO, NO₂ e O₃.
- **`fetchCurrentPoint(latitude, longitude, label)`**: Busca completa de telemetria atual, previsão horária (24h), previsão diária (14 dias) e qualidade do ar, com cache TTL.
- **`fetchMultiplePoints(locations)`**: Consulta paralela de múltiplas cidades para o painel comparativo mundial.
- **`fetchLiveWeather(latitude, longitude, label, pastDays)`**: Gera um `LiveWeatherBundle` com histórico horário recente (30 dias) pronto para carga nas abas analíticas.
- **`fetchHistoricalDay(latitude, longitude, label, targetDate)`**: Consulta horária de 24h de qualquer data histórica via reanálise ERA5.
- **`fetchAnnualDataset(latitude, longitude, label, year)`**: Coleta uma série anual completa (8.760 horas) via ERA5, retornando o `StationDataset` estruturado e o CSV pronto para download.

### 📂 `src/core/formatters.ts` e `src/core/weatherIcons.tsx` — Formatação e Iconografia
- **`brNumber(value, decimals)`**: Formata números no padrão brasileiro (`1.234,5`).
- **`formatDatetimeFriendly` / `formatDateTimeBR` / `formatDateBR`**: Formatação amigável de timestamps e datas ISO para o padrão `DD/MM/AAAA`.
- **`safeFilename(name)` / `getStamp()`**: Sanitização de nomes de arquivos e geração de timestamps para importações e exportações.
- **`cleanConditionText(raw)` / `WeatherConditionIcon`**: Remove emojis residuais das descrições WMO e renderiza o ícone vetorial correspondente (`lucide-react`).

### 📂 `src/components/*` e `src/App.tsx` — Interface e Orquestração
- **`Sidebar.tsx`**: Barra lateral fixa de 272px (com drawer responsivo no mobile) contendo marca, grupos de navegação (*Monitoramento* e *Análise Histórica*), importador CSV com *drag-and-drop*, seletor de bases salvas, filtros do recorte e seletor segmentado de tema (*Escuro* / *Claro*).
- **`HeaderBanner.tsx`**: Barra superior sticky (58px) com título da visão ativa, metadados discretos da estação conectada e ação principal contextual (*Abrir Manaus 2014* ou *Exportar base*).
- **`MetricCard.tsx`**: Cartão de indicador científico com separação tipográfica entre valor tabular e unidade de medida, suporte a tons semânticos e legenda auxiliar.
- **`WorldLiveTab.tsx`**: Tela principal de monitoramento global com busca por cidade/coordenadas, seletor segmentado de ferramentas (*Clima Ao Vivo*, *Calendário Histórico*, *Baixar / Analisar 1 Ano*), painel hero de telemetria, cartões bioclimáticos, anomalia climática, qualidade do ar, gráficos de previsão, radar Windy.com e tabela mundial comparativa.
- **`ComparisonTab.tsx`**: Tela de comparação interanual com seletores independentes (Salvo / Upload / ERA5) para Série A e Série B, KPIs comparativos, gráficos mensais e matriz de deltas.
- **`AnalyticsTabs.tsx`**: Exporta `SummaryTab`, `ChartsTab`, `EditableTableTab`, `ExplorerTab`, `ExportTab` e `HistoricalEmptyState`.
- **`App.tsx`**: Orquestrador central que gerencia estado da sessão, alternância da classe `.dark`, lista de bases salvas/importadas, aplicação memorizada de filtros, troca de visões e notificações toast.

---

## 8. Garantia de Qualidade, Tipagem e Build

A integridade do código é assegurada pela compilação estrita em TypeScript e pelo empacotamento de produção com Vite:

```bash
# 1. Valida toda a tipagem estática, contratos de dados e importações
npm run lint

# 2. Valida o bundle de produção (HTML, CSS Tailwind v4 e chunks JS)
npm run build

# 3. Inicia o servidor local de desenvolvimento na porta 3000
npm run dev
```

> 💡 **Dica de Estudo:** Para acompanhar como um dado sai de um arquivo do INMET ou da API da Open-Meteo até virar um gráfico na tela, leia os arquivos nesta ordem: `src/types/weather.ts` → `src/core/dataLoader.ts` → `src/core/analysis.ts` → `src/core/weatherApi.ts` → `src/App.tsx`.
