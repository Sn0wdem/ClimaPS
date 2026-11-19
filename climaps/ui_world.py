import pandas as pd  # Manipulação de DataFrames para tabela comparativa e mapa
import plotly.express as px  # Criação do mapa mundial interativo de pontos (scatter_geo)
import streamlit as st  # Framework da interface web e cache

from climaps.core.weather_api import (  # Importa funções de integração com a API Open-Meteo
    fetch_current_point,  # Busca clima atual por coordenada
    fetch_live_weather,  # Busca clima + previsão + histórico recente de 30 dias
    fetch_multiple_points,  # Busca clima atual de várias cidades em uma chamada
    search_city,  # Pesquisa cidades por nome
)  # Fecha importação
from climaps.ui_styles import NAVY, br_number, format_datetime_friendly  # Importa constantes visuais e formatadores


WORLD_DEFAULTS = [  # Lista padrão de 10 cidades globais pré-carregadas para comparação inicial
    ("Manaus (BR)", -3.10, -60.02),  # Manaus, Brasil
    ("São Paulo (BR)", -23.55, -46.63),  # São Paulo, Brasil
    ("Nova York (US)", 40.71, -74.01),  # Nova York, EUA
    ("Londres (UK)", 51.51, -0.13),  # Londres, Reino Unido
    ("Paris (FR)", 48.86, 2.35),  # Paris, França
    ("Tóquio (JP)", 35.68, 139.69),  # Tóquio, Japão
    ("Cairo (EG)", 30.04, 31.24),  # Cairo, Egito
    ("Cidade do Cabo (ZA)", -33.92, 18.42),  # Cidade do Cabo, África do Sul
    ("Sydney (AU)", -33.87, 151.21),  # Sydney, Austrália
    ("Moscou (RU)", 55.75, 37.62),  # Moscou, Rússia
]  # Fecha lista WORLD_DEFAULTS


@st.cache_data(ttl=300)  # Guarda o resultado em cache por 300 segundos (5 minutos) para evitar requisições repetidas
def cached_search_city(query: str) -> list[dict[str, object]]:  # Wrapper cacheado para busca de cidades
    return search_city(query, count=10)  # Chama search_city pedindo até 10 resultados


@st.cache_data(ttl=300)  # Cache de 5 minutos para consulta ao vivo de um ponto
def cached_current_point(lat: float, lon: float, label: str) -> dict[str, object]:  # Wrapper cacheado para clima atual
    return fetch_current_point(lat, lon, label)  # Chama fetch_current_point na API


@st.cache_data(ttl=300)  # Cache de 5 minutos para o conjunto de cidades globais padrão
def cached_world_defaults() -> list[dict[str, object]]:  # Wrapper cacheado para as 10 cidades padrão
    return fetch_multiple_points(WORLD_DEFAULTS)  # Busca todas as cidades de WORLD_DEFAULTS em uma requisição


def render_world_live_tab() -> None:  # Renderiza toda a aba "🌍 Mundo Ao Vivo"
    st.subheader("🌍 Consulta de clima ao vivo em qualquer lugar do mundo")  # Título principal da aba

    mode = st.radio(  # Seletor do método de busca do local
        "Modo de busca",  # Rótulo do radio
        ["Por nome da cidade / país", "Por coordenadas (Latitude / Longitude)"],  # Duas opções disponíveis
        horizontal=True,  # Exibe as opções lado a lado
    )  # Fecha st.radio

    target_lat: float | None = None  # Inicializa variável da latitude selecionada
    target_lon: float | None = None  # Inicializa variável da longitude selecionada
    target_label: str = ""  # Inicializa variável do nome de exibição do local

    if mode == "Por nome da cidade / país":  # Se o usuário escolheu buscar por texto
        col_q, col_res = st.columns([1, 1.5])  # Divide em duas colunas (campo de texto à esquerda, selectbox à direita)
        with col_q:  # Coluna da esquerda
            query = st.text_input("Digite qualquer cidade ou lugar do mundo", value="Manaus")  # Campo de busca iniciando com "Manaus"
        try:  # Tenta consultar a API de geocodificação
            matches = cached_search_city(query) if query.strip() else []  # Só pesquisa se o texto não estiver vazio
        except Exception as exc:  # Captura falhas de rede ou timeout
            st.error(f"Erro ao pesquisar local: {exc}")  # Exibe mensagem de erro na tela
            matches = []  # Define lista vazia para evitar quebra no fluxo abaixo

        with col_res:  # Coluna da direita
            if matches:  # Se encontrou pelo menos uma cidade correspondente
                chosen = st.selectbox(  # Lista suspensa para escolher exatamente qual cidade/estado/país deseja
                    "Local encontrado",  # Rótulo do selectbox
                    options=matches,  # Lista de dicionários retornados pela API
                    format_func=lambda r: (  # Formata cada opção exibindo Nome — Estado, País (lat, lon)
                        f"{r.get('name')} — "  # Nome da cidade
                        + ", ".join(x for x in [r.get("admin1"), r.get("country")] if x)  # Junta estado/região e país ignorando nulos
                        + f" ({r['latitude']:.2f}, {r['longitude']:.2f})"  # Mostra coordenadas com 2 casas decimais
                    ),  # Fecha format_func
                )  # Fecha st.selectbox
                target_lat = float(chosen["latitude"])  # Guarda a latitude do item selecionado
                target_lon = float(chosen["longitude"])  # Guarda a longitude do item selecionado
                target_label = f"{chosen.get('name')} ({chosen.get('country_code', '')})".strip()  # Monta rótulo ex.: "Manaus (BR)"
            else:  # Se não houve resultados para a busca
                st.warning("Nenhum local encontrado com esse nome.")  # Exibe aviso amigável
    else:  # Se o usuário escolheu "Por coordenadas (Latitude / Longitude)"
        c_lat, c_lon, c_lbl = st.columns(3)  # Cria 3 colunas iguais
        with c_lat:  # Primeira coluna: latitude
            target_lat = st.number_input("Latitude", min_value=-90.0, max_value=90.0, value=-3.10, step=0.01)  # Campo numérico [-90, 90]
        with c_lon:  # Segunda coluna: longitude
            target_lon = st.number_input("Longitude", min_value=-180.0, max_value=180.0, value=-60.02, step=0.01)  # Campo numérico [-180, 180]
        with c_lbl:  # Terceira coluna: rótulo personalizado
            target_label = st.text_input("Nome do ponto", value="Ponto personalizado")  # Nome para identificar a coordenada

    weather: dict[str, object] | None = None  # Inicializa o dicionário de clima atual do ponto alvo
    if target_lat is not None and target_lon is not None:  # Se houver coordenadas válidas definidas
        try:  # Tenta buscar os dados meteorológicos ao vivo
            weather = cached_current_point(target_lat, target_lon, target_label)  # Chama função cacheada
        except Exception as exc:  # Caso ocorra erro na requisição
            st.error(f"Erro ao consultar clima ao vivo: {exc}")  # Mostra erro na interface

    if weather is not None:  # Se os dados ao vivo foram obtidos com sucesso
        st.markdown(  # Renderiza o cartão hero HTML com destaque da cidade e temperatura
            f"""
<div class="hero-weather"> <!-- Container principal do cartão de telemetria -->
<div> <!-- Bloco esquerdo: badge, nome do local e condição -->
<span class="hero-badge">{weather['periodo']} • {weather['fuso']}</span> <!-- Mostra Dia/Noite e fuso horário -->
<h3 class="hero-title">{weather['local']}</h3> <!-- Nome da cidade/ponto selecionado -->
<div class="hero-sub"> <!-- Sublinha com condição e horário amigável -->
{weather['condicao']} • Atualizado em <code>{format_datetime_friendly(weather['horario'])}</code> <!-- Condição WMO e timestamp amigável -->
</div> <!-- Fecha bloco de condição -->
</div> <!-- Fecha bloco esquerdo -->
<div style="text-align:right;"> <!-- Bloco direito alinhado à direita: temperatura e sensação -->
<div class="hero-temp">{br_number(weather['temperatura_c'])} °C</div> <!-- Temperatura principal formatada -->
<div class="hero-sensacao"> <!-- Linha da sensação térmica -->
Sensação térmica: <b>{br_number(weather['sensacao_c'])} °C</b> <!-- Valor da sensação térmica -->
</div> <!-- Fecha div sensação -->
</div> <!-- Fecha bloco direito -->
</div> <!-- Fecha container hero-weather -->
            """,  # Fecha f-string HTML
            unsafe_allow_html=True,  # Permite HTML customizado
        )  # Fecha st.markdown

        m1, m2, m3, m4, m5, m6 = st.columns(6)  # Cria 6 colunas para métricas detalhadas
        m1.metric("Temperatura", f"{br_number(weather['temperatura_c'])} °C")  # Métrica 1: temperatura
        m2.metric("Sensação", f"{br_number(weather['sensacao_c'])} °C")  # Métrica 2: sensação térmica
        m3.metric("Umidade", f"{br_number(weather['umidade_pct'], 0)}%")  # Métrica 3: umidade relativa
        m4.metric("Vento", f"{br_number(weather['vento_kmh'])} km/h")  # Métrica 4: velocidade do vento
        m5.metric("Pressão", f"{br_number(weather['pressao_hpa'], 0)} hPa")  # Métrica 5: pressão atmosférica
        m6.metric("Chuva agora", f"{br_number(weather['precipitacao_mm'])} mm")  # Métrica 6: precipitação atual

        st.caption(  # Linha complementar abaixo dos cards com detalhes secundários
            f"☁️ Nuvens: {br_number(weather['nuvens_pct'], 0)}% • "  # Cobertura de nuvens
            f"💨 Rajadas: {br_number(weather['rajadas_kmh'])} km/h • "  # Rajadas de vento
            f"☀️ UV máx.: {br_number(weather['uv_max'])} • "  # Índice UV máximo do dia
            f"🌅 Sol: {weather['nascer_sol']} – {weather['por_sol']}"  # Horários de nascer e pôr do sol
        )  # Fecha st.caption

    if "world_pins" not in st.session_state:  # Na primeira execução da sessão, inicializa os pontos fixados no mapa
        try:  # Tenta carregar as 10 cidades globais padrão
            st.session_state["world_pins"] = cached_world_defaults()  # Salva a lista de dicionários na sessão
        except Exception:  # Se falhar (ex.: sem internet no arranque)
            st.session_state["world_pins"] = []  # Inicializa como lista vazia para não quebrar a página

    b1, b2, b3, b4 = st.columns([1, 1, 1, 1.3])  # Cria 4 colunas para os botões de ação (último botão um pouco mais largo)
    with b1:  # Botão 1: fixar cidade atual
        if st.button("📌 Fixar na tabela/mapa", width="stretch") and weather is not None:  # Ao clicar e havendo clima carregado
            pins = [p for p in st.session_state["world_pins"] if p["local"] != weather["local"]]  # Remove eventual entrada anterior de mesmo nome
            pins.append(weather)  # Adiciona o ponto atual à lista de pinos
            st.session_state["world_pins"] = pins  # Atualiza o estado da sessão
    with b2:  # Botão 2: restaurar lista global padrão
        if st.button("🌍 Cidades globais", width="stretch"):  # Ao clicar no botão
            try:  # Tenta buscar as 10 cidades padrão
                st.session_state["world_pins"] = cached_world_defaults()  # Restaura os pinos globais na sessão
            except Exception as exc:  # Em caso de erro de rede
                st.error(f"Erro ao carregar cidades globais: {exc}")  # Exibe erro
    with b3:  # Botão 3: limpar mapa/tabela comparativa
        if st.button("🧹 Limpar mapa", width="stretch"):  # Ao clicar no botão
            st.session_state["world_pins"] = []  # Esvazia a lista de pinos da sessão
    with b4:  # Botão 4: importar últimos 30 dias da cidade atual para as outras abas
        if st.button("📥 Carregar 30 dias nas abas", width="stretch") and target_lat is not None and target_lon is not None:  # Checa clique e coordenadas
            try:  # Tenta baixar o histórico recente da Open-Meteo
                bundle = fetch_live_weather(  # Busca série horária de 30 dias atrás + previsão de 7 dias
                    latitude=target_lat,  # Latitude do local
                    longitude=target_lon,  # Longitude do local
                    location_name=target_label,  # Nome do local
                    past_days=30,  # 30 dias históricos
                    forecast_days=7,  # 7 dias futuros
                )  # Fecha fetch_live_weather
                st.session_state["dataset"] = bundle.dataset  # Grava o StationDataset gerado na sessão
                st.session_state["df"] = bundle.dataset.data.copy()  # Grava cópia do DataFrame na sessão para análise/edição
                st.toast(f"Histórico recente carregado para {target_label}!", icon="📊")  # Exibe notificação flutuante
                st.rerun()  # Recarrega o app para liberar imediatamente as demais abas
            except Exception as exc:  # Caso a API falhe
                st.error(f"Erro ao carregar histórico: {exc}")  # Exibe erro na tela

    st.divider()  # Insere uma linha divisória horizontal
    map_type = st.radio(  # Seletor unificado de tipo de mapa
        "Visualização do mapa mundial",  # Rótulo do radio
        ["🌪️ Mapa animado ao vivo (Windy.com)", "📍 Mapa de pontos comparativo (Plotly)"],  # Opções
        horizontal=True,  # Layout horizontal
    )  # Fecha st.radio

    with st.container(border=True):  # Container com borda onde o mapa escolhido é efetivamente desenhado
        if map_type.startswith("🌪️"):  # Se o usuário selecionou o mapa animado do Windy.com
            c_camada, c_visao = st.columns(2)  # Duas colunas para controles do Windy
            with c_camada:  # Coluna esquerda: escolha da camada meteorológica
                camada = st.selectbox(  # Selectbox para o overlay do Windy
                    "Camada do mapa",  # Rótulo
                    ["wind", "temp", "rain", "clouds", "pressure"],  # Valores internos aceitos pela URL do Windy
                    format_func=lambda x: {  # Traduz códigos internos para rótulos amigáveis em português
                        "wind": "💨 Ventos",  # Camada de ventos
                        "temp": "🌡️ Temperatura",  # Camada térmica
                        "rain": "🌧️ Chuva",  # Camada de precipitação
                        "clouds": "☁️ Nuvens",  # Camada de nebulosidade
                        "pressure": "🧭 Pressão",  # Camada barométrica
                    }[x],  # Fecha dicionário de tradução
                )  # Fecha st.selectbox
            with c_visao:  # Coluna direita: escolha do enquadramento/zoom
                enq_opcoes = ["Mundo inteiro"]  # Opção padrão global
                if target_lat is not None and target_lon is not None:  # Se há uma cidade selecionada
                    enq_opcoes.append(f"Centralizar em {target_label}")  # Adiciona opção de focar na cidade atual
                visao = st.radio("Enquadramento", enq_opcoes, horizontal=True)  # Radio para alternar entre globo ou cidade

            zoom = 3 if visao == "Mundo inteiro" else 6  # Define zoom distante (3) para o mundo ou médio (6) para cidade
            map_lat = 15.0 if visao == "Mundo inteiro" else float(target_lat)  # Latitude central do mapa
            map_lon = -20.0 if visao == "Mundo inteiro" else float(target_lon)  # Longitude central do mapa

            windy_url = (  # Monta a URL de incorporação (embed) do Windy.com com os parâmetros selecionados
                "https://embed.windy.com/embed.html"  # Endpoint de embed do Windy
                f"?type=map&location=coordinates&metricRain=mm&metricTemp=%C2%B0C&metricWind=km/h"  # Unidades métricas (°C, mm, km/h)
                f"&zoom={zoom}&overlay={camada}&product=ecmwf&level=surface"  # Zoom, camada, modelo ECMWF e nível de superfície
                f"&lat={map_lat}&lon={map_lon}&message=true"  # Coordenadas centrais
            )  # Fecha URL do Windy
            if hasattr(st, "iframe"):  # Verifica se a versão do Streamlit possui st.iframe nativo
                st.iframe(windy_url, height=500)  # Renderiza o iframe do Windy com 500px de altura
            else:  # Compatibilidade com versões anteriores do Streamlit
                st.components.v1.iframe(windy_url, height=500)  # Usa st.components.v1.iframe como fallback

            st.link_button("🔗 Se o mapa ficar cinza por bloqueio do navegador, abra o Windy em nova aba", windy_url)  # Botão com link externo
        else:  # Caso tenha sido escolhido o mapa comparativo de pontos com Plotly
            map_points = st.session_state["world_pins"] or ([weather] if weather is not None else [])  # Usa pinos fixados ou apenas o ponto atual
            if map_points:  # Se houver ao menos 1 ponto para plotar
                is_dark = st.session_state.get("dark_mode", True)
                map_df = pd.DataFrame(map_points)  # Converte lista de dicionários em DataFrame
                fig_map = px.scatter_geo(  # Cria mapa geográfico de dispersão com Plotly
                    map_df,  # Tabela com coordenadas e dados climáticos
                    lat="latitude",  # Coluna de latitude
                    lon="longitude",  # Coluna de longitude
                    hover_name="local",  # Título do tooltip ao passar o mouse
                    hover_data={  # Campos extras exibidos/ocultados no tooltip
                        "temperatura_c": ":.1f",  # Temperatura com 1 decimal
                        "umidade_pct": True,  # Mostra umidade
                        "vento_kmh": ":.1f",  # Vento com 1 decimal
                        "condicao": True,  # Mostra condição WMO
                        "latitude": False,  # Oculta latitude bruta do tooltip
                        "longitude": False,  # Oculta longitude bruta do tooltip
                    },  # Fecha hover_data
                    color="temperatura_c",  # Cor dos marcadores proporcional à temperatura
                    color_continuous_scale="Turbo",  # Escala de cores do frio (azul) ao quente (vermelho)
                    projection="natural earth",  # Projeção cartográfica Natural Earth
                    title="Mapa mundial — Pontos comparados",  # Título do mapa
                )  # Fecha px.scatter_geo
                fig_map.update_traces(
                    marker=dict(size=13, line=dict(width=1.2, color="#FFFFFF" if not is_dark else "#F1F5F9"))
                )  # Aumenta pontos e coloca borda
                fig_map.update_geos(  # Configura estilo geográfico do mapa
                    showcountries=True,  # Mostra fronteiras entre países
                    showcoastlines=True,  # Mostra linhas costeiras
                    showland=True,  # Preenche continentes
                    landcolor="#1E293B" if is_dark else "#EEF3F8",  # Cor adaptada da terra
                    showocean=True,  # Preenche oceanos
                    oceancolor="#0E1726" if is_dark else "#DCEBFA",  # Cor adaptada dos oceanos
                    countrycolor="#334155" if is_dark else "#D0D9E2",  # Cor das fronteiras
                    coastlinecolor="#334155" if is_dark else "#D0D9E2",  # Cor da costa
                )  # Fecha update_geos
                fig_map.update_layout(  # Ajusta margens e fundos do mapa Plotly
                    template="plotly_dark" if is_dark else "plotly_white",
                    paper_bgcolor="rgba(0,0,0,0)",  # Fundo externo transparente
                    geo=dict(bgcolor="rgba(0,0,0,0)"),  # Fundo do globo transparente
                    height=450,  # Altura em pixels
                    margin=dict(t=40, b=10, l=0, r=0),  # Margens compactas
                )  # Fecha update_layout
                st.plotly_chart(fig_map, width="stretch")  # Exibe o mapa ocupando toda a largura

    table_points = st.session_state["world_pins"] or ([weather] if weather is not None else [])  # Pontos a exibir na tabela comparativa
    if table_points:  # Se houver pontos disponíveis para comparar
        st.subheader("📋 Comparação ao vivo entre locais do mundo")  # Subtítulo da seção comparativa
        table_df = pd.DataFrame(table_points)  # Converte a lista de pontos para DataFrame

        if len(table_df) > 1 and table_df["temperatura_c"].notna().any() and table_df["vento_kmh"].notna().any():  # Se houver 2+ pontos válidos
            quente = table_df.loc[table_df["temperatura_c"].idxmax()]  # Linha do local mais quente no momento
            fria = table_df.loc[table_df["temperatura_c"].idxmin()]  # Linha do local mais frio no momento
            vento = table_df.loc[table_df["vento_kmh"].idxmax()]  # Linha do local com maior vento no momento

            d1, d2, d3 = st.columns(3)  # Cria 3 colunas para o pódio de extremos
            with d1:
                st.markdown(
                    f"""
<div class="kpi-podium-card kpi-hot">
    <div class="kpi-podium-label">🔥 Mais quente agora</div>
    <div class="kpi-podium-value" title="{quente['local']}">{quente['local']}</div>
    <div class="kpi-badge-wrap">
        <span class="kpi-badge kpi-badge-hot">↑ {br_number(quente['temperatura_c'])} °C</span>
    </div>
</div>
                    """,
                    unsafe_allow_html=True,
                )
            with d2:
                st.markdown(
                    f"""
<div class="kpi-podium-card kpi-cold">
    <div class="kpi-podium-label">❄️ Mais frio agora</div>
    <div class="kpi-podium-value" title="{fria['local']}">{fria['local']}</div>
    <div class="kpi-badge-wrap">
        <span class="kpi-badge kpi-badge-cold">↓ {br_number(fria['temperatura_c'])} °C</span>
    </div>
</div>
                    """,
                    unsafe_allow_html=True,
                )
            with d3:
                st.markdown(
                    f"""
<div class="kpi-podium-card kpi-wind">
    <div class="kpi-podium-label">💨 Maior vento agora</div>
    <div class="kpi-podium-value" title="{vento['local']}">{vento['local']}</div>
    <div class="kpi-badge-wrap">
        <span class="kpi-badge kpi-badge-wind">💨 {br_number(vento['vento_kmh'])} km/h</span>
    </div>
</div>
                    """,
                    unsafe_allow_html=True,
                )

        table_display = table_df.copy()
        if "horario" in table_display.columns:
            table_display["horario"] = table_display["horario"].apply(format_datetime_friendly)

        st.dataframe(  # Exibe tabela comparativa completa dos locais
            table_display[  # Seleciona e ordena as colunas mostradas
                [
                    "local",  # Nome do local
                    "condicao",  # Condição atual
                    "temperatura_c",  # Temperatura atual
                    "sensacao_c",  # Sensação térmica
                    "umidade_pct",  # Umidade relativa
                    "vento_kmh",  # Velocidade do vento
                    "pressao_hpa",  # Pressão atmosférica
                    "precipitacao_mm",  # Chuva atual
                    "horario",  # Hora local da medição
                ]
            ],  # Fecha seleção de colunas
            hide_index=True,  # Oculta o índice do DataFrame
            column_config={  # Configura rótulos e formatos numéricos
                "local": "Local",  # Rótulo Local
                "condicao": "Condição",  # Rótulo Condição
                "temperatura_c": st.column_config.NumberColumn("Temp. (°C)", format="%.1f"),  # 1 casa decimal
                "sensacao_c": st.column_config.NumberColumn("Sensação (°C)", format="%.1f"),  # 1 casa decimal
                "umidade_pct": st.column_config.NumberColumn("Umidade (%)", format="%d"),  # Inteiro
                "vento_kmh": st.column_config.NumberColumn("Vento (km/h)", format="%.1f"),  # 1 casa decimal
                "pressao_hpa": st.column_config.NumberColumn("Pressão (hPa)", format="%.0f"),  # Inteiro arredondado
                "precipitacao_mm": st.column_config.NumberColumn("Chuva (mm)", format="%.1f"),  # 1 casa decimal
                "horario": st.column_config.TextColumn("Hora local"),  # Rótulo Hora local formatada
            },  # Fecha column_config
        )  # Fecha st.dataframe