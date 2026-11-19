from datetime import datetime
from pathlib import Path
import re

import pandas as pd
import streamlit as st

from climaps.core.analysis import FilterSpec, apply_filters
from climaps.core.data_loader import StationDataset, load_station_csv
from climaps.ui_styles import inject_custom_css, render_header
from climaps.ui_tabs import (
    render_charts_tab,
    render_explorer_tab,
    render_summary_tab,
    render_table_tab,
)
from climaps.ui_world import render_world_live_tab


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
IMPORT_DIR = DATA_DIR / "importados"
EXPORT_DIR = BASE_DIR / "exportacoes"
SAMPLE_CSV = DATA_DIR / "dados_A101_H_2014.csv"


def safe_filename(name: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", Path(name).name).strip("._")
    return safe or "dados.csv"


def sql_value(value, is_date_only: bool = False) -> str:
    if pd.isna(value):
        return "NULL"
    if isinstance(value, pd.Timestamp):
        fmt = "%Y-%m-%d" if is_date_only else "%Y-%m-%d %H:%M:%S"
        return f"'{value.strftime(fmt)}'"
    if hasattr(value, "strftime"):
        return f"'{value:%Y-%m-%d}'"
    if isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"
    return str(float(value)) if isinstance(value, float) else str(value)


def build_sql_script(df: pd.DataFrame) -> str:
    columns = [
        "data",
        "hora",
        "data_hora",
        "precipitacao_mm",
        "temp_max_c",
        "temp_min_c",
        "hora_num",
        "mes",
        "dia",
    ]
    sql_lines = [
        "DROP TABLE IF EXISTS observacoes_meteorologicas;",
        "CREATE TABLE observacoes_meteorologicas (",
        "    data DATE,",
        "    hora INTEGER,",
        "    data_hora TIMESTAMP,",
        "    precipitacao_mm REAL,",
        "    temp_max_c REAL,",
        "    temp_min_c REAL,",
        "    hora_num INTEGER,",
        "    mes INTEGER,",
        "    dia DATE",
        ");",
        "",
    ]
    for _, row in df[columns].iterrows():
        values = ", ".join(
            sql_value(row[col], is_date_only=(col in {"data", "dia"})) for col in columns
        )
        sql_lines.append(
            f"INSERT INTO observacoes_meteorologicas ({', '.join(columns)}) VALUES ({values});"
        )
    return "\n".join(sql_lines) + "\n"


def load_into_session(path: Path) -> None:
    dataset: StationDataset = load_station_csv(path)
    st.session_state["dataset"] = dataset
    st.session_state["df"] = dataset.data.copy()


def render_sidebar() -> FilterSpec | None:
    with st.sidebar:
        st.header("📂 Dados históricos (CSV)")
        uploaded = st.file_uploader("Importar CSV do INMET", type=["csv"])
        if uploaded is not None:
            sig = (uploaded.name, uploaded.size)
            if st.session_state.get("last_upload_sig") != sig:
                IMPORT_DIR.mkdir(parents=True, exist_ok=True)
                stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                dest = IMPORT_DIR / f"{stamp}_{safe_filename(uploaded.name)}"
                dest.write_bytes(uploaded.getvalue())
                load_into_session(dest)
                st.session_state["last_upload_sig"] = sig
                st.toast(f"Arquivo importado: {dest.name}", icon="✅")

        available_files: list[Path] = []
        if SAMPLE_CSV.exists():
            available_files.append(SAMPLE_CSV)
        if IMPORT_DIR.exists():
            available_files.extend(sorted(IMPORT_DIR.glob("*.csv"), reverse=True))

        if available_files:
            chosen = st.selectbox(
                "Ou carregar arquivo salvo",
                options=available_files,
                format_func=lambda p: f"{p.parent.name}/{p.name}",
            )
            if st.button("Carregar arquivo selecionado", width="stretch"):
                load_into_session(chosen)
                st.rerun()

        df: pd.DataFrame | None = st.session_state.get("df")
        if df is None or df.empty:
            return None

        st.divider()
        st.header("🎛️ Filtros de análise")

        valid_dt = df["data_hora"].dropna()
        min_date = valid_dt.min().date()
        max_date = valid_dt.max().date()

        date_range = st.date_input(
            "Período",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            key=f"period_{min_date}_{max_date}",
        )
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_d, end_d = date_range
        else:
            start_d = end_d = date_range[0] if isinstance(date_range, tuple) else date_range

        hour_start, hour_end = st.slider("Faixa de horário", 0, 23, (0, 23))
        rainy_only = st.checkbox("Somente horas com chuva", value=False)

        return FilterSpec(
            start=pd.Timestamp(start_d),
            end=pd.Timestamp(end_d),
            hour_start=hour_start,
            hour_end=hour_end,
            rainy_only=rainy_only,
        )


def render_export_tab(full_df: pd.DataFrame, filtered: pd.DataFrame) -> None:
    scope = st.radio(
        "Dados para exportação",
        ["Base completa (com edições)", "Apenas recorte filtrado"],
        horizontal=True,
    )
    target_df = full_df if scope.startswith("Base") else filtered
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    csv_bytes = target_df.to_csv(
        sep=";",
        decimal=",",
        index=False,
        date_format="%Y-%m-%d %H:%M",
    ).encode("utf-8-sig")

    sql_text = build_sql_script(target_df)

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "⬇️ Baixar CSV",
            data=csv_bytes,
            file_name=f"climaps_dados_{stamp}.csv",
            mime="text/csv",
            width="stretch",
        )
    with col2:
        st.download_button(
            "🗄️ Baixar Script SQL",
            data=sql_text.encode("utf-8"),
            file_name=f"climaps_dados_{stamp}.sql",
            mime="application/sql",
            width="stretch",
        )

    if st.button("Salvar cópias também na pasta exportacoes/"):
        EXPORT_DIR.mkdir(exist_ok=True)
        csv_path = EXPORT_DIR / f"dados_editados_{stamp}.csv"
        sql_path = EXPORT_DIR / f"dados_meteorologicos_{stamp}.sql"
        csv_path.write_bytes(csv_bytes)
        sql_path.write_text(sql_text, encoding="utf-8")
        st.success(f"Arquivos salvos em `exportacoes/`: `{csv_path.name}` e `{sql_path.name}`.")


def main() -> None:
    st.set_page_config(
        page_title="ClimaPS - Dados Meteorológicos",
        page_icon="☁️",
        layout="wide",
    )
    inject_custom_css()
    render_header()
    filter_spec = render_sidebar()

    df: pd.DataFrame | None = st.session_state.get("df")
    has_dataset = df is not None and not df.empty and filter_spec is not None

    tab_mundo, tab_resumo, tab_graficos, tab_tabela, tab_explorador, tab_exportar = st.tabs(
        ["🌍 Mundo Ao Vivo", "📊 Resumo", "📈 Gráficos", "✏️ Tabela editável", "🔍 Explorador", "⬇️ Exportar"]
    )

    with tab_mundo:
        render_world_live_tab()

    if has_dataset:
        filtered = apply_filters(df, filter_spec)
        with tab_resumo:
            render_summary_tab(filtered, df)
        with tab_graficos:
            render_charts_tab(filtered)
        with tab_tabela:
            render_table_tab(df)
        with tab_explorador:
            render_explorer_tab(filtered)
        with tab_exportar:
            render_export_tab(df, filtered)
    else:
        for tab in (tab_resumo, tab_graficos, tab_tabela, tab_explorador, tab_exportar):
            with tab:
                st.info("Importe um CSV na barra lateral ou clique em **Carregar 30 dias nas abas** na aba Mundo Ao Vivo.")


if __name__ == "__main__":
    main()