from datetime import date, datetime, timedelta  # Manipulação de datas para calendário e datasets anuais
from pathlib import Path  # Manipulação de diretórios para salvar datasets importados

import pandas as pd  # Manipulação de DataFrames para tabela comparativa
import plotly.graph_objects as go  # Gráficos interativos customizados de previsão
import streamlit as st  # Framework da interface web e cache

from climaps.core.analysis import calculate_climate_anomaly  # Cruzamento de anomalia climática (Histórico vs Ao Vivo)
from climaps.core.data_loader import StationDataset  # Tipo do dataset de estação meteorológica
from climaps.core.weather_api import (  # Importa funções de integração com a API Open-Meteo
    fetch_annual_dataset,  # Baixa série anual completa de 8.760 horas
    fetch_current_point,  # Busca clima atual por coordenada
    fetch_historical_day,  # Consulta telemetria de qualquer dia da história (ERA5)
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


@st.cache_data(ttl=3600, show_spinner=False)  # Cache de 1 hora para consulta de dia específico
def cached_historical_day(lat: float, lon: float, label: str, target_date: str) -> dict[str, object]:
    """Cache para consulta de telemetria de um dia histórico no ERA5 / Open-Meteo."""
    return fetch_historical_day(lat, lon, label, target_date)


@st.cache_data(ttl=86400, show_spinner=False)  # Cache de 24 horas para download de 1 ano completo
def cached_annual_dataset(lat: float, lon: float, label: str, year: int) -> tuple[StationDataset, bytes]:
    """Cache para download e estruturação de 1 ano completo (8.760 horas)."""
    return fetch_annual_dataset(lat, lon, label, year)


@st.cache_data(ttl=300)  # Cache de 5 minutos para o conjunto de cidades globais padrão
def cached_world_defaults() -> list[dict[str, object]]:  # Wrapper cacheado para as 10 cidades padrão
    return fetch_multiple_points(WORLD_DEFAULTS)  # Busca todas as cidades de WORLD_DEFAULTS em uma requisição


def render_world_live_tab() -> None:  # Renderiza toda a aba "🌍 Mundo Ao Vivo"
    is_dark = st.session_state.get("dark_mode", True)
    template = "plotly_dark" if is_dark else "plotly_white"
    chart_text_color = "#E2E8F0" if is_dark else "#0F172A"
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

    if "world_pins" not in st.session_state:  # Inicializa pinos globais na sessão se ainda não existirem
        try:
            st.session_state["world_pins"] = cached_world_defaults()
        except Exception:
            st.session_state["world_pins"] = []

    weather: dict[str, object] | None = None  # Inicializa o dicionário de clima atual do ponto alvo
    if target_lat is not None and target_lon is not None:  # Se houver coordenadas válidas definidas
        st.markdown("---")
        tool_mode = st.radio(
            "Selecione o recurso para este local:",
            [
                "⚡ Clima Ao Vivo (Tempo Real & Previsão)",
                "📅 Consultar Qualquer Dia (Calendário)",
                "📂 Baixar / Analisar 1 Ano Completo (CSV)",
            ],
            horizontal=True,
            key=f"world_tool_{target_lat:.2f}_{target_lon:.2f}",
        )

        if tool_mode.startswith("⚡"):
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
                b_c1, b_c2, b_c3 = st.columns(3)
                with b_c1:
                    hi_val = weather.get("indice_calor_c")
                    hi_desc = weather.get("indice_calor_desc", "Normal")
                    st.metric(
                        "🔥 Índice de Calor (Heat Index)",
                        f"{br_number(hi_val)} °C" if hi_val is not None else "-",
                        delta=hi_desc,
                        delta_color="off" if (hi_val is None or hi_val < 27) else "inverse",
                        help="Combinação de temperatura e umidade relativa que reflete a temperatura aparente sentida pelo corpo humano (NOAA/Steadman).",
                    )
                with b_c2:
                    dew_val = weather.get("ponto_orvalho_c")
                    dew_desc = "Muito Abafado / Tropical" if dew_val and dew_val >= 21 else ("Confortável" if dew_val and dew_val >= 10 else "Seco")
                    st.metric(
                        "💧 Ponto de Orvalho (Dew Point)",
                        f"{br_number(dew_val)} °C" if dew_val is not None else "-",
                        delta=dew_desc,
                        delta_color="off",
                        help="Temperatura em que o vapor d'água condensa. Valores acima de 20 °C provocam forte sensação de ar opressivo e desconforto térmico.",
                    )
                with b_c3:
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

                                fig_prev.add_trace(
                                    go.Bar(
                                        x=df_h["hora_label"],
                                        y=df_h["prob_chuva_pct"],
                                        name="Prob. de Chuva (%)",
                                        yaxis="y2",
                                        marker_color="rgba(14, 165, 233, 0.45)" if is_dark else "rgba(37, 99, 235, 0.35)",
                                        hovertemplate="<b>Hora:</b> %{x}<br><b>Prob. de Chuva:</b> %{y}%<extra></extra>",
                                    )
                                )

                                fig_prev.add_trace(
                                    go.Scatter(
                                        x=df_h["hora_label"],
                                        y=df_h["temperatura_c"],
                                        name="Temperatura (°C)",
                                        mode="lines+markers",
                                        line=dict(color="#F59E0B" if is_dark else ORANGE, width=2.5, shape="spline"),
                                        marker=dict(size=5, color="#F59E0B" if is_dark else ORANGE),
                                        hovertemplate="<b>Hora:</b> %{x}<br><b>Temperatura:</b> %{y:.1f} °C<extra></extra>",
                                    )
                                )

                                fig_prev.update_layout(
                                    template=template,
                                    font=dict(color=chart_text_color, family="Inter, sans-serif"),
                                    hoverlabel=dict(
                                        bgcolor="#1E293B" if is_dark else "#FFFFFF",
                                        bordercolor="#334155" if is_dark else "#CBD5E1",
                                        font=dict(color="#F8FAFC" if is_dark else "#0F172A", family="Inter, sans-serif"),
                                    ),
                                    paper_bgcolor="rgba(0,0,0,0)",
                                    plot_bgcolor="rgba(0,0,0,0)",
                                    height=340,
                                    margin=dict(t=45, b=25, l=40, r=40),
                                    hovermode="x unified",
                                    legend=dict(
                                        orientation="h",
                                        yanchor="bottom",
                                        y=1.04,
                                        xanchor="right",
                                        x=1,
                                        font=dict(color=chart_text_color),
                                    ),
                                    xaxis=dict(
                                        title=dict(text="Horário local", font=dict(color=chart_text_color)),
                                        tickfont=dict(color=chart_text_color),
                                    ),
                                    yaxis=dict(
                                        title=dict(text="Temperatura (°C)", font=dict(color="#D97706" if not is_dark else ORANGE)),
                                        tickfont=dict(color="#D97706" if not is_dark else ORANGE),
                                        showgrid=True,
                                    ),
                                    yaxis2=dict(
                                        title=dict(text="Probabilidade de Chuva (%)", font=dict(color="#0284C7" if not is_dark else "#38BDF8")),
                                        tickfont=dict(color="#0284C7" if not is_dark else "#38BDF8"),
                                        overlaying="y",
                                        side="right",
                                        range=[0, 100],
                                        showgrid=False,
                                    ),
                                )
                                st.plotly_chart(fig_prev, width="stretch", config={"displayModeBar": "hover", "displaylogo": False})

                        elif f_daily:
                            dias_limite = 7 if "7 dias" in visao_prev else 14
                            df_d = pd.DataFrame(f_daily[:dias_limite])
                            if not df_d.empty:
                                fig_d = go.Figure()

                                fig_d.add_trace(
                                    go.Bar(
                                        x=df_d["data_label"],
                                        y=df_d["chuva_mm"],
                                        name="Chuva Prevista (mm)",
                                        yaxis="y2",
                                        marker_color="rgba(14, 165, 233, 0.45)" if is_dark else "rgba(37, 99, 235, 0.40)",
                                        hovertemplate="<b>Data:</b> %{x}<br><b>Chuva prevista:</b> %{y:.1f} mm<extra></extra>",
                                    )
                                )

                                fig_d.add_trace(
                                    go.Scatter(
                                        x=df_d["data_label"],
                                        y=df_d["temp_max_c"],
                                        name="Temp. Máxima (°C)",
                                        mode="lines+markers",
                                        line=dict(color="#F59E0B" if is_dark else ORANGE, width=2.5, shape="spline"),
                                        marker=dict(size=6, color="#F59E0B" if is_dark else ORANGE),
                                        hovertemplate="<b>Temp. Máx.:</b> %{y:.1f} °C<extra></extra>",
                                    )
                                )

                                fig_d.add_trace(
                                    go.Scatter(
                                        x=df_d["data_label"],
                                        y=df_d["temp_min_c"],
                                        name="Temp. Mínima (°C)",
                                        mode="lines+markers",
                                        line=dict(color="#0EA5E9" if is_dark else BLUE, width=2.5, shape="spline"),
                                        marker=dict(size=5, color="#0EA5E9" if is_dark else BLUE),
                                        fill="tonexty",
                                        fillcolor="rgba(14, 165, 233, 0.12)" if is_dark else "rgba(37, 99, 235, 0.10)",
                                        hovertemplate="<b>Temp. Mín.:</b> %{y:.1f} °C<extra></extra>",
                                    )
                                )

                                fig_d.update_layout(
                                    template=template,
                                    font=dict(color=chart_text_color, family="Inter, sans-serif"),
                                    hoverlabel=dict(
                                        bgcolor="#1E293B" if is_dark else "#FFFFFF",
                                        bordercolor="#334155" if is_dark else "#CBD5E1",
                                        font=dict(color="#F8FAFC" if is_dark else "#0F172A", family="Inter, sans-serif"),
                                    ),
                                    paper_bgcolor="rgba(0,0,0,0)",
                                    plot_bgcolor="rgba(0,0,0,0)",
                                    height=350,
                                    margin=dict(t=45, b=25, l=40, r=40),
                                    hovermode="x unified",
                                    legend=dict(
                                        orientation="h",
                                        yanchor="bottom",
                                        y=1.04,
                                        xanchor="right",
                                        x=1,
                                        font=dict(color=chart_text_color),
                                    ),
                                    xaxis=dict(
                                        title=dict(text="Dia", font=dict(color=chart_text_color)),
                                        tickfont=dict(color=chart_text_color),
                                    ),
                                    yaxis=dict(
                                        title=dict(text="Temperatura (°C)", font=dict(color="#D97706" if not is_dark else ORANGE)),
                                        tickfont=dict(color="#D97706" if not is_dark else ORANGE),
                                        showgrid=True,
                                    ),
                                    yaxis2=dict(
                                        title=dict(text="Chuva Acumulada (mm)", font=dict(color="#0284C7" if not is_dark else "#38BDF8")),
                                        tickfont=dict(color="#0284C7" if not is_dark else "#38BDF8"),
                                        overlaying="y",
                                        side="right",
                                        showgrid=False,
                                    ),
                                )
                                st.plotly_chart(fig_d, width="stretch", config={"displayModeBar": "hover", "displaylogo": False})

                b1, b2, b3, b4 = st.columns([1, 1, 1, 1.3])  # Cria 4 colunas para os botões de ação
                with b1:  # Botão 1: fixar cidade atual
                    if st.button("📌 Fixar na tabela/mapa", width="stretch") and weather is not None:
                        pins = [p for p in st.session_state["world_pins"] if p["local"] != weather["local"]]
                        pins.append(weather)
                        st.session_state["world_pins"] = pins
                with b2:  # Botão 2: restaurar lista global padrão
                    if st.button("🌍 Cidades globais", width="stretch"):
                        try:
                            st.session_state["world_pins"] = cached_world_defaults()
                        except Exception as exc:
                            st.error(f"Erro ao carregar cidades globais: {exc}")
                with b3:  # Botão 3: limpar mapa/tabela comparativa
                    if st.button("🧹 Limpar mapa", width="stretch"):
                        st.session_state["world_pins"] = []
                with b4:  # Botão 4: importar últimos 30 dias da cidade atual para as outras abas
                    if st.button("📥 Carregar 30 dias nas abas", width="stretch") and target_lat is not None and target_lon is not None:
                        try:
                            bundle = fetch_live_weather(
                                latitude=target_lat,
                                longitude=target_lon,
                                location_name=target_label,
                                past_days=30,
                                forecast_days=7,
                            )
                            st.session_state["dataset"] = bundle.dataset
                            st.session_state["df"] = bundle.dataset.data.copy()
                            st.toast(f"Histórico recente carregado para {target_label}!", icon="📊")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Erro ao carregar histórico: {exc}")

        elif tool_mode.startswith("📅"):  # "📅 Consultar Qualquer Dia (Calendário)"
            st.markdown("#### 📅 Consulta de Clima por Calendário Histórico")
            c_d1, c_d2 = st.columns([1.2, 2])
            with c_d1:
                data_consulta = st.date_input(
                    "Selecione o dia desejado",
                    value=date.today() - timedelta(days=1),
                    min_value=date(1940, 1, 1),
                    max_value=date.today() + timedelta(days=7),
                    key=f"cal_date_{target_lat:.2f}_{target_lon:.2f}",
                    help="Consulte qualquer data desde 1940 até previsões para os próximos dias (dados ERA5 e Open-Meteo).",
                )
            with c_d2:
                st.caption("💡 **Dica de pesquisa histórica:**")
                st.markdown(
                    f"Consulte o clima exato em **{target_label}** em qualquer dia da história registrada (desde 1940) "
                    "com telemetria hora a hora de temperatura, chuva, umidade e vento."
                )

            hist_day: dict[str, object] | None = None
            if data_consulta:
                with st.spinner(f"Consultando dados de {data_consulta.strftime('%d/%m/%Y')} para {target_label}..."):
                    try:
                        hist_day = cached_historical_day(target_lat, target_lon, target_label, str(data_consulta))
                    except Exception as exc:
                        st.error(f"Erro ao consultar histórico para {data_consulta.strftime('%d/%m/%Y')}: {exc}")

            if hist_day is not None:
                is_dark = st.session_state.get("dark_mode", True)
                st.markdown(
                    f"""
<div class="hero-weather">
<div>
<span class="hero-badge">📅 {hist_day['dia_semana']} • {hist_day['data_formatada']}</span>
<h3 class="hero-title">{hist_day['local']}</h3>
<div class="hero-sub">
{hist_day['condicao']} • Fuso horário: <code>{hist_day['fuso']}</code>
</div>
</div>
<div style="text-align:right;">
<div class="hero-temp" style="font-size:2.2rem;">
<span style="color:{'#F59E0B' if is_dark else '#D97706'};">{br_number(hist_day['temp_max_c'])}°</span> / 
<span style="color:{'#38BDF8' if is_dark else '#2563EB'};">{br_number(hist_day['temp_min_c'])}°C</span>
</div>
<div class="hero-sensacao">
Média do dia: <b>{br_number(hist_day['temp_media_c'])} °C</b> • Amplitude: <b>{br_number(hist_day['amplitude_termica_c'])} °C</b>
</div>
</div>
</div>
                    """,
                    unsafe_allow_html=True,
                )

                m1, m2, m3, m4, m5, m6 = st.columns(6)
                m1.metric("Temp. Máxima", f"{br_number(hist_day['temp_max_c'])} °C")
                m2.metric("Temp. Mínima", f"{br_number(hist_day['temp_min_c'])} °C")
                m3.metric("Temp. Média", f"{br_number(hist_day['temp_media_c'])} °C")
                m4.metric("Chuva do Dia", f"{br_number(hist_day['precipitacao_total_mm'])} mm")
                m5.metric("Vento Máximo", f"{br_number(hist_day['vento_max_kmh'])} km/h")
                m6.metric("Umidade Média", f"{br_number(hist_day['umidade_media_pct'], 0)}%")

                st.caption(
                    f"🌅 Sol: **{hist_day['nascer_sol']} – {hist_day['por_sol']}** • "
                    f"🧭 Pressão Média: **{br_number(hist_day['pressao_media_hpa'], 0)} hPa**"
                )

                hourly_list = hist_day.get("hourly") or []
                if hourly_list:
                    df_day = pd.DataFrame(hourly_list)
                    template = "plotly_dark" if is_dark else "plotly_white"

                    fig_day = go.Figure()
                    fig_day.add_trace(
                        go.Bar(
                            x=df_day["hora_label"],
                            y=df_day["chuva_mm"],
                            name="Chuva (mm)",
                            yaxis="y2",
                            marker_color="rgba(14, 165, 233, 0.45)" if is_dark else "rgba(37, 99, 235, 0.40)",
                            hovertemplate="<b>Hora:</b> %{x}<br><b>Chuva:</b> %{y:.1f} mm<extra></extra>",
                        )
                    )
                    fig_day.add_trace(
                        go.Scatter(
                            x=df_day["hora_label"],
                            y=df_day["temperatura_c"],
                            name="Temperatura (°C)",
                            mode="lines+markers",
                            line=dict(color="#F59E0B" if is_dark else ORANGE, width=3, shape="spline"),
                            marker=dict(size=6, color="#F59E0B" if is_dark else ORANGE),
                            hovertemplate="<b>Hora:</b> %{x}<br><b>Temperatura:</b> %{y:.1f} °C<extra></extra>",
                        )
                    )
                    fig_day.update_layout(
                        template=template,
                        font=dict(color=chart_text_color, family="Inter, sans-serif"),
                        hoverlabel=dict(
                            bgcolor="#1E293B" if is_dark else "#FFFFFF",
                            bordercolor="#334155" if is_dark else "#CBD5E1",
                            font=dict(color="#F8FAFC" if is_dark else "#0F172A", family="Inter, sans-serif"),
                        ),
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        height=350,
                        margin=dict(t=45, b=25, l=40, r=40),
                        hovermode="x unified",
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.04,
                            xanchor="right",
                            x=1,
                            font=dict(color=chart_text_color),
                        ),
                        xaxis=dict(
                            title=dict(text="Horário local", font=dict(color=chart_text_color)),
                            tickfont=dict(color=chart_text_color),
                        ),
                        yaxis=dict(
                            title=dict(text="Temperatura (°C)", font=dict(color="#D97706" if not is_dark else ORANGE)),
                            tickfont=dict(color="#D97706" if not is_dark else ORANGE),
                            showgrid=True,
                        ),
                        yaxis2=dict(
                            title=dict(text="Precipitação (mm)", font=dict(color="#0284C7" if not is_dark else "#38BDF8")),
                            tickfont=dict(color="#0284C7" if not is_dark else "#38BDF8"),
                            overlaying="y",
                            side="right",
                            showgrid=False,
                        ),
                    )
                    st.plotly_chart(fig_day, width="stretch", config={"displayModeBar": "hover", "displaylogo": False})

                    with st.expander("📋 Ver telemetria horária completa do dia em tabela"):
                        st.dataframe(
                            df_day[["hora_label", "condicao", "temperatura_c", "chuva_mm", "umidade_pct", "vento_kmh"]],
                            hide_index=True,
                            column_config={
                                "hora_label": "Hora",
                                "condicao": "Condição",
                                "temperatura_c": st.column_config.NumberColumn("Temp. (°C)", format="%.1f"),
                                "chuva_mm": st.column_config.NumberColumn("Chuva (mm)", format="%.1f"),
                                "umidade_pct": st.column_config.NumberColumn("Umidade (%)", format="%d"),
                                "vento_kmh": st.column_config.NumberColumn("Vento (km/h)", format="%.1f"),
                            },
                        )

        else:  # "📂 Baixar / Analisar 1 Ano Completo (CSV)"
            st.markdown("#### 📂 Histórico Anual Completo — Download de CSV & Análise (ERA5)")
            st.write(
                f"Gere o histórico meteorológico de um ano inteiro (8.760 registros horários) para **{target_label}** "
                "via reanálise ERA5 / Open-Meteo. Você pode baixar o CSV no padrão ClimaPS/INMET ou carregá-lo instantaneamente "
                "nas abas de análise (Resumo, Gráficos, Editor e Exportar)."
            )

            c_yr, c_info = st.columns([1, 2])
            now_year = datetime.now().year
            with c_yr:
                ano_escolhido = st.selectbox(
                    "Selecione o ano",
                    options=list(range(now_year, 1939, -1)),
                    index=1 if now_year > 1940 else 0,
                    key=f"annual_year_{target_lat:.2f}_{target_lon:.2f}",
                )
            with c_info:
                st.info(
                    f"📍 **Local:** {target_label} ({target_lat:.2f}, {target_lon:.2f}) • **Ano:** {ano_escolhido}\n\n"
                    "⚡ O dataset contém **8.760 registros horários** completos com data, hora, temperatura e precipitação."
                )

            annual_dataset: StationDataset | None = None
            annual_csv_bytes: bytes | None = None
            with st.spinner(f"Buscando histórico anual de {ano_escolhido} para {target_label} no Open-Meteo ERA5..."):
                try:
                    annual_dataset, annual_csv_bytes = cached_annual_dataset(
                        target_lat, target_lon, target_label, ano_escolhido
                    )
                except Exception as exc:
                    st.error(f"Erro ao buscar histórico anual de {ano_escolhido}: {exc}")

            if annual_dataset is not None and annual_csv_bytes is not None:
                df_ann = annual_dataset.data
                t_max_ann = df_ann["temp_max_c"].max()
                t_min_ann = df_ann["temp_min_c"].min()
                t_med_ann = df_ann["temp_max_c"].mean()
                rain_total_ann = df_ann["precipitacao_mm"].sum()
                rain_days_ann = int((df_ann.groupby("dia")["precipitacao_mm"].sum() > 0.2).sum())

                st.success(
                    f"✅ Histórico do ano **{ano_escolhido}** carregado com sucesso! "
                    f"Total de **{len(df_ann):,}** horas registradas."
                )

                k1, k2, k3, k4 = st.columns(4)
                k1.metric("🌡️ Temp. Máxima do Ano", f"{br_number(t_max_ann)} °C")
                k2.metric("❄️ Temp. Mínima do Ano", f"{br_number(t_min_ann)} °C")
                k3.metric("📈 Temp. Média Anual", f"{br_number(t_med_ann)} °C")
                k4.metric("🌧️ Chuva Acumulada Anual", f"{br_number(rain_total_ann)} mm", f"{rain_days_ann} dias chuvosos")

                safe_name = "".join(c if c.isalnum() else "_" for c in target_label).strip("_")
                csv_filename = f"climaps_{safe_name}_{ano_escolhido}.csv"

                c_down, c_load = st.columns(2)
                with c_down:
                    st.download_button(
                        label=f"⬇️ Baixar CSV de {ano_escolhido} (8.760 horas)",
                        data=annual_csv_bytes,
                        file_name=csv_filename,
                        mime="text/csv",
                        width="stretch",
                        help="Baixa o CSV no padrão ClimaPS/INMET (codificação UTF-8-SIG, separador ';' e decimais com vírgula).",
                    )
                with c_load:
                    if st.button("📊 Carregar este ano nas Abas Analíticas", width="stretch", help="Carrega este ano nas abas Resumo, Gráficos, Editor e Exportar da aplicação."):
                        import_dir = Path(__file__).resolve().parent.parent / "data" / "importados"
                        try:
                            import_dir.mkdir(parents=True, exist_ok=True)
                            (import_dir / csv_filename).write_bytes(annual_csv_bytes)
                        except Exception:
                            pass
                        st.session_state["dataset"] = annual_dataset
                        st.session_state["df"] = df_ann.copy()
                        st.toast(f"Ano {ano_escolhido} de {target_label} carregado com sucesso nas abas!", icon="🚀")
                        st.rerun()

                # Gráfico de perfil mensal do ano
                is_dark = st.session_state.get("dark_mode", True)
                template = "plotly_dark" if is_dark else "plotly_white"
                df_m = df_ann.groupby("mes").agg(
                    temp_max=("temp_max_c", "max"),
                    temp_min=("temp_min_c", "min"),
                    temp_media=("temp_max_c", "mean"),
                    chuva_total=("precipitacao_mm", "sum"),
                ).reset_index()

                meses_abrev = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
                df_m["mes_nome"] = df_m["mes"].apply(lambda m: meses_abrev[m - 1] if 1 <= m <= 12 else str(m))

                fig_ano = go.Figure()
                fig_ano.add_trace(
                    go.Bar(
                        x=df_m["mes_nome"],
                        y=df_m["chuva_total"],
                        name="Chuva Mensal (mm)",
                        yaxis="y2",
                        marker_color="rgba(14, 165, 233, 0.45)" if is_dark else "rgba(37, 99, 235, 0.40)",
                        hovertemplate="<b>Mês:</b> %{x}<br><b>Chuva total:</b> %{y:.1f} mm<extra></extra>",
                    )
                )
                fig_ano.add_trace(
                    go.Scatter(
                        x=df_m["mes_nome"],
                        y=df_m["temp_media"],
                        name="Temp. Média (°C)",
                        mode="lines+markers",
                        line=dict(color="#F59E0B" if is_dark else ORANGE, width=3),
                        marker=dict(size=8, color="#F59E0B" if is_dark else ORANGE),
                        hovertemplate="<b>Mês:</b> %{x}<br><b>Temp. Média:</b> %{y:.1f} °C<extra></extra>",
                    )
                )
                fig_ano.update_layout(
                    template=template,
                    font=dict(color=chart_text_color, family="Inter, sans-serif"),
                    hoverlabel=dict(
                        bgcolor="#1E293B" if is_dark else "#FFFFFF",
                        bordercolor="#334155" if is_dark else "#CBD5E1",
                        font=dict(color="#F8FAFC" if is_dark else "#0F172A", family="Inter, sans-serif"),
                    ),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    height=320,
                    margin=dict(t=45, b=25, l=40, r=40),
                    hovermode="x unified",
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.04,
                        xanchor="right",
                        x=1,
                        font=dict(color=chart_text_color),
                    ),
                    xaxis=dict(
                        title=dict(text="Mês", font=dict(color=chart_text_color)),
                        tickfont=dict(color=chart_text_color),
                    ),
                    yaxis=dict(
                        title=dict(text="Temperatura Média (°C)", font=dict(color="#D97706" if not is_dark else ORANGE)),
                        tickfont=dict(color="#D97706" if not is_dark else ORANGE),
                        showgrid=True,
                    ),
                    yaxis2=dict(
                        title=dict(text="Chuva Acumulada (mm)", font=dict(color="#0284C7" if not is_dark else "#38BDF8")),
                        tickfont=dict(color="#0284C7" if not is_dark else "#38BDF8"),
                        overlaying="y",
                        side="right",
                        showgrid=False,
                    ),
                )
                st.plotly_chart(fig_ano, width="stretch", config={"displayModeBar": "hover", "displaylogo": False})

    st.divider()  # Insere uma linha divisória horizontal
    st.markdown("#### 🌪️ Mapa Meteorológico Global Dinâmico (Windy.com)")

    with st.container(border=True):  # Container onde o mapa Windy é desenhado
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
            st.iframe(windy_url, height=520)  # Renderiza o iframe do Windy
        else:  # Compatibilidade com versões anteriores do Streamlit
            st.components.v1.iframe(windy_url, height=520)  # Usa st.components.v1.iframe como fallback

        st.link_button("🔗 Abrir mapa Windy em nova aba se o navegador bloquear o quadro", windy_url)

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