import pandas as pd
import streamlit as st

from climaps.core.data_loader import StationDataset


NAVY = "#12355B"
BLUE = "#2878B5"
ORANGE = "#F28C28"


def br_number(value: float | int | None, decimals: int = 1) -> str:
    if value is None or pd.isna(value):
        return "-"
    text = f"{float(value):,.{decimals}f}"
    return text.replace(",", "X").replace(".", ",").replace("X", ".")


def inject_custom_css() -> None:
    st.markdown(
        f"""
<style>
.stApp {{
    background-color: #F2F6FA;
}}
section[data-testid="stSidebar"] {{
    background-color: #FFFFFF;
    border-right: 1px solid #E3EAF2;
}}
.climaps-banner {{
    background: linear-gradient(135deg, {NAVY} 0%, {BLUE} 65%, #3A8FD4 100%);
    color: white;
    padding: 1.4rem 1.8rem;
    border-radius: 16px;
    margin-bottom: 1.2rem;
    border-left: 6px solid {ORANGE};
    box-shadow: 0 10px 25px rgba(18, 53, 91, 0.14);
}}
.climaps-banner h1 {{
    margin: 0;
    font-size: 2rem;
    font-weight: 700;
    letter-spacing: -0.5px;
    color: white;
}}
.climaps-banner p {{
    margin: 0.3rem 0 0 0;
    color: #DCE9F5;
    font-size: 0.95rem;
}}
div[data-testid="stMetric"] {{
    background-color: #FFFFFF;
    border: 1px solid #E2E9F1;
    border-top: 3px solid {BLUE};
    border-radius: 12px;
    padding: 0.95rem 1.1rem;
    box-shadow: 0 4px 12px rgba(18, 53, 91, 0.05);
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}}
div[data-testid="stMetric"]:hover {{
    transform: translateY(-2px);
    box-shadow: 0 8px 18px rgba(18, 53, 91, 0.10);
}}
div[data-testid="stTabs"] button[data-baseweb="tab"] {{
    background-color: #FFFFFF;
    border: 1px solid #DCE6EF;
    border-radius: 999px;
    padding: 0.45rem 1rem;
    margin-right: 0.35rem;
    font-weight: 600;
    color: {NAVY};
}}
div[data-testid="stTabs"] button[aria-selected="true"] {{
    background-color: {NAVY} !important;
    color: #FFFFFF !important;
    border-color: {NAVY} !important;
}}
div[data-testid="stTabs"] div[data-baseweb="tab-highlight"] {{
    display: none;
}}
.stButton > button, .stDownloadButton > button {{
    border-radius: 10px;
    font-weight: 600;
}}
.hero-weather {{
    background: linear-gradient(135deg, #FFFFFF 0%, #F7FAFD 100%);
    border: 1px solid #DCE6EF;
    border-radius: 16px;
    padding: 1.25rem 1.5rem;
    margin: 0.6rem 0 1rem 0;
    box-shadow: 0 6px 18px rgba(18, 53, 91, 0.06);
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 1rem;
}}
.hero-temp {{
    font-size: 2.7rem;
    font-weight: 800;
    color: {NAVY};
    line-height: 1;
}}
.hero-badge {{
    display: inline-block;
    background-color: #EAF2FA;
    color: {BLUE};
    padding: 0.25rem 0.7rem;
    border-radius: 999px;
    font-size: 0.82rem;
    font-weight: 600;
    margin-bottom: 0.4rem;
}}
</style>
        """,
        unsafe_allow_html=True,
    )


def render_header() -> None:
    dataset: StationDataset | None = st.session_state.get("dataset")
    df: pd.DataFrame | None = st.session_state.get("df")

    if dataset is not None and df is not None:
        meta = dataset.metadata
        subtitle = (
            f"Estação {meta.get('nome', 'Desconhecida')} "
            f"({meta.get('codigo_estacao', '-')}) • "
            f"{br_number(len(df), 0)} registros • "
            f"Fonte: {dataset.source.name}"
        )
    else:
        subtitle = "Clima ao vivo em qualquer lugar do mundo • Análise meteorológica com Python"

    st.markdown(
        f"""
<div class="climaps-banner">
<h1>☁️ ClimaPS</h1>
<p>{subtitle}</p>
</div>
        """,
        unsafe_allow_html=True,
    )