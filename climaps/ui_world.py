import pandas as pd
import plotly.express as px
import streamlit as st

from climaps.core.weather_api import (
    fetch_current_point,
    fetch_live_weather,
    fetch_multiple_points,
    search_city,
)
from climaps.ui_styles import NAVY, br_number


WORLD_DEFAULTS = [
    ("Manaus (BR)", -3.10, -60.02),
    ("São Paulo (BR)", -23.55, -46.63),
    ("Nova York (US)", 40.71, -74.01),
    ("Londres (UK)", 51.51, -0.13),
    ("Paris (FR)", 48.86, 2.35),
    ("Tóquio (JP)", 35.68, 139.69),
    ("Cairo (EG)", 30.04, 31.24),
    ("Cidade do Cabo (ZA)", -33.92, 18.42),
    ("Sydney (AU)", -33.87, 151.21),
    ("Moscou (RU)", 55.75, 37.62),
]


@st.cache_data(ttl=300)
def cached_search_city(query: str) -> list[dict[str, object]]:
    return search_city(query, count=10)


@st.cache_data(ttl=300)
def cached_current_point(lat: float, lon: float, label: str) -> dict[str, object]:
    return fetch_current_point(lat, lon, label)


@st.cache_data(ttl=300)
def cached_world_defaults() -> list[dict[str, object]]:
    return fetch_multiple_points(WORLD_DEFAULTS)


def render_world_live_tab() -> None:
    st.subheader("🌍 Consulta de clima ao vivo em qualquer lugar do mundo")

    mode = st.radio(
        "Modo de busca",
        ["Por nome da cidade / país", "Por coordenadas (Latitude / Longitude)"],
        horizontal=True,
    )

    target_lat: float | None = None
    target_lon: float | None = None
    target_label: str = ""

    if mode == "Por nome da cidade / país":
        col_q, col_res = st.columns([1, 1.5])
        with col_q:
            query = st.text_input("Digite qualquer cidade ou lugar do mundo", value="Manaus")
        try:
            matches = cached_search_city(query) if query.strip() else []
        except Exception as exc:
            st.error(f"Erro ao pesquisar local: {exc}")
            matches = []

        with col_res:
            if matches:
                chosen = st.selectbox(
                    "Local encontrado",
                    options=matches,
                    format_func=lambda r: (
                        f"{r.get('name')} — "
                        + ", ".join(x for x in [r.get("admin1"), r.get("country")] if x)
                        + f" ({r['latitude']:.2f}, {r['longitude']:.2f})"
                    ),
                )
                target_lat = float(chosen["latitude"])
                target_lon = float(chosen["longitude"])
                target_label = f"{chosen.get('name')} ({chosen.get('country_code', '')})".strip()
            else:
                st.warning("Nenhum local encontrado com esse nome.")
    else:
        c_lat, c_lon, c_lbl = st.columns(3)
        with c_lat:
            target_lat = st.number_input("Latitude", min_value=-90.0, max_value=90.0, value=-3.10, step=0.01)
        with c_lon:
            target_lon = st.number_input("Longitude", min_value=-180.0, max_value=180.0, value=-60.02, step=0.01)
        with c_lbl:
            target_label = st.text_input("Nome do ponto", value="Ponto personalizado")

    weather: dict[str, object] | None = None
    if target_lat is not None and target_lon is not None:
        try:
            weather = cached_current_point(target_lat, target_lon, target_label)
        except Exception as exc:
            st.error(f"Erro ao consultar clima ao vivo: {exc}")

    if weather is not None:
        st.markdown(
            f"""
<div class="hero-weather">
<div>
<span class="hero-badge">{weather['periodo']} • {weather['fuso']}</span>
<h3 style="margin:0; color:{NAVY};">{weather['local']}</h3>
<div style="color:#60758A; font-size:0.92rem; margin-top:4px;">
{weather['condicao']} • Atualizado em <code>{weather['horario']}</code>
</div>
</div>
<div style="text-align:right;">
<div class="hero-temp">{br_number(weather['temperatura_c'])} °C</div>
<div style="color:#60758A; font-size:0.9rem; margin-top:4px;">
Sensação térmica: <b>{br_number(weather['sensacao_c'])} °C</b>
</div>
</div>
</div>
            """,
            unsafe_allow_html=True,
        )

        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("Temperatura", f"{br_number(weather['temperatura_c'])} °C")
        m2.metric("Sensação", f"{br_number(weather['sensacao_c'])} °C")
        m3.metric("Umidade", f"{br_number(weather['umidade_pct'], 0)}%")
        m4.metric("Vento", f"{br_number(weather['vento_kmh'])} km/h")
        m5.metric("Pressão", f"{br_number(weather['pressao_hpa'], 0)} hPa")
        m6.metric("Chuva agora", f"{br_number(weather['precipitacao_mm'])} mm")

        st.caption(
            f"☁️ Nuvens: {br_number(weather['nuvens_pct'], 0)}% • "
            f"💨 Rajadas: {br_number(weather['rajadas_kmh'])} km/h • "
            f"☀️ UV máx.: {br_number(weather['uv_max'])} • "
            f"🌅 Sol: {weather['nascer_sol']} – {weather['por_sol']}"
        )

    if "world_pins" not in st.session_state:
        try:
            st.session_state["world_pins"] = cached_world_defaults()
        except Exception:
            st.session_state["world_pins"] = []

    b1, b2, b3, b4 = st.columns([1, 1, 1, 1.3])
    with b1:
        if st.button("📌 Fixar na tabela/mapa", width="stretch") and weather is not None:
            pins = [p for p in st.session_state["world_pins"] if p["local"] != weather["local"]]
            pins.append(weather)
            st.session_state["world_pins"] = pins
    with b2:
        if st.button("🌍 Cidades globais", width="stretch"):
            try:
                st.session_state["world_pins"] = cached_world_defaults()
            except Exception as exc:
                st.error(f"Erro ao carregar cidades globais: {exc}")
    with b3:
        if st.button("🧹 Limpar mapa", width="stretch"):
            st.session_state["world_pins"] = []
    with b4:
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

    st.divider()
    map_type = st.radio(
        "Visualização do mapa mundial",
        ["🌪️ Mapa animado ao vivo (Windy.com)", "📍 Mapa de pontos comparativo (Plotly)"],
        horizontal=True,
    )

    with st.container(border=True):
       map_type = st.radio(
        "Visualização do mapa mundial",
        ["📍 Mapa de pontos comparativo (Plotly)", "🌪️ Mapa animado ao vivo (Windy.com)"],
        horizontal=True,
    )

    with st.container(border=True):
        if map_type.startswith("🌪️"):
            c_camada, c_visao = st.columns(2)
            with c_camada:
                camada = st.selectbox(
                    "Camada do mapa",
                    ["wind", "temp", "rain", "clouds", "pressure"],
                    format_func=lambda x: {
                        "wind": "💨 Ventos",
                        "temp": "🌡️ Temperatura",
                        "rain": "🌧️ Chuva",
                        "clouds": "☁️ Nuvens",
                        "pressure": "🧭 Pressão",
                    }[x],
                )
            with c_visao:
                enq_opcoes = ["Mundo inteiro"]
                if target_lat is not None and target_lon is not None:
                    enq_opcoes.append(f"Centralizar em {target_label}")
                visao = st.radio("Enquadramento", enq_opcoes, horizontal=True)

            zoom = 3 if visao == "Mundo inteiro" else 6
            map_lat = 15.0 if visao == "Mundo inteiro" else float(target_lat)
            map_lon = -20.0 if visao == "Mundo inteiro" else float(target_lon)

            windy_url = (
                "https://embed.windy.com/embed.html"
                f"?type=map&location=coordinates&metricRain=mm&metricTemp=%C2%B0C&metricWind=km/h"
                f"&zoom={zoom}&overlay={camada}&product=ecmwf&level=surface"
                f"&lat={map_lat}&lon={map_lon}&message=true"
            )
            if hasattr(st, "iframe"):
                st.iframe(windy_url, height=500)
            else:
                st.components.v1.iframe(windy_url, height=500)

            st.link_button("🔗 Se o mapa ficar cinza por bloqueio do navegador, abra o Windy em nova aba", windy_url)
        else:
            map_points = st.session_state["world_pins"] or ([weather] if weather is not None else [])
            if map_points:
                map_df = pd.DataFrame(map_points)
                fig_map = px.scatter_geo(
                    map_df,
                    lat="latitude",
                    lon="longitude",
                    hover_name="local",
                    hover_data={
                        "temperatura_c": ":.1f",
                        "umidade_pct": True,
                        "vento_kmh": ":.1f",
                        "condicao": True,
                        "latitude": False,
                        "longitude": False,
                    },
                    color="temperatura_c",
                    color_continuous_scale="Turbo",
                    projection="natural earth",
                    title="Mapa mundial — Pontos comparados",
                )
                fig_map.update_traces(marker=dict(size=13, line=dict(width=1.2, color="white")))
                fig_map.update_geos(
                    showcountries=True,
                    showcoastlines=True,
                    showland=True,
                    landcolor="#EEF3F8",
                    showocean=True,
                    oceancolor="#DCEBFA",
                )
                fig_map.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    geo=dict(bgcolor="rgba(0,0,0,0)"),
                    height=450,
                    margin=dict(t=40, b=10, l=0, r=0),
                )
                st.plotly_chart(fig_map, width="stretch") 

    table_points = st.session_state["world_pins"] or ([weather] if weather is not None else [])
    if table_points:
        st.subheader("📋 Comparação ao vivo entre locais do mundo")
        table_df = pd.DataFrame(table_points)

        if len(table_df) > 1 and table_df["temperatura_c"].notna().any() and table_df["vento_kmh"].notna().any():
            quente = table_df.loc[table_df["temperatura_c"].idxmax()]
            fria = table_df.loc[table_df["temperatura_c"].idxmin()]
            vento = table_df.loc[table_df["vento_kmh"].idxmax()]

            d1, d2, d3 = st.columns(3)
            d1.metric("🔥 Mais quente agora", str(quente["local"]), f"{br_number(quente['temperatura_c'])} °C")
            d2.metric("❄️ Mais frio agora", str(fria["local"]), f"{br_number(fria['temperatura_c'])} °C")
            d3.metric("💨 Maior vento agora", str(vento["local"]), f"{br_number(vento['vento_kmh'])} km/h")

        st.dataframe(
            table_df[
                [
                    "local",
                    "condicao",
                    "temperatura_c",
                    "sensacao_c",
                    "umidade_pct",
                    "vento_kmh",
                    "pressao_hpa",
                    "precipitacao_mm",
                    "horario",
                ]
            ],
            hide_index=True,
            column_config={
                "local": "Local",
                "condicao": "Condição",
                "temperatura_c": st.column_config.NumberColumn("Temp. (°C)", format="%.1f"),
                "sensacao_c": st.column_config.NumberColumn("Sensação (°C)", format="%.1f"),
                "umidade_pct": st.column_config.NumberColumn("Umidade (%)", format="%d"),
                "vento_kmh": st.column_config.NumberColumn("Vento (km/h)", format="%.1f"),
                "pressao_hpa": st.column_config.NumberColumn("Pressão (hPa)", format="%.0f"),
                "precipitacao_mm": st.column_config.NumberColumn("Chuva (mm)", format="%.1f"),
                "horario": "Hora local",
            },
        )