# ClimaPS — Telemetria e Análise Meteorológica

Aplicação didática em Python com Streamlit, Plotly e pandas para monitoramento climático global ao vivo e análise de dados meteorológicos horários no padrão do INMET.

A interface conta com tema escuro estilo telemetria, mapas interativos mundiais, previsão de 7 dias, comparação entre cidades e ferramentas completas para importar, filtrar, editar e exportar séries históricas em CSV e SQL.
Aplicacao didatica para importar, visualizar, editar e exportar dados meteorologicos horarios no padrao do INMET.

A versao atual foi simplificada para priorizar estabilidade: a interface usa componentes basicos do Flet, as tabelas sao leves e os graficos sao barras criadas diretamente com controles visuais simples.

## Funcionalidades

- inicia pronta para consultar o clima mundial ao vivo sem exigir CSV prévio;
- consulta condições atuais de qualquer cidade/país ou coordenada (`Latitude` / `Longitude`) via API Open-Meteo;
- exibe mapa global interativo (Plotly) e radar animado ao vivo (Windy.com);
- mostra previsão de 7 dias e duelo comparativo entre duas cidades do mundo;
- permite carregar os últimos 30 dias de qualquer cidade direto para as abas de análise;
- importa arquivos CSV horários do INMET pela barra lateral e salva cópias em `data/importados/`;
- aplica filtros por período, faixa de horário e ocorrência de chuva;
- calcula KPIs, insights automáticos, resumo mensal, matriz de correlação e diagnóstico de qualidade;
- permite editar chuva, temperatura máxima e temperatura mínima na sessão atual;
- exporta os dados (completos ou filtrados) em CSV e script SQL (`CREATE TABLE` e `INSERT`).

## Abas da aplicacao
- `🌍 LIVE MUNDO`: clima ao vivo global, cartão de telemetria, mapa Plotly/Windy, pódio de extremos e tabela comparativa.
- `📆 PREVISÃO 7D`: previsão diária em cards e gráfico combinado de temperatura e chuva para qualquer cidade.
- `⚔️ DUELO`: comparação ao vivo e curva térmica de 7 dias entre duas cidades escolhidas.
- `📊 RESUMO`: indicadores gerais (KPIs), insights automáticos, resumo mensal e qualidade da base.
- `📈 GRÁFICOS`: gráficos interativos de precipitação, amplitude térmica e matriz de correlação.
- `✏️ EDITOR`: tabela editável dos registros carregados na sessão.
- `🔍 EXPLORADOR`: visualização tabular dos registros conforme os filtros ativos.
- `⬇️ EXPORTAR`: download de CSV e script SQL (além de salvamento local em `exportacoes/`).

## Estrutura

```text
.
├── app_streamlit.py              # Interface principal em Streamlit
├── .streamlit/
│   └── config.toml               # Tema escuro padrão do ClimaPS
├── climaps/
│   ├── __init__.py
│   ├── ui_styles.py              # CSS, fontes, banner e faixa animada
│   ├── ui_world.py               # Aba Live Mundo (Open-Meteo, Plotly e Windy)
│   ├── ui_forecast.py            # Abas Previsão 7D e Duelo de Cidades
│   ├── ui_tabs.py                # Abas Resumo, Gráficos, Editor e Explorador
│   └── core/
│       ├── __init__.py
│       ├── data_loader.py        # Leitura e normalização do CSV do INMET
│       ├── analysis.py           # KPIs, resumos, filtros, insights e qualidade
│       └── weather_api.py        # Integração com a API pública Open-Meteo
├── data/
│   ├── dados_A101_H_2014.csv     # Exemplo de dataset (Manaus A101 - 2014)
│   └── importados/               # CSVs importados pela interface
├── exportacoes/                  # Arquivos CSV e SQL exportados
├── tests/
│   └── test_analysis.py          # Testes automatizados (unittest)
├── requirements.txt
└── README.md


## Instalar

No Windows:

```powershell
py -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

No Linux ou macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Executar
python -m streamlit run app_streamlit.py --server.port 8501

## Usar a aplicacao

1. Abra a aplicacao.
2. Clique em `Importar CSV` no topo.
3. Escolha um arquivo `.csv` no padrao do INMET.
4. Edite os valores na aba `Tabela`, se necessario.
5. Clique em `Salvar edicoes da pagina`.
6. Use `Importar/Exportar` para gerar CSV ou SQL.

Os arquivos importados ficam em:

```text
data/importados/
```

Os arquivos exportados ficam em:

```text
exportacoes/
```

## Exportacao SQL

A exportacao SQL gera um arquivo `.sql` com a tabela:

```sql
observacoes_meteorologicas
```

O arquivo inclui:

```sql
DROP TABLE IF EXISTS observacoes_meteorologicas;
CREATE TABLE observacoes_meteorologicas (...);
INSERT INTO observacoes_meteorologicas (...) VALUES (...);
```

## Executar testes

```powershell
python -m unittest discover -s tests -v
```

## Observacoes
O CSV deve seguir o formato horário do INMET, com metadados no início e tabela contendo data, hora, precipitação e temperaturas máxima/mínima. O carregador em climaps/core/data_loader.py faz a normalização dos nomes e tipos usados pela aplicação.
As consultas ao vivo utilizam a API pública Open-Meteo (sem necessidade de chave de API) e o embed oficial do Windy.com, exigindo conexão com a internet.

