import pandas as pd  # Manipulação de DataFrames para tabela comparativa e mapa
import plotly.express as px  # Criação do mapa mundial interativo de pontos (scatter_geo)
import plotly.graph_objects as go  # Gráficos interativos customizados de previsão
import streamlit as st  # Framework da interface web e cache

from climaps.core.analysis import calculate_climate_anomaly  # Cruzamento de anomalia climática (Histórico vs Ao Vivo)
from climaps.core.weather_api import (  # Importa funções de integração com a API Open-Meteo
    fetch_current_point,  # Busca clima atual por coordenada
    fetch_live_weather,  # Busca clima + previsão + histórico recente de 30 dias
    fetch_multiple_points,  # Busca clima atual de várias cidades em uma chamada
    search_city,  # Pesquisa cidades por nome
)  # Fecha importação
from climaps.ui_styles import BLUE, NAVY, ORANGE, br_number, format_datetime_friendly  # Importa constantes visuais e formatadores


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

        # 1. Alerta de Risco de Tempestade e Barômetro
        storm_risk = weather.get("risco_tempestade") or {}
        if storm_risk:
            st.markdown(
                f"""
<div class="storm-banner {storm_risk.get('classe', 'storm-low')}">
    <span style="font-size:1.3rem;">{storm_risk.get('icone', '🟢')}</span>
    <div>
        <b>{storm_risk.get('nivel', 'Condição Atmosférica')}:</b> {storm_risk.get('detalhe', '')}
    </div>
</div>
                """,
                unsafe_allow_html=True,
            )

        # 2. Índices Bioclimáticos & Desconforto Térmico
        b1, b2, b3 = st.columns(3)
        with b1:
            hi_val = weather.get("indice_calor_c")
            hi_desc = weather.get("indice_calor_desc", "Normal")
            st.metric(
                "🔥 Índice de Calor (Heat Index)",
                f"{br_number(hi_val)} °C" if hi_val is not None else "-",
                delta=hi_desc,
                delta_color="off" if (hi_val is None or hi_val < 27) else "inverse",
                help="Combinação de temperatura e umidade relativa que reflete a temperatura aparente sentida pelo corpo humano (NOAA/Steadman).",
            )
        with b2:
            dew_val = weather.get("ponto_orvalho_c")
            dew_desc = "Muito Abafado / Tropical" if dew_val and dew_val >= 21 else ("Confortável" if dew_val and dew_val >= 10 else "Seco")
            st.metric(
                "💧 Ponto de Orvalho (Dew Point)",
                f"{br_number(dew_val)} °C" if dew_val is not None else "-",
                delta=dew_desc,
                delta_color="off",
                help="Temperatura em que o vapor d'água condensa. Valores acima de 20 °C provocam forte sensação de ar opressivo e desconforto térmico.",
            )
        with b3:
            uv_val = weather.get("uv_max")
            uv_info = weather.get("uv_info") or {}
            st.metric(
                "☀️ Radiação UV Máxima",
                f"UV {br_number(uv_val)}" if uv_val is not None else "-",
                delta=f"{uv_info.get('status', 'Índice')}",
                delta_color="off",
                help="Índice de radiação ultravioleta diária máxima conforme escala da OMS.",
            )

        # 3. Análise de Anomalias Climáticas (Histórico vs. Ao Vivo)
        hist_df = st.session_state.get("df")
        anomaly = calculate_climate_anomaly(hist_df, weather)
        if anomaly is not None:
            delta_t = anomaly["delta_temp"]
            delta_r = anomaly["delta_rain"]
            sinal_t = "+" if delta_t >= 0 else ""
            badge_cor = "#EF4444" if delta_t > 0.5 else ("#3B82F6" if delta_t < -0.5 else "#10B981")
            st.markdown(
                f"""
<div class="anomaly-card">
    <div class="anomaly-card-title">
        <span>📊 Anomalia Climática Histórica ({anomaly['mes_nome']})</span>
        <span class="kpi-badge" style="background-color:rgba({ '239,68,68,0.2' if delta_t > 0.5 else ('59,130,246,0.2' if delta_t < -0.5 else '16,185,129,0.2') }); color:{badge_cor};">
            { '🔺' if delta_t >= 0 else '🔻' } {sinal_t}{delta_t:.1f} °C vs. histórico
        </span>
    </div>
    <p class="anomaly-card-desc">
        {anomaly['summary_text']}<br>
        <b>Chuva observada hoje:</b> {br_number(anomaly['curr_rain'])} mm • <b>Média diária histórica de {anomaly['mes_nome']}:</b> {br_number(anomaly['hist_rain_daily_avg'])} mm ({'+' if delta_r >= 0 else ''}{delta_r:.1f} mm).
    </p>
</div>
                """,
                unsafe_allow_html=True,
            )
        else:
            with st.container(border=True):
                st.caption(
                    "💡 **Análise de Anomalia Histórica:** Carregue um CSV de estação do INMET na barra lateral ou clique no botão **📥 Carregar 30 dias nas abas** abaixo para cruzar a temperatura/chuva de hoje com a média histórica dos anos anteriores."
                )

        # 4. Qualidade do Ar e Monitoramento de Queimadas / Fumaça (Open-Meteo Air Quality)
        air_q = weather.get("air_quality") or {}
        if air_q:
            info = air_q.get("info") or {}
            with st.expander("🍃 Qualidade do Ar & Monitoramento de Queimadas (Open-Meteo)", expanded=True):
                aq1, aq2, aq3, aq4 = st.columns(4)
                us_aqi = air_q.get("us_aqi")
                pm25 = air_q.get("pm2_5")
                pm10 = air_q.get("pm10")
                co = air_q.get("co")

                aq1.metric("Índice US AQI", f"{us_aqi}" if us_aqi is not None else "-", info.get("status", "Geral"), delta_color="off")
                aq2.metric(
                    "PM2.5 (Fumaça fina)",
                    f"{br_number(pm25)} µg/m³" if pm25 is not None else "-",
                    "Queimadas / Fuligem",
                    delta_color="off",
                    help="Partículas inaláveis finas (< 2.5 µm), principal indicador de fumaça de queimadas e incêndios florestais na Amazônia.",
                )
                aq3.metric("PM10 (Poeira e aerossóis)", f"{br_number(pm10)} µg/m³" if pm10 is not None else "-", "Partículas inaláveis", delta_color="off")
                aq4.metric("Monóxido de Carbono (CO)", f"{br_number(co, 0)} µg/m³" if co is not None else "-", "Gases de combustão", delta_color="off")

                st.caption(f"{info.get('icone', 'ℹ️')} **Diagnóstico para a saúde:** {info.get('recomendacao', '')}")

        # 5. Previsão Horária e Estendida (7 a 14 dias)
        f_hourly = weather.get("forecast_hourly") or []
        f_daily = weather.get("forecast_daily") or []

        if f_hourly or f_daily:
            with st.container(border=True):
                st.markdown("#### 📈 Previsão Meteorológica Interativa")
                visao_prev = st.radio(
                    "Escopo da previsão",
                    ["⏱️ Próximas 24 horas (Horária)", "📅 Próximos 7 dias", "🗓️ Próximos 14 dias (Estendida)"],
                    horizontal=True,
                    label_visibility="collapsed",
                    key=f"radio_visao_prev_{target_label}",
                )

                is_dark = st.session_state.get("dark_mode", True)
                template = "plotly_dark" if is_dark else "plotly_white"

                if visao_prev.startswith("⏱️") and f_hourly:
                    df_h = pd.DataFrame(f_hourly[:24])
                    if not df_h.empty:
                        fig_prev = go.Figure()

                        # Barras de probabilidade de chuva no eixo secundário Y2
                        fig_prev.add_trace(
                            go.Bar(
                                x=df_h["hora_label"],
                                y=df_h["prob_chuva_pct"],
                                name="Prob. de Chuva (%)",
                                yaxis="y2",
                                marker_color="rgba(56, 189, 248, 0.35)" if is_dark else "rgba(40, 120, 181, 0.35)",
                                hovertemplate="<b>Hora:</b> %{x}<br><b>Prob. de Chuva:</b> %{y}%<extra></extra>",
                            )
                        )

                        # Linha de temperatura no eixo principal Y1
                        fig_prev.add_trace(
                            go.Scatter(
                                x=df_h["hora_label"],
                                y=df_h["temperatura_c"],
                                name="Temperatura (°C)",
                                mode="lines+markers",
                                line=dict(color=ORANGE, width=3, shape="spline"),
                                marker=dict(size=6, color=ORANGE),
                                hovertemplate="<b>Hora:</b> %{x}<br><b>Temperatura:</b> %{y:.1f} °C<extra></extra>",
                            )
                        )

                        fig_prev.update_layout(
                            template=template,
                            paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)",
                            height=340,
                            margin=dict(t=35, b=25, l=40, r=40),
                            hovermode="x unified",
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                            xaxis=dict(title="Horário local"),
                            yaxis=dict(
                                title=dict(text="Temperatura (°C)", font=dict(color=ORANGE)),
                                tickfont=dict(color=ORANGE),
                                showgrid=True,
                            ),
                            yaxis2=dict(
                                title=dict(text="Probabilidade de Chuva (%)", font=dict(color="#38BDF8")),
                                tickfont=dict(color="#38BDF8"),
                                overlaying="y",
                                side="right",
                                range=[0, 100],
                                showgrid=False,
                            ),
                        )
                        st.plotly_chart(fig_prev, width="stretch")

                elif f_daily:
                    dias_limite = 7 if "7 dias" in visao_prev else 14
                    df_d = pd.DataFrame(f_daily[:dias_limite])
                    if not df_d.empty:
                        fig_d = go.Figure()

                        # Chuva prevista em mm no eixo secundário Y2
                        fig_d.add_trace(
                            go.Bar(
                                x=df_d["data_label"],
                                y=df_d["chuva_mm"],
                                name="Chuva Prevista (mm)",
                                yaxis="y2",
                                marker_color="rgba(56, 189, 248, 0.45)" if is_dark else "rgba(40, 120, 181, 0.40)",
                                hovertemplate="<b>Data:</b> %{x}<br><b>Chuva prevista:</b> %{y:.1f} mm<extra></extra>",
                            )
                        )

                        # Curva de Temperatura Máxima
                        fig_d.add_trace(
                            go.Scatter(
                                x=df_d["data_label"],
                                y=df_d["temp_max_c"],
                                name="Temp. Máxima (°C)",
                                mode="lines+markers",
                                line=dict(color=ORANGE, width=3, shape="spline"),
                                marker=dict(size=7, color=ORANGE),
                                hovertemplate="<b>Temp. Máx.:</b> %{y:.1f} °C<extra></extra>",
                            )
                        )

                        # Curva de Temperatura Mínima
                        fig_d.add_trace(
                            go.Scatter(
                                x=df_d["data_label"],
                                y=df_d["temp_min_c"],
                                name="Temp. Mínima (°C)",
                                mode="lines+markers",
                                line=dict(color="#38BDF8" if is_dark else BLUE, width=2.5, shape="spline"),
                                marker=dict(size=6),
                                fill="tonexty",
                                fillcolor="rgba(56, 189, 248, 0.15)" if is_dark else "rgba(40, 120, 181, 0.12)",
                                hovertemplate="<b>Temp. Mín.:</b> %{y:.1f} °C<extra></extra>",
                            )
                        )

                        fig_d.update_layout(
                            template=template,
                            paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)",
                            height=350,
                            margin=dict(t=35, b=25, l=40, r=40),
                            hovermode="x unified",
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                            xaxis=dict(title="Dia"),
                            yaxis=dict(
                                title=dict(text="Temperatura (°C)", font=dict(color=ORANGE)),
                                tickfont=dict(color=ORANGE),
                                showgrid=True,
                            ),
                            yaxis2=dict(
                                title=dict(text="Chuva Acumulada (mm)", font=dict(color="#38BDF8")),
                                tickfont=dict(color="#38BDF8"),
                                overlaying="y",
                                side="right",
                                showgrid=False,
                            ),
                        )
                        st.plotly_chart(fig_d, width="stretch")

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

        cols_to_show = [
            "local",
            "condicao",
            "temperatura_c",
            "sensacao_c",
            "indice_calor_c",
            "ponto_orvalho_c",
            "umidade_pct",
            "vento_kmh",
            "pressao_hpa",
            "precipitacao_mm",
            "horario",
        ]
        available_cols = [c for c in cols_to_show if c in table_display.columns]

        st.dataframe(  # Exibe tabela comparativa completa dos locais
            table_display[available_cols],  # Seleciona e ordena as colunas mostradas
            hide_index=True,  # Oculta o índice do DataFrame
            column_config={  # Configura rótulos e formatos numéricos
                "local": "Local",  # Rótulo Local
                "condicao": "Condição",  # Rótulo Condição
                "temperatura_c": st.column_config.NumberColumn("Temp. (°C)", format="%.1f"),  # 1 casa decimal
                "sensacao_c": st.column_config.NumberColumn("Sensação (°C)", format="%.1f"),  # 1 casa decimal
                "indice_calor_c": st.column_config.NumberColumn("Índ. Calor (°C)", format="%.1f"),  # 1 casa decimal
                "ponto_orvalho_c": st.column_config.NumberColumn("Orvalho (°C)", format="%.1f"),  # 1 casa decimal
                "umidade_pct": st.column_config.NumberColumn("Umidade (%)", format="%d"),  # Inteiro
                "vento_kmh": st.column_config.NumberColumn("Vento (km/h)", format="%.1f"),  # 1 casa decimal
                "pressao_hpa": st.column_config.NumberColumn("Pressão (hPa)", format="%.0f"),  # Inteiro arredondado
                "precipitacao_mm": st.column_config.NumberColumn("Chuva (mm)", format="%.1f"),  # 1 casa decimal
                "horario": st.column_config.TextColumn("Hora local"),  # Rótulo Hora local formatada
            },  # Fecha column_config
        )  # Fecha st.dataframe