import pandas as pd  # Importado para usar pd.isna na verificação de valores ausentes
import streamlit as st  # Framework da interface web

from climaps.core.data_loader import StationDataset  # Tipo usado para leitura da sessão no cabeçalho


NAVY = "#12355B"  # Cor azul-marinho principal da identidade visual
BLUE = "#2878B5"  # Cor azul intermediária usada em bordas, gradientes e gráficos
ORANGE = "#F28C28"  # Cor laranja de destaque (borda do banner e linha de temperatura máxima)


def br_number(value: float | int | None, decimals: int = 1) -> str:  # Formata números no padrão brasileiro (vírgula decimal, ponto milhar)
    if value is None or pd.isna(value):  # Se o valor for None ou NaN
        return "-"  # Retorna um hífen indicando ausência de dado
    text = f"{float(value):,.{decimals}f}"  # Formata no padrão americano (ex.: 1,234.5)
    return text.replace(",", "X").replace(".", ",").replace("X", ".")  # Troca separadores: "," -> "X", "." -> ",", "X" -> "." (ex.: 1.234,5)


def format_datetime_friendly(value: str | pd.Timestamp | None) -> str:
    """Formata datas e timestamps para formato amigável brasileiro (ex: 19/11/2026 às 16:00)."""
    if not value or pd.isna(value):  # Se nulo ou vazio
        return "-"
    if isinstance(value, str) and " às " in value:  # Se já estiver formatado
        return value
    try:
        dt = pd.to_datetime(value)  # Converte texto ISO ou objeto para Timestamp
        return dt.strftime("%d/%m/%Y às %H:%M")  # Formata como DD/MM/AAAA às HH:MM
    except Exception:
        return str(value)  # Retorna representação em string caso falhe o parse


def inject_custom_css(is_dark: bool = True) -> None:  # Injeta CSS personalizado na página do Streamlit conforme o tema ativo
    if is_dark:  # Estilos para o Tema Escuro
        app_bg = "#0E1726"
        text_color = "#E2E8F0"
        sidebar_bg = "#182234"
        sidebar_border = "#27354A"
        banner_bg = "linear-gradient(135deg, #0A192F 0%, #163664 65%, #1E4E8C 100%)"
        banner_shadow = "0 10px 25px rgba(0, 0, 0, 0.35)"
        banner_sub = "#CBD5E1"
        metric_bg = "#182234"
        metric_border = "#27354A"
        metric_top = "#3A8FD4"
        metric_shadow = "0 4px 12px rgba(0, 0, 0, 0.25)"
        metric_hover_shadow = "0 8px 18px rgba(0, 0, 0, 0.40)"
        tab_bg = "#182234"
        tab_border = "#27354A"
        tab_color = "#CBD5E1"
        tab_sel_bg = "#2878B5"
        tab_sel_color = "#FFFFFF"
        hero_bg = "linear-gradient(135deg, #182234 0%, #111A29 100%)"
        hero_border = "#27354A"
        hero_shadow = "0 6px 18px rgba(0, 0, 0, 0.25)"
        hero_title = "#F1F5F9"
        hero_sub = "#94A3B8"
        hero_code_bg = "#27354A"
        hero_code_color = "#7DD3FC"
        hero_code_border = "1px solid #334155"
        hero_temp = "#F1F5F9"
        hero_badge_bg = "#1E3A5F"
        hero_badge_color = "#7DD3FC"
        kpi_bg = "#182234"
        kpi_border = "#27354A"
        kpi_shadow = "0 4px 12px rgba(0, 0, 0, 0.25)"
        kpi_hover_shadow = "0 8px 18px rgba(0, 0, 0, 0.40)"
        kpi_label = "#94A3B8"
        kpi_val = "#F1F5F9"
        kpi_hot_bg = "rgba(239, 68, 68, 0.2)"
        kpi_hot_color = "#FCA5A5"
        kpi_hot_border = "rgba(239, 68, 68, 0.35)"
        kpi_cold_bg = "rgba(59, 130, 246, 0.2)"
        kpi_cold_color = "#93C5FD"
        kpi_cold_border = "rgba(59, 130, 246, 0.35)"
        kpi_wind_bg = "rgba(6, 182, 212, 0.2)"
        kpi_wind_color = "#67E8F9"
        kpi_wind_border = "rgba(6, 182, 212, 0.35)"
    else:  # Estilos para o Tema Claro
        app_bg = "#F2F6FA"
        text_color = "#243447"
        sidebar_bg = "#FFFFFF"
        sidebar_border = "#E3EAF2"
        banner_bg = f"linear-gradient(135deg, {NAVY} 0%, {BLUE} 65%, #3A8FD4 100%)"
        banner_shadow = "0 10px 25px rgba(18, 53, 91, 0.14)"
        banner_sub = "#DCE9F5"
        metric_bg = "#FFFFFF"
        metric_border = "#E2E9F1"
        metric_top = BLUE
        metric_shadow = "0 4px 12px rgba(18, 53, 91, 0.05)"
        metric_hover_shadow = "0 8px 18px rgba(18, 53, 91, 0.10)"
        tab_bg = "#FFFFFF"
        tab_border = "#DCE6EF"
        tab_color = NAVY
        tab_sel_bg = NAVY
        tab_sel_color = "#FFFFFF"
        hero_bg = "linear-gradient(135deg, #FFFFFF 0%, #F7FAFD 100%)"
        hero_border = "#DCE6EF"
        hero_shadow = "0 6px 18px rgba(18, 53, 91, 0.06)"
        hero_title = NAVY
        hero_sub = "#60758A"
        hero_code_bg = "#EAF2FA"
        hero_code_color = NAVY
        hero_code_border = "1px solid #DCE6EF"
        hero_temp = NAVY
        hero_badge_bg = "#EAF2FA"
        hero_badge_color = BLUE
        kpi_bg = "#FFFFFF"
        kpi_border = "#E2E9F1"
        kpi_shadow = "0 4px 12px rgba(18, 53, 91, 0.05)"
        kpi_hover_shadow = "0 8px 18px rgba(18, 53, 91, 0.10)"
        kpi_label = "#60758A"
        kpi_val = NAVY
        kpi_hot_bg = "#FEE2E2"
        kpi_hot_color = "#DC2626"
        kpi_hot_border = "#FECACA"
        kpi_cold_bg = "#DBEAFE"
        kpi_cold_color = "#1D4ED8"
        kpi_cold_border = "#BFDBFE"
        kpi_wind_bg = "#CFFAFE"
        kpi_wind_color = "#0E7490"
        kpi_wind_border = "#A5F3FC"

    st.markdown(  # Escreve um bloco HTML/CSS bruto na página
        f"""
<style>
.stApp {{
    background-color: {app_bg};
    color: {text_color};
}}
section[data-testid="stSidebar"] {{
    background-color: {sidebar_bg};
    border-right: 1px solid {sidebar_border};
}}
.climaps-banner {{
    background: {banner_bg};
    color: white;
    padding: 1.4rem 1.8rem;
    border-radius: 16px;
    margin-bottom: 1.2rem;
    border-left: 6px solid {ORANGE};
    box-shadow: {banner_shadow};
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
    color: {banner_sub};
    font-size: 0.95rem;
}}
div[data-testid="stMetric"] {{
    background-color: {metric_bg};
    border: 1px solid {metric_border};
    border-top: 3px solid {metric_top};
    border-radius: 12px;
    padding: 0.95rem 1.1rem;
    box-shadow: {metric_shadow};
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}}
div[data-testid="stMetric"]:hover {{
    transform: translateY(-2px);
    box-shadow: {metric_hover_shadow};
}}
div[data-testid="stTabs"] button[data-baseweb="tab"] {{
    background-color: {tab_bg};
    border: 1px solid {tab_border};
    border-radius: 999px;
    padding: 0.45rem 1rem;
    margin-right: 0.35rem;
    font-weight: 600;
    color: {tab_color};
}}
div[data-testid="stTabs"] button[aria-selected="true"] {{
    background-color: {tab_sel_bg} !important;
    color: {tab_sel_color} !important;
    border-color: {tab_sel_bg} !important;
}}
div[data-testid="stTabs"] div[data-baseweb="tab-highlight"] {{
    display: none;
}}
.stButton > button, .stDownloadButton > button {{
    border-radius: 10px;
    font-weight: 600;
}}
.hero-weather {{
    background: {hero_bg};
    border: 1px solid {hero_border};
    border-radius: 16px;
    padding: 1.25rem 1.5rem;
    margin: 0.6rem 0 1rem 0;
    box-shadow: {hero_shadow};
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 1rem;
}}
.hero-title {{
    margin: 0;
    color: {hero_title};
    font-size: 1.4rem;
    font-weight: 700;
}}
.hero-sub {{
    color: {hero_sub};
    font-size: 0.92rem;
    margin-top: 4px;
}}
.hero-sub code {{
    background-color: {hero_code_bg};
    color: {hero_code_color};
    border: {hero_code_border};
    padding: 2px 7px;
    border-radius: 6px;
    font-size: 0.88rem;
    font-family: inherit;
    font-weight: 600;
}}
.hero-temp {{
    font-size: 2.7rem;
    font-weight: 800;
    color: {hero_temp};
    line-height: 1;
}}
.hero-sensacao {{
    color: {hero_sub};
    font-size: 0.9rem;
    margin-top: 4px;
}}
.hero-sensacao b {{
    color: {hero_title};
}}
.hero-badge {{
    display: inline-block;
    background-color: {hero_badge_bg};
    color: {hero_badge_color};
    padding: 0.25rem 0.7rem;
    border-radius: 999px;
    font-size: 0.82rem;
    font-weight: 600;
    margin-bottom: 0.4rem;
}}
.kpi-podium-card {{
    background-color: {kpi_bg};
    border: 1px solid {kpi_border};
    border-radius: 12px;
    padding: 0.95rem 1.1rem;
    box-shadow: {kpi_shadow};
    min-height: 110px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}}
.kpi-podium-card:hover {{
    transform: translateY(-2px);
    box-shadow: {kpi_hover_shadow};
}}
.kpi-podium-card.kpi-hot {{
    border-top: 3px solid #EF5350;
}}
.kpi-podium-card.kpi-cold {{
    border-top: 3px solid #3B82F6;
}}
.kpi-podium-card.kpi-wind {{
    border-top: 3px solid #06B6D4;
}}
.kpi-podium-label {{
    font-size: 0.85rem;
    font-weight: 600;
    color: {kpi_label};
    margin-bottom: 0.25rem;
}}
.kpi-podium-value {{
    font-size: 1.3rem;
    font-weight: 700;
    color: {kpi_val};
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    line-height: 1.25;
    margin-bottom: 0.5rem;
}}
.kpi-badge-wrap {{
    display: flex;
    align-items: center;
}}
.kpi-badge {{
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 0.25rem 0.75rem;
    border-radius: 999px;
    font-size: 0.85rem;
    font-weight: 700;
    letter-spacing: 0.2px;
}}
.kpi-badge-hot {{
    background-color: {kpi_hot_bg};
    color: {kpi_hot_color};
    border: 1px solid {kpi_hot_border};
}}
.kpi-badge-cold {{
    background-color: {kpi_cold_bg};
    color: {kpi_cold_color};
    border: 1px solid {kpi_cold_border};
}}
.kpi-badge-wind {{
    background-color: {kpi_wind_bg};
    color: {kpi_wind_color};
    border: 1px solid {kpi_wind_border};
}}
.storm-banner {{
    border-radius: 12px;
    padding: 0.85rem 1.2rem;
    margin: 0.6rem 0 1rem 0;
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 0.93rem;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}}
.storm-banner.storm-high {{
    background: linear-gradient(135deg, rgba(239, 68, 68, 0.22) 0%, rgba(185, 28, 28, 0.32) 100%);
    border: 1.5px solid #EF4444;
    color: {"#FECACA" if is_dark else "#991B1B"};
}}
.storm-banner.storm-med {{
    background: linear-gradient(135deg, rgba(245, 158, 11, 0.18) 0%, rgba(217, 119, 6, 0.25) 100%);
    border: 1.5px solid #F59E0B;
    color: {"#FDE68A" if is_dark else "#92400E"};
}}
.storm-banner.storm-low {{
    background: linear-gradient(135deg, rgba(16, 185, 129, 0.12) 0%, rgba(5, 150, 105, 0.18) 100%);
    border: 1px solid #10B981;
    color: {"#A7F3D0" if is_dark else "#065F46"};
}}
.anomaly-card {{
    background-color: {kpi_bg};
    border: 1px solid {kpi_border};
    border-left: 5px solid #F28C28;
    border-radius: 12px;
    padding: 1rem 1.3rem;
    margin: 0.8rem 0 1rem 0;
    box-shadow: {kpi_shadow};
}}
.anomaly-card-title {{
    font-size: 0.92rem;
    font-weight: 700;
    color: {hero_title};
    margin-bottom: 0.4rem;
    display: flex;
    align-items: center;
    gap: 8px;
}}
.anomaly-card-desc {{
    font-size: 0.92rem;
    color: {hero_sub};
    margin: 0;
    line-height: 1.45;
}}
.aqi-container {{
    background-color: {kpi_bg};
    border: 1px solid {kpi_border};
    border-radius: 14px;
    padding: 1rem 1.3rem;
    margin: 0.8rem 0 1rem 0;
    box-shadow: {kpi_shadow};
}}
</style>
        """,
        unsafe_allow_html=True,
    )


def render_header() -> None:  # Renderiza o banner superior com título e subtítulo dinâmico
    dataset: StationDataset | None = st.session_state.get("dataset")  # Busca o StationDataset ativo na sessão (se houver)
    df: pd.DataFrame | None = st.session_state.get("df")  # Busca o DataFrame ativo na sessão (se houver)

    if dataset is not None and df is not None:  # Se já existir uma base histórica carregada na sessão
        meta = dataset.metadata  # Obtém o dicionário de metadados
        subtitle = (  # Monta subtítulo informativo com estação, código, quantidade de linhas e arquivo fonte
            f"Estação {meta.get('nome', 'Desconhecida')} "  # Nome da estação ou "Desconhecida"
            f"({meta.get('codigo_estacao', '-')}) • "  # Código da estação ou "-"
            f"{br_number(len(df), 0)} registros • "  # Total de registros formatado sem decimais
            f"Fonte: {dataset.source.name}"  # Nome do arquivo ou fonte Open-Meteo
        )  # Fecha subtítulo
    else:  # Se ainda não houver base histórica carregada
        subtitle = "Clima ao vivo em qualquer lugar do mundo • Análise meteorológica com Python"  # Subtítulo padrão inicial

    st.markdown(  # Renderiza o HTML do banner no topo da página
        f"""
<div class="climaps-banner"> <!-- Container estilizado do banner -->
<h1>☁️ ClimaPS</h1> <!-- Título principal do aplicativo -->
<p>{subtitle}</p> <!-- Subtítulo dinâmico gerado acima -->
</div> <!-- Fecha div do banner -->
        """,  # Fecha f-string HTML
        unsafe_allow_html=True,  # Habilita renderização de HTML
    )  # Fecha st.markdown
