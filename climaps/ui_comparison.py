from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from climaps.core.data_loader import StationDataset, load_station_csv
from climaps.core.weather_api import fetch_annual_dataset
from climaps.ui_styles import BLUE, NAVY, ORANGE, br_number


MESES_NOMES = [
    "Janeiro",
    "Fevereiro",
    "Março",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro",
]

MESES_ABREV = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


def _obter_arquivos_disponiveis() -> list[Path]:
    """Lista todos os arquivos CSV salvos em data/, data/importados/ e exportacoes/."""
    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / "data"
    import_dir = data_dir / "importados"
    export_dir = base_dir / "exportacoes"

    arquivos: list[Path] = []
    sample_csv = data_dir / "dados_A101_H_2014.csv"
    if sample_csv.exists():
        arquivos.append(sample_csv)
    if import_dir.exists():
        arquivos.extend(sorted(import_dir.glob("*.csv"), reverse=True))
    if export_dir.exists():
        arquivos.extend(sorted(export_dir.glob("*.csv"), reverse=True))
    return arquivos


def _identificar_ano_e_nome(dataset: StationDataset) -> tuple[str, str]:
    """Extrai ou detecta o ano e nome do local do dataset."""
    df = dataset.data
    nome = dataset.metadata.get("nome") or dataset.metadata.get("codigo_estacao") or dataset.source.stem
    nome = nome.replace("climaps_", "").replace("_", " ").title()

    ano_detectado = dataset.metadata.get("ano")
    if not ano_detectado and "data_hora" in df.columns:
        valid_years = df["data_hora"].dropna().dt.year.unique()
        if len(valid_years) > 0:
            ano_detectado = str(valid_years[0])
        else:
            ano_detectado = "Série"
    return nome, str(ano_detectado or "Série")


def _carregar_dataset_seletor(prefixo: str, titulo: str, default_index: int = 0) -> StationDataset | None:
    """Componente visual para carregar um dataset por upload, arquivo salvo ou busca no Open-Meteo ERA5."""
    with st.container(border=True):
        st.markdown(f"#### {titulo}")
        modo = st.radio(
            "Origem dos dados",
            ["📁 Arquivo salvo / importado", "📤 Upload de novo CSV", "🌐 Buscar ano no Open-Meteo ERA5"],
            horizontal=True,
            key=f"modo_comp_{prefixo}",
        )

        dataset: StationDataset | None = None

        if modo == "📁 Arquivo salvo / importado":
            arquivos = _obter_arquivos_disponiveis()
            if arquivos:
                idx = default_index if default_index < len(arquivos) else 0
                escolhido = st.selectbox(
                    "Selecione o arquivo CSV",
                    options=arquivos,
                    index=idx,
                    format_func=lambda p: f"{p.parent.name}/{p.name}",
                    key=f"file_select_{prefixo}",
                )
                if escolhido:
                    try:
                        dataset = load_station_csv(escolhido)
                    except Exception as exc:
                        st.error(f"Erro ao ler {escolhido.name}: {exc}")
            else:
                st.info("Nenhum arquivo CSV encontrado localmente. Faça um upload abaixo ou busque via Open-Meteo.")

        elif modo == "📤 Upload de novo CSV":
            uploaded = st.file_uploader(
                f"Envie o arquivo CSV para {prefixo.upper()} (INMET ou ClimaPS)",
                type=["csv"],
                key=f"uploader_{prefixo}",
            )
            if uploaded is not None:
                try:
                    dataset = load_station_csv(uploaded)
                    st.success(f"Arquivo `{uploaded.name}` carregado com sucesso!")
                except Exception as exc:
                    st.error(f"Erro ao processar CSV enviado: {exc}")

        else:  # "🌐 Buscar ano no Open-Meteo ERA5"
            c1, c2 = st.columns([1.5, 1])
            with c1:
                cidade = st.text_input("Cidade / Local", value="Manaus", key=f"city_era5_{prefixo}")
            with c2:
                now_year = datetime.now().year
                ano = st.selectbox(
                    "Ano",
                    options=list(range(now_year, 1939, -1)),
                    index=default_index if default_index < 50 else 1,
                    key=f"year_era5_{prefixo}",
                )

            # Coordenadas aproximadas para cidades comuns ou busca rápida
            coords = {
                "manaus": (-3.10, -60.02),
                "são paulo": (-23.55, -46.63),
                "sao paulo": (-23.55, -46.63),
                "rio de janeiro": (-22.90, -43.17),
                "brasília": (-15.78, -47.93),
                "brasilia": (-15.78, -47.93),
                "belém": (-1.45, -48.50),
                "belem": (-1.45, -48.50),
                "curitiba": (-25.42, -49.27),
                "porto alegre": (-30.03, -51.23),
                "salvador": (-12.97, -38.51),
                "recife": (-8.05, -34.88),
                "fortaleza": (-3.71, -38.54),
            }
            c_key = cidade.strip().lower()
            lat, lon = coords.get(c_key, (-3.10, -60.02))

            if st.button(f"📥 Buscar {ano} via ERA5 Reanalysis", key=f"btn_era5_{prefixo}", width="stretch"):
                with st.spinner(f"Buscando histórico de {ano} para {cidade}..."):
                    try:
                        dataset, csv_bytes = fetch_annual_dataset(lat, lon, cidade, ano)
                        st.session_state[f"cached_dataset_{prefixo}"] = dataset
                        st.success(f"Ano {ano} ({len(dataset.data):,} registros) baixado com sucesso!")
                    except Exception as exc:
                        st.error(f"Erro na consulta ERA5: {exc}")

            if f"cached_dataset_{prefixo}" in st.session_state:
                dataset = st.session_state[f"cached_dataset_{prefixo}"]

        if dataset is not None:
            nome, ano = _identificar_ano_e_nome(dataset)
            st.caption(f"✅ **Identificado:** {nome} — Ano: **{ano}** ({len(dataset.data):,} horas)")

        return dataset


def render_comparison_tab() -> None:
    """Renderiza a aba completa de comparação interanual entre dois CSVs/anos."""
    is_dark = st.session_state.get("dark_mode", True)
    template = "plotly_dark" if is_dark else "plotly_white"

    st.subheader("⚖️ Comparação Interanual de Séries Meteorológicas")
    st.write(
        "Selecione ou envie dois arquivos CSV de anos distintos (do mesmo local ou de estações diferentes a seu critério) "
        "para analisar contrastes térmicos, volumes pluviométricos acumulados e o comportamento mês a mês."
    )

    col_a, col_b = st.columns(2)
    with col_a:
        dataset_a = _carregar_dataset_seletor("a", "📅 Ano Base / Referência (Dataset A)", default_index=0)
    with col_b:
        dataset_b = _carregar_dataset_seletor("b", "📅 Ano de Comparação (Dataset B)", default_index=1)

    if dataset_a is None or dataset_b is None:
        st.info("👈 Selecione ou envie o **Dataset A** e o **Dataset B** acima para gerar a análise comparativa completa.")
        return

    df_a = dataset_a.data.copy()
    df_b = dataset_b.data.copy()

    nome_a, ano_a = _identificar_ano_e_nome(dataset_a)
    nome_b, ano_b = _identificar_ano_e_nome(dataset_b)

    # Hero card comparativo
    st.markdown(
        f"""
<div class="hero-weather" style="margin-top:1rem; margin-bottom:1.5rem;">
    <div style="flex:1;">
        <span class="hero-badge" style="background:#F59E0B; color:#000;">ANO BASE A</span>
        <h3 class="hero-title">{nome_a}</h3>
        <div class="hero-sub">Ano: <b>{ano_a}</b> • {len(df_a):,} registros horários</div>
    </div>
    <div style="text-align:center; padding: 0 1.5rem;">
        <div style="font-size:1.8rem; font-weight:800; color:{'#38BDF8' if is_dark else '#2563EB'};">VS</div>
        <span style="font-size:0.75rem; color:{'#94A3B8' if is_dark else '#64748B'}; font-weight:600;">COMPARAÇÃO</span>
    </div>
    <div style="flex:1; text-align:right;">
        <span class="hero-badge" style="background:#2563EB; color:#FFF;">ANO COMPARATIVO B</span>
        <h3 class="hero-title">{nome_b}</h3>
        <div class="hero-sub">Ano: <b>{ano_b}</b> • {len(df_b):,} registros horários</div>
    </div>
</div>
        """,
        unsafe_allow_html=True,
    )

    # Cálculos estatísticos gerais
    t_med_a = df_a["temp_max_c"].mean()
    t_med_b = df_b["temp_max_c"].mean()
    delta_t_med = t_med_b - t_med_a

    t_max_a = df_a["temp_max_c"].max()
    t_max_b = df_b["temp_max_c"].max()

    t_min_a = df_a["temp_min_c"].min()
    t_min_b = df_b["temp_min_c"].min()

    rain_a = df_a["precipitacao_mm"].sum()
    rain_b = df_b["precipitacao_mm"].sum()
    delta_rain = rain_b - rain_a
    pct_rain = ((rain_b - rain_a) / rain_a * 100) if rain_a > 0 else 0.0

    dias_rain_a = int((df_a.groupby("dia")["precipitacao_mm"].sum() > 0.2).sum())
    dias_rain_b = int((df_b.groupby("dia")["precipitacao_mm"].sum() > 0.2).sum())
    delta_dias = dias_rain_b - dias_rain_a

    max_rain_24h_a = df_a.groupby("dia")["precipitacao_mm"].sum().max()
    max_rain_24h_b = df_b.groupby("dia")["precipitacao_mm"].sum().max()

    # Painel de 6 KPIs Comparativos
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric(
        "🌡️ Temp. Média Anual",
        f"{br_number(t_med_b)} °C",
        delta=f"{'+' if delta_t_med >= 0 else ''}{delta_t_med:.1f} °C vs {ano_a}",
        delta_color="inverse" if delta_t_med > 0.3 else "normal",
        help=f"Média anual no Ano B ({ano_b}) vs Ano A ({ano_a}: {t_med_a:.1f} °C)",
    )
    k2.metric(
        "🔥 Temp. Máxima Absoluta",
        f"{br_number(t_max_b)} °C",
        delta=f"{'+' if t_max_b - t_max_a >= 0 else ''}{t_max_b - t_max_a:.1f} °C",
        delta_color="off",
        help=f"Ano A ({ano_a}): {t_max_a:.1f} °C | Ano B ({ano_b}): {t_max_b:.1f} °C",
    )
    k3.metric(
        "❄️ Temp. Mínima Absoluta",
        f"{br_number(t_min_b)} °C",
        delta=f"{'+' if t_min_b - t_min_a >= 0 else ''}{t_min_b - t_min_a:.1f} °C",
        delta_color="off",
        help=f"Ano A ({ano_a}): {t_min_a:.1f} °C | Ano B ({ano_b}): {t_min_b:.1f} °C",
    )
    k4.metric(
        "🌧️ Chuva Total Acumulada",
        f"{br_number(rain_b)} mm",
        delta=f"{'+' if delta_rain >= 0 else ''}{delta_rain:.1f} mm ({'+' if pct_rain >= 0 else ''}{pct_rain:.1f}%)",
        delta_color="normal" if delta_rain >= 0 else "inverse",
        help=f"Volume anual: {ano_a} acumulou {rain_a:.1f} mm vs {ano_b} com {rain_b:.1f} mm",
    )
    k5.metric(
        "☔ Dias de Chuva (>0.2mm)",
        f"{dias_rain_b} dias",
        delta=f"{'+' if delta_dias >= 0 else ''}{delta_dias} dias vs {ano_a}",
        delta_color="off",
        help=f"Ano A ({ano_a}): {dias_rain_a} dias | Ano B ({ano_b}): {dias_rain_b} dias",
    )
    k6.metric(
        "🌊 Maior Chuva em 24h",
        f"{br_number(max_rain_24h_b)} mm",
        delta=f"{'+' if max_rain_24h_b - max_rain_24h_a >= 0 else ''}{max_rain_24h_b - max_rain_24h_a:.1f} mm",
        delta_color="off",
        help=f"Pico diário: {ano_a} teve {max_rain_24h_a:.1f} mm vs {ano_b} com {max_rain_24h_b:.1f} mm",
    )

    st.markdown("---")

    # Agregação Mensal para Gráficos
    m_a = (
        df_a.groupby("mes")
        .agg(
            temp_media_a=("temp_max_c", "mean"),
            temp_max_a=("temp_max_c", "max"),
            temp_min_a=("temp_min_c", "min"),
            chuva_total_a=("precipitacao_mm", "sum"),
        )
        .reset_index()
    )

    m_b = (
        df_b.groupby("mes")
        .agg(
            temp_media_b=("temp_max_c", "mean"),
            temp_max_b=("temp_max_c", "max"),
            temp_min_b=("temp_min_c", "min"),
            chuva_total_b=("precipitacao_mm", "sum"),
        )
        .reset_index()
    )

    comp_m = pd.merge(m_a, m_b, on="mes", how="outer").sort_values("mes").reset_index(drop=True)
    comp_m["mes_nome"] = comp_m["mes"].apply(lambda m: MESES_NOMES[int(m) - 1] if 1 <= m <= 12 else str(m))
    comp_m["mes_abrev"] = comp_m["mes"].apply(lambda m: MESES_ABREV[int(m) - 1] if 1 <= m <= 12 else str(m))
    comp_m["delta_temp"] = comp_m["temp_media_b"] - comp_m["temp_media_a"]
    comp_m["delta_chuva"] = comp_m["chuva_total_b"] - comp_m["chuva_total_a"]
    comp_m["pct_chuva"] = comp_m.apply(
        lambda r: ((r["delta_chuva"] / r["chuva_total_a"] * 100) if r["chuva_total_a"] > 0 else 0.0), axis=1
    )

    # Cores de tipografia e grade para alto contraste nos modos escuro e claro
    chart_text_color = "#E2E8F0" if is_dark else "#0F172A"
    grid_color = "rgba(148, 163, 184, 0.15)" if is_dark else "rgba(100, 116, 139, 0.18)"

    # 1. Gráficos Comparativos Principais
    g_col1, g_col2 = st.columns(2)

    with g_col1:
        st.markdown(f"##### 🌡️ Perfil Térmico Mensal: **{ano_a}** vs **{ano_b}**")
        fig_temp = go.Figure()

        # Curva Ano A
        fig_temp.add_trace(
            go.Scatter(
                x=comp_m["mes_abrev"],
                y=comp_m["temp_media_a"],
                name=f"Ano A ({ano_a})",
                mode="lines+markers",
                line=dict(color="#F59E0B" if is_dark else ORANGE, width=3),
                marker=dict(size=7, color="#F59E0B" if is_dark else ORANGE),
                hovertemplate=f"<b>Mês:</b> %{{x}}<br><b>{ano_a}:</b> %{{y:.1f}} °C<extra></extra>",
            )
        )

        # Curva Ano B
        fig_temp.add_trace(
            go.Scatter(
                x=comp_m["mes_abrev"],
                y=comp_m["temp_media_b"],
                name=f"Ano B ({ano_b})",
                mode="lines+markers",
                line=dict(color="#0EA5E9" if is_dark else BLUE, width=3),
                marker=dict(size=7, color="#0EA5E9" if is_dark else BLUE),
                fill="tonexty",
                fillcolor="rgba(14, 165, 233, 0.12)" if is_dark else "rgba(37, 99, 235, 0.10)",
                hovertemplate=f"<b>Mês:</b> %{{x}}<br><b>{ano_b}:</b> %{{y:.1f}} °C<extra></extra>",
            )
        )

        fig_temp.update_layout(
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
            margin=dict(t=45, b=25, l=40, r=20),
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
                title=dict(text="Temperatura Média (°C)", font=dict(color=chart_text_color)),
                tickfont=dict(color=chart_text_color),
                showgrid=True,
                gridcolor=grid_color,
            ),
        )
        st.plotly_chart(fig_temp, width="stretch", config={"displayModeBar": "hover", "displaylogo": False})

    with g_col2:
        st.markdown(f"##### 🌧️ Precipitação Mensal Lado a Lado (mm)")
        fig_rain = go.Figure()

        fig_rain.add_trace(
            go.Bar(
                x=comp_m["mes_abrev"],
                y=comp_m["chuva_total_a"],
                name=f"Ano A ({ano_a})",
                marker_color="rgba(245, 158, 11, 0.85)" if is_dark else "rgba(234, 88, 12, 0.85)",
                hovertemplate=f"<b>Mês:</b> %{{x}}<br><b>{ano_a}:</b> %{{y:.1f}} mm<extra></extra>",
            )
        )

        fig_rain.add_trace(
            go.Bar(
                x=comp_m["mes_abrev"],
                y=comp_m["chuva_total_b"],
                name=f"Ano B ({ano_b})",
                marker_color="rgba(14, 165, 233, 0.85)" if is_dark else "rgba(37, 99, 235, 0.85)",
                hovertemplate=f"<b>Mês:</b> %{{x}}<br><b>{ano_b}:</b> %{{y:.1f}} mm<extra></extra>",
            )
        )

        fig_rain.update_layout(
            barmode="group",
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
            margin=dict(t=45, b=25, l=40, r=20),
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
                title=dict(text="Chuva Acumulada (mm)", font=dict(color=chart_text_color)),
                tickfont=dict(color=chart_text_color),
                showgrid=True,
                gridcolor=grid_color,
            ),
        )
        st.plotly_chart(fig_rain, width="stretch", config={"displayModeBar": "hover", "displaylogo": False})

    # 2. Curva de Chuva Acumulada Dia a Dia (Trajetória Anual de 1 a 365)
    st.markdown("##### 📈 Trajetória de Precipitação Acumulada ao Longo do Ano (Dia 1 ao 365)")
    df_daily_a = (
        df_a.groupby("dia")["precipitacao_mm"].sum().reset_index().sort_values("dia").reset_index(drop=True)
    )
    df_daily_a["dia_num"] = range(1, len(df_daily_a) + 1)
    df_daily_a["chuva_acumulada"] = df_daily_a["precipitacao_mm"].cumsum()

    df_daily_b = (
        df_b.groupby("dia")["precipitacao_mm"].sum().reset_index().sort_values("dia").reset_index(drop=True)
    )
    df_daily_b["dia_num"] = range(1, len(df_daily_b) + 1)
    df_daily_b["chuva_acumulada"] = df_daily_b["precipitacao_mm"].cumsum()

    fig_cum = go.Figure()
    fig_cum.add_trace(
        go.Scatter(
            x=df_daily_a["dia_num"],
            y=df_daily_a["chuva_acumulada"],
            name=f"Chuva Acumulada — {ano_a}",
            mode="lines",
            line=dict(color="#F59E0B" if is_dark else ORANGE, width=2.5),
            hovertemplate=f"<b>Dia %{{x}}:</b> %{{y:.1f}} mm acumulados em {ano_a}<extra></extra>",
        )
    )
    fig_cum.add_trace(
        go.Scatter(
            x=df_daily_b["dia_num"],
            y=df_daily_b["chuva_acumulada"],
            name=f"Chuva Acumulada — {ano_b}",
            mode="lines",
            line=dict(color="#0EA5E9" if is_dark else BLUE, width=2.8),
            hovertemplate=f"<b>Dia %{{x}}:</b> %{{y:.1f}} mm acumulados em {ano_b}<extra></extra>",
        )
    )
    fig_cum.update_layout(
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
        margin=dict(t=45, b=25, l=40, r=20),
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
            title=dict(text="Dia do ano (1 a 365)", font=dict(color=chart_text_color)),
            tickfont=dict(color=chart_text_color),
        ),
        yaxis=dict(
            title=dict(text="Chuva Acumulada Total (mm)", font=dict(color=chart_text_color)),
            tickfont=dict(color=chart_text_color),
            showgrid=True,
            gridcolor=grid_color,
        ),
    )
    st.plotly_chart(fig_cum, width="stretch", config={"displayModeBar": "hover", "displaylogo": False})

    # 3. Tabela Comparativa Detalhada
    st.markdown("##### 📋 Tabela Comparativa Mês a Mês")
    tabela_display = comp_m[
        [
            "mes_nome",
            "temp_media_a",
            "temp_media_b",
            "delta_temp",
            "chuva_total_a",
            "chuva_total_b",
            "delta_chuva",
            "pct_chuva",
        ]
    ].copy()

    st.dataframe(
        tabela_display,
        hide_index=True,
        column_config={
            "mes_nome": "Mês",
            "temp_media_a": st.column_config.NumberColumn(f"Temp. Média {ano_a} (°C)", format="%.1f"),
            "temp_media_b": st.column_config.NumberColumn(f"Temp. Média {ano_b} (°C)", format="%.1f"),
            "delta_temp": st.column_config.NumberColumn("Δ Temp (°C)", format="%+.1f"),
            "chuva_total_a": st.column_config.NumberColumn(f"Chuva {ano_a} (mm)", format="%.1f"),
            "chuva_total_b": st.column_config.NumberColumn(f"Chuva {ano_b} (mm)", format="%.1f"),
            "delta_chuva": st.column_config.NumberColumn("Δ Chuva (mm)", format="%+.1f"),
            "pct_chuva": st.column_config.NumberColumn("Variação Chuva (%)", format="%+.1f%%"),
        },
    )

    # Download da tabela comparativa em CSV
    csv_comp_bytes = tabela_display.to_csv(sep=";", decimal=",", index=False).encode("utf-8-sig")
    st.download_button(
        "⬇️ Baixar Tabela Comparativa em CSV",
        data=csv_comp_bytes,
        file_name=f"climaps_comparacao_{ano_a}_vs_{ano_b}.csv",
        mime="text/csv",
        width="stretch",
    )
