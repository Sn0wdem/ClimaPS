import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from climaps.core.analysis import (
    MESES_PT,
    calculate_kpis,
    correlation_matrix,
    daily_summary,
    generate_insights,
    monthly_summary,
    quality_report,
)
from climaps.ui_styles import BLUE, ORANGE, br_number


def render_summary_tab(filtered: pd.DataFrame, full_df: pd.DataFrame) -> None:
    if filtered.empty:
        st.warning("Nenhum registro atende aos filtros selecionados.")
        return

    kpis = calculate_kpis(filtered)
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Registros", br_number(kpis["registros"], 0))
    c2.metric("Chuva acumulada", f"{br_number(kpis['precipitacao_total'])} mm")
    c3.metric("Temp. máx. média", f"{br_number(kpis['temp_max_media'])} °C")
    c4.metric("Temp. mín. média", f"{br_number(kpis['temp_min_media'])} °C")
    c5.metric("Completude", f"{br_number(kpis['completude'])}%")

    st.subheader("💡 Insights do recorte")
    for insight in generate_insights(filtered):
        st.info(insight)

    col_left, col_right = st.columns([1.4, 1])
    with col_left:
        with st.container(border=True):
            st.subheader("📅 Resumo mensal")
            mensal = monthly_summary(filtered).copy()
            st.dataframe(
                mensal[["mes_nome", "registros", "precipitacao_mm", "temp_max_media", "temp_min_media", "horas_com_chuva"]],
                hide_index=True,
                column_config={
                    "mes_nome": "Mês",
                    "registros": st.column_config.NumberColumn("Registros", format="%d"),
                    "precipitacao_mm": st.column_config.NumberColumn("Chuva (mm)", format="%.1f"),
                    "temp_max_media": st.column_config.NumberColumn("Máx. média (°C)", format="%.1f"),
                    "temp_min_media": st.column_config.NumberColumn("Mín. média (°C)", format="%.1f"),
                    "horas_com_chuva": st.column_config.NumberColumn("Horas c/ chuva", format="%d"),
                },
            )

    with col_right:
        with st.container(border=True):
            st.subheader("🩺 Qualidade da base completa")
            report = quality_report(full_df)
            missing = report["valores_ausentes"]
            outliers = report["outliers_iqr"]
            qualidade_df = pd.DataFrame(
                [
                    {"Indicador": "Lacunas de timestamp", "Valor": report["timestamps_ausentes"]},
                    {"Indicador": "Timestamps duplicados", "Valor": report["timestamps_duplicados"]},
                    {"Indicador": "Chuva negativa", "Valor": report["chuva_negativa"]},
                    {"Indicador": "Máxima < Mínima", "Valor": report["temp_inconsistente"]},
                    {"Indicador": "Ausentes em chuva", "Valor": missing["precipitacao_mm"]},
                    {"Indicador": "Ausentes em temp. máx.", "Valor": missing["temp_max_c"]},
                    {"Indicador": "Ausentes em temp. mín.", "Valor": missing["temp_min_c"]},
                    {"Indicador": "Outliers (IQR)", "Valor": sum(outliers.values())},
                ]
            )
            st.dataframe(qualidade_df, hide_index=True)


def render_charts_tab(filtered: pd.DataFrame) -> None:
    if filtered.empty:
        st.warning("Nenhum dado disponível para os filtros atuais.")
        return

    col_ctrl1, col_ctrl2 = st.columns([1, 1])
    with col_ctrl1:
        granularity = st.radio("Agrupamento", ["Por mês", "Por dia"], horizontal=True)

    if granularity == "Por mês":
        chart_df = monthly_summary(filtered).copy()
        chart_df["label"] = chart_df["mes_nome"]
        x_title = "Mês"
    else:
        months = sorted(int(m) for m in filtered["mes"].dropna().unique())
        with col_ctrl2:
            selected_month = st.selectbox(
                "Filtrar mês",
                options=["todos", *months],
                format_func=lambda m: "Todos os meses" if m == "todos" else MESES_PT.get(m, str(m)),
            )
        chart_df = daily_summary(filtered).copy()
        if selected_month != "todos":
            chart_df = chart_df[chart_df["dia"].dt.month == selected_month]
        chart_df["label"] = chart_df["dia"].dt.strftime("%d/%m")
        x_title = "Dia"

    if chart_df.empty:
        st.info("Sem registros para a seleção atual.")
        return

    with st.container(border=True):
        fig_rain = px.bar(
            chart_df,
            x="label",
            y="precipitacao_mm",
            title="Precipitação acumulada (mm)",
            labels={"label": x_title, "precipitacao_mm": "Chuva (mm)"},
            color="precipitacao_mm",
            color_continuous_scale="Blues",
        )
        fig_rain.update_layout(
            template="plotly_white",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            coloraxis_showscale=False,
            hovermode="x unified",
            height=360,
            margin=dict(t=45, b=20),
        )
        st.plotly_chart(fig_rain, width="stretch")

    with st.container(border=True):
        fig_temp = go.Figure()
        fig_temp.add_trace(
            go.Scatter(
                x=chart_df["label"],
                y=chart_df["temp_max_media"],
                name="Temp. máxima média (°C)",
                mode="lines+markers",
                line=dict(color=ORANGE, width=2.5),
            )
        )
        fig_temp.add_trace(
            go.Scatter(
                x=chart_df["label"],
                y=chart_df["temp_min_media"],
                name="Temp. mínima média (°C)",
                mode="lines+markers",
                line=dict(color=BLUE, width=2.5),
                fill="tonexty",
                fillcolor="rgba(40, 120, 181, 0.12)",
            )
        )
        fig_temp.update_layout(
            title="Amplitude térmica média (°C)",
            xaxis_title=x_title,
            yaxis_title="Temperatura (°C)",
            template="plotly_white",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=380,
            margin=dict(t=55, b=20),
        )
        st.plotly_chart(fig_temp, width="stretch")

    with st.container(border=True):
        corr = correlation_matrix(filtered).rename(
            index={"precipitacao_mm": "Chuva", "temp_max_c": "Temp. máx.", "temp_min_c": "Temp. mín."},
            columns={"precipitacao_mm": "Chuva", "temp_max_c": "Temp. máx.", "temp_min_c": "Temp. mín."},
        )
        fig_corr = px.imshow(
            corr,
            text_auto=".2f",
            zmin=-1,
            zmax=1,
            color_continuous_scale="RdBu_r",
            title="Correlação entre variáveis",
        )
        fig_corr.update_layout(
            template="plotly_white",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=350,
            margin=dict(t=45, b=20),
        )
        st.plotly_chart(fig_corr, width="stretch")


def render_table_tab(full_df: pd.DataFrame) -> None:
    st.caption("Edite chuva, temperatura máxima ou mínima diretamente na tabela e clique em **Salvar edições**.")
    editable_cols = ["data_hora", "precipitacao_mm", "temp_max_c", "temp_min_c"]

    with st.form("editor_form"):
        edited = st.data_editor(
            full_df[editable_cols],
            disabled=["data_hora"],
            hide_index=True,
            height=480,
            column_config={
                "data_hora": st.column_config.DatetimeColumn("Data e hora", format="DD/MM/YYYY HH:mm"),
                "precipitacao_mm": st.column_config.NumberColumn("Chuva (mm)", min_value=0.0, step=0.1, format="%.1f"),
                "temp_max_c": st.column_config.NumberColumn("Temp. máx. (°C)", step=0.1, format="%.1f"),
                "temp_min_c": st.column_config.NumberColumn("Temp. mín. (°C)", step=0.1, format="%.1f"),
            },
        )
        submitted = st.form_submit_button("💾 Salvar edições", type="primary")

    if submitted:
        for col in ["precipitacao_mm", "temp_max_c", "temp_min_c"]:
            st.session_state["df"].loc[edited.index, col] = pd.to_numeric(edited[col], errors="coerce")
        st.success("Edições salvas na sessão atual! Os gráficos e KPIs já foram atualizados.")
        st.rerun()


def render_explorer_tab(filtered: pd.DataFrame) -> None:
    st.caption(f"Exibindo {br_number(len(filtered), 0)} registros conforme os filtros da barra lateral.")
    st.dataframe(
        filtered[["data_hora", "precipitacao_mm", "temp_max_c", "temp_min_c"]],
        hide_index=True,
        height=480,
        column_config={
            "data_hora": st.column_config.DatetimeColumn("Data e hora", format="DD/MM/YYYY HH:mm"),
            "precipitacao_mm": st.column_config.NumberColumn("Chuva (mm)", format="%.1f"),
            "temp_max_c": st.column_config.NumberColumn("Temp. máx. (°C)", format="%.1f"),
            "temp_min_c": st.column_config.NumberColumn("Temp. mín. (°C)", format="%.1f"),
        },
    )