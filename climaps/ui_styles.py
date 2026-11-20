import pandas as pd  # Importado para usar pd.isna na verificação de valores ausentes
import streamlit as st  # Framework da interface web

from climaps.core.data_loader import StationDataset  # Tipo usado para leitura da sessão no cabeçalho

# Paleta Profissional e Elegante (Estilo Data/SaaS Científico e Meteorológico)
PRIMARY_BLUE = "#2563EB"       # Azul de ação e identidade institucional (Blue 600)
ACCENT_SKY = "#0EA5E9"         # Azul celeste / ciano meteorológico suave (Sky 500)
ACCENT_AMBER = "#F59E0B"       # Âmbar para calor e médias (Amber 500)
ALERT_RED = "#EF4444"          # Vermelho para alertas severos de risco (Red 500)
SUCCESS_EMERALD = "#10B981"    # Verde para dados ao vivo e normalidade (Emerald 500)

# Constantes legadas mantidas para retrocompatibilidade com outros módulos
NAVY = "#1E3A8A"
BLUE = "#2563EB"
ORANGE = "#F59E0B"
ELECTRIC_NEON = "#2563EB"
ACCENT_ORANGE = "#F59E0B"
ACCENT_CYAN = "#0EA5E9"
CRITICAL_RED = "#EF4444"
PURE_BLACK = "#0B0F19"
DARK_SURFACE = "#111827"
DARK_BORDER = "#1F2937"


def br_number(value: float | int | None, decimals: int = 1) -> str:  # Formata números no padrão brasileiro
    if value is None or pd.isna(value):
        return "-"
    text = f"{float(value):,.{decimals}f}"
    return text.replace(",", "X").replace(".", ",").replace("X", ".")


def format_datetime_friendly(value: str | pd.Timestamp | None) -> str:
    """Formata datas e timestamps para formato amigável brasileiro (ex: 19/11/2026 às 16:00)."""
    if not value or pd.isna(value):
        return "-"
    if isinstance(value, str) and " às " in value:
        return value
    try:
        dt = pd.to_datetime(value)
        return dt.strftime("%d/%m/%Y às %H:%M")
    except Exception:
        return str(value)


def inject_custom_css(is_dark: bool = True) -> None:  # Injeta CSS personalizado limpo e profissional
    if is_dark:  # Tema Escuro Profissional (Slate / Obsidian)
        app_bg = "#0B0F19"
        text_color = "#F8FAFC"
        sidebar_bg = "#0D131F"
        sidebar_border = "#1E293B"
        sidebar_text = "#94A3B8"
        sidebar_heading = "#F1F5F9"

        banner_bg = "linear-gradient(135deg, #0F172A 0%, #131E33 100%)"
        banner_border = "#1E293B"
        banner_shadow = "0 2px 12px rgba(0, 0, 0, 0.35)"
        banner_sub = "#94A3B8"

        container_bg = "#111827"
        container_border = "#1F2937"

        kpi_bg = "#111827"
        kpi_border = "#1F2937"
        kpi_shadow = "0 1px 3px rgba(0, 0, 0, 0.2)"
        kpi_label = "#94A3B8"
        kpi_val = "#F8FAFC"
        kpi_hot_bg = "rgba(245, 158, 11, 0.12)"
        kpi_hot_color = "#FBBF24"
        kpi_hot_border = "rgba(245, 158, 11, 0.25)"
        kpi_cold_bg = "rgba(14, 165, 233, 0.12)"
        kpi_cold_color = "#38BDF8"
        kpi_cold_border = "rgba(14, 165, 233, 0.25)"
        kpi_wind_bg = "rgba(99, 102, 241, 0.12)"
        kpi_wind_color = "#818CF8"
        kpi_wind_border = "rgba(99, 102, 241, 0.25)"
    else:  # Tema Claro Profissional (Tailwind Slate / Vercel Light)
        app_bg = "#F8FAFC"
        text_color = "#0F172A"
        sidebar_bg = "#FFFFFF"
        sidebar_border = "#E2E8F0"
        sidebar_text = "#334155"
        sidebar_heading = "#0F172A"

        banner_bg = "linear-gradient(135deg, #FFFFFF 0%, #F8FAFC 100%)"
        banner_border = "#E2E8F0"
        banner_shadow = "0 1px 3px rgba(0, 0, 0, 0.05)"
        banner_sub = "#475569"

        container_bg = "#FFFFFF"
        container_border = "#E2E8F0"

        kpi_bg = "#FFFFFF"
        kpi_border = "#E2E8F0"
        kpi_shadow = "0 1px 3px rgba(0, 0, 0, 0.05)"
        kpi_label = "#475569"
        kpi_val = "#0F172A"
        kpi_hot_bg = "#FEF3C7"
        kpi_hot_color = "#B45309"
        kpi_hot_border = "#FCD34D"
        kpi_cold_bg = "#E0F2FE"
        kpi_cold_color = "#0369A1"
        kpi_cold_border = "#BAE6FD"
        kpi_wind_bg = "#EEF2FF"
        kpi_wind_color = "#4338CA"
        kpi_wind_border = "#C7D2FE"

    st.markdown(
        f"""
<style>
/* ==============================================================================
   CLIMAPS - Design System Profissional (Clean / Scientific SaaS)
   ============================================================================== */

/* Tipografia global e fundo */
.stApp {{
    background-color: {app_bg} !important;
    color: {text_color} !important;
    font-family: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}}
.stApp header, header[data-testid="stHeader"] {{
    background-color: transparent !important;
    height: 1.5rem !important;
}}

/* Redução do espaçamento em branco no topo (posiciona o CLIMAPS bem mais acima) */
.block-container,
div[data-testid="stMainBlockContainer"],
div[data-testid="stAppViewContainer"] section.main > div.block-container {{
    padding-top: 0.8rem !important;
    padding-bottom: 2rem !important;
}}
section[data-testid="stSidebar"] [data-testid="stSidebarContent"],
section[data-testid="stSidebar"] div.block-container {{
    padding-top: 1rem !important;
}}
h1, h2, h3, h4, h5, h6, .stHeading,
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {{
    color: {"#F8FAFC" if is_dark else "#0F172A"} !important;
    font-weight: 700 !important;
    letter-spacing: -0.2px !important;
}}
.stApp p, .stMarkdown p, [data-testid="stMarkdownContainer"] p {{
    color: {text_color} !important;
}}

/* Indicador de status elegante */
.status-dot {{
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background-color: #10B981;
}}

/* Barra lateral (Sidebar) */
section[data-testid="stSidebar"] {{
    background-color: {sidebar_bg} !important;
    border-right: 1px solid {sidebar_border} !important;
}}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] h4 {{
    color: {sidebar_heading} !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
}}
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] label p,
section[data-testid="stSidebar"] label span,
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] p {{
    color: {sidebar_text} !important;
    font-weight: 500 !important;
    font-size: 0.85rem !important;
}}
section[data-testid="stSidebar"] span {{
    color: {sidebar_text} !important;
}}

/* Rótulos de Widgets em Toda a Aplicação (Sidebar e Conteúdo Principal) */
[data-testid="stWidgetLabel"],
[data-testid="stWidgetLabel"] p,
[data-testid="stWidgetLabel"] span,
[data-testid="stWidgetLabel"] label,
label[data-testid="stWidgetLabel"] {{
    color: {"#F8FAFC" if is_dark else "#0F172A"} !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
}}

/* Rádio de alternância de tema e opções de rádio em geral */
div[data-testid="stRadio"] [role="radiogroup"] label,
div[data-testid="stRadio"] [role="radiogroup"] label p,
div[data-testid="stRadio"] [role="radiogroup"] label span,
div[data-testid="stRadio"] [role="radiogroup"] label * {{
    color: {"#F8FAFC" if is_dark else "#0F172A"} !important;
    font-weight: 500 !important;
    font-size: 0.88rem !important;
}}
div[data-testid="stRadio"] [data-testid="stWidgetLabel"] * {{
    color: {"#F8FAFC" if is_dark else "#0F172A"} !important;
    font-weight: 600 !important;
}}
/* Garante que o indicador circular do rádio seja perfeitamente redondo e enxuto */
div[data-testid="stRadio"] div[role="radiogroup"] label div[role="radio"],
div[data-testid="stRadio"] div[role="radiogroup"] label input + div,
div[data-testid="stRadio"] div[role="radiogroup"] label div:first-child,
div[data-testid="stRadio"] div[role="radiogroup"] label div:first-child div {{
    border-radius: 50% !important;
}}

/* File uploader */
section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"],
[data-testid="stFileUploaderDropzone"] {{
    background-color: {"#111827" if is_dark else "#F8FAFC"} !important;
    border: 1.5px dashed {"#334155" if is_dark else "#CBD5E1"} !important;
    border-radius: 8px !important;
}}
[data-testid="stFileUploaderDropzone"] span,
[data-testid="stFileUploaderDropzone"] small,
[data-testid="stFileUploaderDropzone"] p,
[data-testid="stFileUploaderDropzone"] * {{
    color: {"#94A3B8" if is_dark else "#475569"} !important;
    font-weight: 500 !important;
}}
[data-testid="stFileUploaderDropzone"] button {{
    background: #2563EB !important;
    background-color: #2563EB !important;
    color: #FFFFFF !important;
    border: 1px solid #1D4ED8 !important;
    font-weight: 600 !important;
    border-radius: 6px !important;
    padding: 0.35rem 0.9rem !important;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05) !important;
}}
[data-testid="stFileUploaderDropzone"] button * {{
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: #FFFFFF !important;
    fill: #FFFFFF !important;
    font-weight: 600 !important;
}}

/* Selectbox e Menus Suspensos (Suporte completo a Streamlit 1.x e novas tags React-Aria) */
div[data-testid="stSelectbox"] > div:not([data-testid="stWidgetLabel"]),
div[data-testid="stSelectbox"] [role="combobox"],
div[data-testid="stSelectbox"] input,
div[data-baseweb="select"],
div[data-baseweb="select"] > div,
div[data-baseweb="select"] > div > div {{
    background-color: {"#111827" if is_dark else "#FFFFFF"} !important;
    border-color: {"#1F2937" if is_dark else "#CBD5E1"} !important;
    border-radius: 8px !important;
    color: {"#F8FAFC" if is_dark else "#0F172A"} !important;
}}
div[data-testid="stSelectbox"] input {{
    background-color: transparent !important;
    color: {"#F8FAFC" if is_dark else "#0F172A"} !important;
    font-weight: 500 !important;
}}
div[data-testid="stSelectbox"] span,
div[data-testid="stSelectbox"] div {{
    color: {"#F8FAFC" if is_dark else "#0F172A"} !important;
}}
div[data-testid="stSelectbox"] svg,
div[data-baseweb="select"] svg {{
    fill: {"#94A3B8" if is_dark else "#475569"} !important;
    color: {"#94A3B8" if is_dark else "#475569"} !important;
}}
div[data-testid="stSelectboxVirtualDropdown"],
div[data-testid="stSelectboxVirtualDropdown"] ul,
div[data-testid="stSelectboxVirtualDropdown"] li,
div[data-baseweb="popover"],
div[data-baseweb="menu"] {{
    background-color: {"#111827" if is_dark else "#FFFFFF"} !important;
    border: 1px solid {"#1F2937" if is_dark else "#CBD5E1"} !important;
    color: {"#F8FAFC" if is_dark else "#0F172A"} !important;
}}
div[data-testid="stSelectboxVirtualDropdown"] li,
div[data-testid="stSelectboxVirtualDropdown"] li *,
div[data-baseweb="menu"] li,
div[data-baseweb="menu"] li * {{
    color: {"#F8FAFC" if is_dark else "#0F172A"} !important;
    font-weight: 500 !important;
}}
div[data-testid="stSelectboxVirtualDropdown"] li:hover,
div[data-testid="stSelectboxVirtualDropdown"] li[data-focused="true"],
div[data-baseweb="menu"] li:hover {{
    background-color: {"#1F2937" if is_dark else "#F1F5F9"} !important;
    color: {"#38BDF8" if is_dark else "#2563EB"} !important;
}}

/* Date input, text input e number input (Novo DatePicker / DateRangePicker e inputs padrão) */
div[data-testid="stDateInput"] > div:not([data-testid="stWidgetLabel"]),
div[data-testid="stDateInput"] [data-testid="stDateInputField"],
div[data-testid="stDateInput"] [role="group"],
div[data-testid="stTextInput"] > div:not([data-testid="stWidgetLabel"]),
div[data-testid="stNumberInput"] > div:not([data-testid="stWidgetLabel"]),
div[data-baseweb="base-input"],
div[data-baseweb="base-input"] > div,
div[data-baseweb="input"],
div[data-baseweb="input"] > div,
input[data-testid="stTextInputRootElement"],
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
div[data-testid="stDateInput"] input {{
    background-color: {"#111827" if is_dark else "#FFFFFF"} !important;
    color: {"#F8FAFC" if is_dark else "#0F172A"} !important;
    border-color: {"#1F2937" if is_dark else "#CBD5E1"} !important;
    border-radius: 8px !important;
}}
div[data-testid="stDateInput"] [role="spinbutton"],
div[data-testid="stDateInput"] span,
div[data-testid="stDateInput"] div,
div[data-baseweb="base-input"] input,
div[data-baseweb="input"] input {{
    color: {"#F8FAFC" if is_dark else "#0F172A"} !important;
    background-color: transparent !important;
    font-weight: 500 !important;
}}
div[data-testid="stDateInput"] button {{
    background: transparent !important;
    border: none !important;
}}
div[data-testid="stDateInput"] svg {{
    fill: {"#94A3B8" if is_dark else "#475569"} !important;
    color: {"#94A3B8" if is_dark else "#475569"} !important;
}}

/* Sliders e Checkboxes */
div[data-testid="stSlider"] [data-testid="stWidgetLabel"] p {{
    color: {"#F8FAFC" if is_dark else "#0F172A"} !important;
    font-weight: 600 !important;
}}
div[data-testid="stSlider"] div[data-testid="stTickBar"] span {{
    color: {"#94A3B8" if is_dark else "#475569"} !important;
}}
div[data-testid="stCheckbox"] label > div:first-child,
div[data-testid="stCheckbox"] div[role="checkbox"] {{
    background-color: {"#1E293B" if is_dark else "#FFFFFF"} !important;
    border: 1.5px solid {"#475569" if is_dark else "#CBD5E1"} !important;
    border-radius: 4px !important;
}}
div[data-testid="stCheckbox"] label > div:first-child[data-selected="true"],
div[data-testid="stCheckbox"] label input:checked + div,
div[data-testid="stCheckbox"] label > div:first-child:has(svg) {{
    background-color: #2563EB !important;
    border-color: #1D4ED8 !important;
}}
div[data-testid="stCheckbox"] svg {{
    fill: #FFFFFF !important;
    stroke: #FFFFFF !important;
    color: #FFFFFF !important;
}}
div[data-testid="stCheckbox"] label p,
div[data-testid="stCheckbox"] label span {{
    color: {"#F8FAFC" if is_dark else "#0F172A"} !important;
    font-weight: 500 !important;
}}

/* Botões Modernos e Profissionais (Apenas botões de ação st.button e st.download_button) */
div[data-testid="stButton"] > button,
div[data-testid="stDownloadButton"] > button,
.stButton > button,
.stDownloadButton > button {{
    background: #2563EB !important;
    background-color: #2563EB !important;
    color: #FFFFFF !important;
    border: 1px solid #1D4ED8 !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    padding: 0.45rem 1rem !important;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05) !important;
    transition: background-color 0.15s ease, border-color 0.15s ease !important;
}}
div[data-testid="stButton"] > button *,
div[data-testid="stDownloadButton"] > button *,
.stButton > button *,
.stDownloadButton > button * {{
    color: #FFFFFF !important;
    font-weight: 600 !important;
    fill: #FFFFFF !important;
}}
div[data-testid="stButton"] > button:hover,
div[data-testid="stDownloadButton"] > button:hover,
.stButton > button:hover,
.stDownloadButton > button:hover {{
    background: #1D4ED8 !important;
    background-color: #1D4ED8 !important;
    border-color: #1E40AF !important;
    color: #FFFFFF !important;
    transform: none !important;
}}

/* Garante que botões utilitários de ícone (Help/Tooltip e Selectbox) não virem blocos azuis */
button[data-testid="stHelpButton"],
[data-testid="stHelpButton"] button,
button[aria-label="Help"],
[data-testid="stTooltipIcon"],
[data-testid="stTooltipIcon"] button,
[data-testid="stTooltipHoverTarget"],
[data-testid="stTooltipHoverTarget"] button,
div[data-testid="stMetricLabel"] button,
div[data-testid="stMetric"] button,
div[data-testid="stMetric"] [data-testid="stTooltipIcon"] button,
div[data-baseweb="select"] button,
div[data-baseweb="base-input"] button {{
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    padding: 0 !important;
    margin: 0 !important;
    width: auto !important;
    min-width: auto !important;
    height: auto !important;
    min-height: auto !important;
    outline: none !important;
}}
div[data-testid="stMetricLabel"] button *,
div[data-testid="stMetric"] button *,
[data-testid="stTooltipIcon"] *,
[data-testid="stTooltipHoverTarget"] * {{
    color: {"#94A3B8" if is_dark else "#64748B"} !important;
}}
div[data-testid="stMetricLabel"] button svg,
div[data-testid="stMetric"] button svg,
[data-testid="stTooltipIcon"] svg,
[data-testid="stTooltipHoverTarget"] svg {{
    fill: {"#94A3B8" if is_dark else "#64748B"} !important;
    color: {"#94A3B8" if is_dark else "#64748B"} !important;
}}

/* ==============================================================================
   Plotly Charts - Tipografia Nítida e de Alto Contraste (White e Dark Mode)
   ============================================================================== */
div[data-testid="stPlotlyChart"] .js-plotly-plot,
div[data-testid="stPlotlyChart"] svg {{
    background: transparent !important;
}}
.js-plotly-plot .xtick text,
.js-plotly-plot .ytick text,
.js-plotly-plot .y2tick text,
.js-plotly-plot .g-xtitle text,
.js-plotly-plot .g-ytitle text,
.js-plotly-plot .g-y2title text,
.js-plotly-plot .gtitle,
.js-plotly-plot .legendtext {{
    fill: {"#CBD5E1" if is_dark else "#0F172A"} !important;
    color: {"#CBD5E1" if is_dark else "#0F172A"} !important;
    font-weight: 500 !important;
}}
.js-plotly-plot .gridlayer path,
.js-plotly-plot .zerolinelayer path {{
    stroke: {"rgba(148, 163, 184, 0.15)" if is_dark else "rgba(100, 116, 139, 0.20)"} !important;
}}

/* Tooltip Hover no Plotly (hoverlayer / hovertext) - Nítido e Legível */
.js-plotly-plot .hoverlayer .hovertext path {{
    fill: {"#1E293B" if is_dark else "#FFFFFF"} !important;
    stroke: {"#334155" if is_dark else "#CBD5E1"} !important;
    stroke-width: 1.5px !important;
    opacity: 0.98 !important;
}}
.js-plotly-plot .hoverlayer text,
.js-plotly-plot .hoverlayer .hovertext text,
.js-plotly-plot .hoverlayer .axistext text,
.js-plotly-plot .hoverlayer tspan,
.js-plotly-plot .hoverlayer .hovertext tspan {{
    fill: {"#F8FAFC" if is_dark else "#0F172A"} !important;
    color: {"#F8FAFC" if is_dark else "#0F172A"} !important;
    font-weight: 600 !important;
}}

/* Modebar do Plotly sem sobreposição na legenda */
.js-plotly-plot .modebar-container {{
    opacity: 0.3 !important;
    transition: opacity 0.2s ease !important;
}}
.js-plotly-plot:hover .modebar-container {{
    opacity: 0.85 !important;
}}
.js-plotly-plot .modebar-btn path {{
    fill: {"#94A3B8" if is_dark else "#64748B"} !important;
}}

/* Containers com bordas (st.container(border=True)) */
div[data-testid="stVerticalBlockBorderWrapper"] {{
    background: {container_bg} !important;
    border: 1px solid {container_border} !important;
    border-radius: 12px !important;
    box-shadow: {"0 1px 3px rgba(0, 0, 0, 0.2)" if is_dark else "0 1px 3px rgba(0, 0, 0, 0.05)"} !important;
}}

/* Banner Principal ClimaPS */
.climaps-banner {{
    background: {banner_bg};
    padding: 1rem 1.4rem;
    border-radius: 12px;
    margin-top: 0 !important;
    margin-bottom: 1rem;
    border: 1px solid {banner_border};
    box-shadow: {banner_shadow};
}}
.platform-eyebrow {{
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.8px;
    color: {"#38BDF8" if is_dark else "#0284C7"};
    text-transform: uppercase;
}}
.platform-title {{
    margin: 0;
    font-size: 1.65rem;
    font-weight: 700;
    letter-spacing: -0.4px;
    color: {"#F8FAFC" if is_dark else "#0F172A"} !important;
}}
.platform-subtitle {{
    margin: 0.25rem 0 0 0;
    color: {banner_sub} !important;
    font-size: 0.88rem;
    font-weight: 400;
}}
.tech-chip {{
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 0.25rem 0.65rem;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 500;
    background: {"#1E293B" if is_dark else "#F1F5F9"};
    color: {"#94A3B8" if is_dark else "#475569"};
    border: 1px solid {"#334155" if is_dark else "#CBD5E1"};
}}
.tech-chip-live {{
    color: #10B981 !important;
    font-weight: 600 !important;
}}

/* KPI Cards nativos (st.metric) */
div[data-testid="stMetric"] {{
    background: {"#111827" if is_dark else "#FFFFFF"} !important;
    border: 1px solid {"#1F2937" if is_dark else "#E2E8F0"} !important;
    border-radius: 10px !important;
    padding: 0.85rem 1.1rem !important;
    box-shadow: {"0 1px 3px rgba(0, 0, 0, 0.2)" if is_dark else "0 1px 3px rgba(0, 0, 0, 0.05)"} !important;
    transition: border-color 0.15s ease !important;
}}
div[data-testid="stMetric"]:hover {{
    border-color: {"#334155" if is_dark else "#CBD5E1"} !important;
    transform: none !important;
}}
div[data-testid="stMetric"] [data-testid="stMetricLabel"],
div[data-testid="stMetric"] [data-testid="stMetricLabel"] *,
div[data-testid="stMetric"] [data-testid="stMetricLabel"] p {{
    color: {"#94A3B8" if is_dark else "#475569"} !important;
    font-weight: 600 !important;
    font-size: 0.76rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.5px !important;
}}
div[data-testid="stMetric"] [data-testid="stMetricValue"],
div[data-testid="stMetric"] [data-testid="stMetricValue"] *,
div[data-testid="stMetric"] [data-testid="stMetricValue"] div {{
    color: {"#F8FAFC" if is_dark else "#0F172A"} !important;
    font-weight: 700 !important;
    font-size: 1.75rem !important;
    letter-spacing: -0.3px !important;
}}

/* Caixas de avisos e insights (st.info, st.success, st.warning, st.alert) */
div[data-testid="stAlert"],
div[data-testid="stAlert"] > div {{
    background: {"#111827" if is_dark else "#F8FAFC"} !important;
    background-color: {"#111827" if is_dark else "#F8FAFC"} !important;
    border: 1px solid {"#1F2937" if is_dark else "#CBD5E1"} !important;
    border-left: 4px solid #2563EB !important;
    border-radius: 8px !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06) !important;
}}
div[data-testid="stAlert"] p,
div[data-testid="stAlert"] span,
div[data-testid="stAlert"] div,
div[data-testid="stAlert"] * {{
    color: {"#E2E8F0" if is_dark else "#0F172A"} !important;
    font-weight: 500 !important;
}}

/* Indicadores de delta nos KPIs (st.metric delta) - Alto Contraste e Legibilidade no White Mode */
div[data-testid="stMetricDelta"] {{
    background: {"rgba(255, 255, 255, 0.08)" if is_dark else "#F1F5F9"} !important;
    background-color: {"rgba(255, 255, 255, 0.08)" if is_dark else "#F1F5F9"} !important;
    border: 1px solid {"rgba(255, 255, 255, 0.14)" if is_dark else "#CBD5E1"} !important;
    border-radius: 9999px !important;
    padding: 3px 10px !important;
    margin-top: 5px !important;
    display: inline-flex !important;
    align-items: center !important;
    gap: 4px !important;
    width: fit-content !important;
    max-width: 100% !important;
}}
div[data-testid="stMetricDelta"],
div[data-testid="stMetricDelta"] *,
div[data-testid="stMetricDelta"] span,
div[data-testid="stMetricDelta"] div,
div[data-testid="stMetricDelta"] p {{
    color: {"#F1F5F9" if is_dark else "#0F172A"} !important;
    font-weight: 600 !important;
    font-size: 0.81rem !important;
    line-height: 1.25 !important;
}}
div[data-testid="stMetricDelta"] svg {{
    fill: {"#94A3B8" if is_dark else "#334155"} !important;
    color: {"#94A3B8" if is_dark else "#334155"} !important;
    width: 13px !important;
    height: 13px !important;
    flex-shrink: 0 !important;
}}

/* ==============================================================================
   Navegação de Abas (st.tabs) - Design Enxuto, Moderno e Limpo (Estilo SaaS)
   ============================================================================== */
div[data-testid="stTabs"] {{
    margin-top: 0.2rem !important;
    margin-bottom: 1rem !important;
}}
div[data-testid="stTabs"] div[data-baseweb="tab-list"] {{
    background: transparent !important;
    border: none !important;
    border-bottom: 1.5px solid {"#1E293B" if is_dark else "#E2E8F0"} !important;
    border-radius: 0 !important;
    padding: 0 0 2px 0 !important;
    gap: 4px !important;
    display: flex !important;
    flex-wrap: wrap !important;
    align-items: center !important;
    min-height: auto !important;
}}
div[data-testid="stTabs"] button[data-baseweb="tab"] {{
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    border-bottom: 2.5px solid transparent !important;
    border-radius: 6px 6px 0 0 !important;
    padding: 0.5rem 0.9rem !important;
    margin: 0 !important;
    font-weight: 500 !important;
    color: {"#94A3B8" if is_dark else "#64748B"} !important;
    font-size: 0.90rem !important;
    letter-spacing: -0.1px !important;
    cursor: pointer !important;
    transition: all 0.15s ease-in-out !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    box-shadow: none !important;
    height: auto !important;
}}
div[data-testid="stTabs"] button[data-baseweb="tab"]:hover {{
    background-color: {"rgba(255, 255, 255, 0.04)" if is_dark else "rgba(0, 0, 0, 0.03)"} !important;
    border-bottom: 2.5px solid {"#475569" if is_dark else "#94A3B8"} !important;
    color: {"#F8FAFC" if is_dark else "#0F172A"} !important;
}}
div[data-testid="stTabs"] button[data-baseweb="tab"] p,
div[data-testid="stTabs"] button[data-baseweb="tab"] span,
div[data-testid="stTabs"] button[data-baseweb="tab"] div,
div[data-testid="stTabs"] button[data-baseweb="tab"] * {{
    color: {"#94A3B8" if is_dark else "#64748B"} !important;
    font-weight: 500 !important;
    font-size: 0.90rem !important;
    line-height: 1.3 !important;
    opacity: 1 !important;
    margin: 0 !important;
    padding: 0 !important;
}}
div[data-testid="stTabs"] button[data-baseweb="tab"]:hover * {{
    color: {"#F8FAFC" if is_dark else "#0F172A"} !important;
}}
div[data-testid="stTabs"] button[aria-selected="true"] {{
    background: {"rgba(37, 99, 235, 0.08)" if is_dark else "rgba(37, 99, 235, 0.06)"} !important;
    background-color: {"rgba(37, 99, 235, 0.08)" if is_dark else "rgba(37, 99, 235, 0.06)"} !important;
    border: none !important;
    border-bottom: 2.5px solid #2563EB !important;
    border-radius: 6px 6px 0 0 !important;
    box-shadow: none !important;
    color: {"#38BDF8" if is_dark else "#2563EB"} !important;
}}
div[data-testid="stTabs"] button[aria-selected="true"] p,
div[data-testid="stTabs"] button[aria-selected="true"] span,
div[data-testid="stTabs"] button[aria-selected="true"] div,
div[data-testid="stTabs"] button[aria-selected="true"] * {{
    color: {"#38BDF8" if is_dark else "#2563EB"} !important;
    font-weight: 700 !important;
    font-size: 0.90rem !important;
}}
div[data-testid="stTabs"] div[data-baseweb="tab-highlight"],
div[data-testid="stTabs"] div[data-baseweb="tab-border"] {{
    display: none !important;
}}

/* Tabelas interativas (st.dataframe e st.data_editor) */
div[data-testid="stDataFrame"],
div[data-testid="stDataEditor"] {{
    border-radius: 8px !important;
    overflow: hidden !important;
    border: 1px solid {container_border} !important;
    {"" if is_dark else "filter: invert(1) hue-rotate(180deg) contrast(1.05) !important;"}
}}
{"" if is_dark else '''
div[data-testid="stDataFrame"] img,
div[data-testid="stDataEditor"] img {
    filter: invert(1) hue-rotate(180deg) !important;
}'''}

/* Cartão Hero de Clima ao Vivo */
.hero-weather {{
    background: {"linear-gradient(135deg, #111827 0%, #0F172A 100%)" if is_dark else "#FFFFFF"};
    border: 1px solid {"#1E293B" if is_dark else "#E2E8F0"};
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    margin: 0.5rem 0 1rem 0;
    box-shadow: {"0 2px 8px rgba(0, 0, 0, 0.25)" if is_dark else "0 1px 3px rgba(0, 0, 0, 0.05)"};
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 1rem;
}}
.hero-title {{
    margin: 0;
    color: {"#F8FAFC" if is_dark else "#0F172A"};
    font-size: 1.35rem;
    font-weight: 700;
}}
.hero-sub {{
    color: {"#94A3B8" if is_dark else "#475569"};
    font-size: 0.88rem;
    margin-top: 4px;
    font-weight: 500;
}}
.hero-sub code {{
    background-color: {"#1E293B" if is_dark else "#F1F5F9"};
    color: {"#38BDF8" if is_dark else "#0369A1"};
    border: 1px solid {"#334155" if is_dark else "#CBD5E1"};
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 0.82rem;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}}
.hero-temp {{
    font-size: 2.6rem;
    font-weight: 800;
    color: {"#38BDF8" if is_dark else "#0284C7"};
    line-height: 1;
}}
.hero-sensacao {{
    color: {"#94A3B8" if is_dark else "#475569"};
    font-size: 0.85rem;
    margin-top: 4px;
}}
.hero-sensacao b {{
    color: {"#F8FAFC" if is_dark else "#0F172A"};
}}
.hero-badge {{
    display: inline-block;
    background-color: {"rgba(14, 165, 233, 0.12)" if is_dark else "#E0F2FE"};
    color: {"#38BDF8" if is_dark else "#0369A1"};
    padding: 0.2rem 0.6rem;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 600;
    margin-bottom: 0.3rem;
}}

/* Cards de Extremos Comparativos */
.kpi-podium-card {{
    background: {kpi_bg};
    border: 1px solid {kpi_border};
    border-radius: 10px;
    padding: 0.9rem 1.1rem;
    box-shadow: {kpi_shadow};
    min-height: 105px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}}
.kpi-podium-card.kpi-hot {{
    border-left: 3px solid #F59E0B;
}}
.kpi-podium-card.kpi-cold {{
    border-left: 3px solid #0EA5E9;
}}
.kpi-podium-card.kpi-wind {{
    border-left: 3px solid #6366F1;
}}
.kpi-podium-label {{
    font-size: 0.75rem;
    font-weight: 600;
    color: {kpi_label};
    margin-bottom: 0.2rem;
    text-transform: uppercase;
    letter-spacing: 0.4px;
}}
.kpi-podium-value {{
    font-size: 1.25rem;
    font-weight: 700;
    color: {kpi_val};
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    line-height: 1.2;
    margin-bottom: 0.4rem;
}}
.kpi-badge {{
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 0.2rem 0.65rem;
    border-radius: 6px;
    font-size: 0.78rem;
    font-weight: 600;
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

/* Alerta de Tempestade e Barômetro */
.storm-banner {{
    border-radius: 10px;
    padding: 0.75rem 1.1rem;
    margin: 0.5rem 0 0.9rem 0;
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 0.88rem;
    font-weight: 500;
}}
.storm-banner.storm-high {{
    background: rgba(239, 68, 68, 0.12);
    border: 1px solid rgba(239, 68, 68, 0.35);
    color: {"#FCA5A5" if is_dark else "#991B1B"};
}}
.storm-banner.storm-med {{
    background: rgba(245, 158, 11, 0.12);
    border: 1px solid rgba(245, 158, 11, 0.35);
    color: {"#FCD34D" if is_dark else "#92400E"};
}}
.storm-banner.storm-low {{
    background: rgba(16, 185, 129, 0.10);
    border: 1px solid rgba(16, 185, 129, 0.25);
    color: {"#6EE7B7" if is_dark else "#065F46"};
}}

/* Cartões de Anomalia e Qualidade do Ar */
.anomaly-card {{
    background: {kpi_bg};
    border: 1px solid {kpi_border};
    border-left: 4px solid #F59E0B;
    border-radius: 10px;
    padding: 0.9rem 1.2rem;
    margin: 0.6rem 0 0.9rem 0;
    box-shadow: {kpi_shadow};
}}
.anomaly-card-title {{
    font-size: 0.92rem;
    font-weight: 700;
    color: {"#F8FAFC" if is_dark else "#0F172A"};
    margin-bottom: 0.3rem;
    display: flex;
    align-items: center;
    gap: 8px;
}}
.anomaly-card-desc {{
    font-size: 0.88rem;
    color: {"#94A3B8" if is_dark else "#334155"};
    margin: 0;
    line-height: 1.4;
}}
.aqi-container {{
    background: {kpi_bg};
    border: 1px solid {kpi_border};
    border-radius: 10px;
    padding: 0.9rem 1.2rem;
    margin: 0.6rem 0 0.9rem 0;
    box-shadow: {kpi_shadow};
}}

/* Expander (st.expander) */
div[data-testid="stExpander"],
div[data-testid="stExpander"] details {{
    background: {container_bg} !important;
    background-color: {container_bg} !important;
    border: 1px solid {container_border} !important;
    border-radius: 10px !important;
}}
div[data-testid="stExpander"] summary,
div[data-testid="stExpander"] details > summary {{
    background: {"#1F2937" if is_dark else "#F8FAFC"} !important;
    background-color: {"#1F2937" if is_dark else "#F8FAFC"} !important;
    color: {"#F8FAFC" if is_dark else "#0F172A"} !important;
    border-radius: 9px 9px 0 0 !important;
    font-weight: 600 !important;
}}
div[data-testid="stExpander"] summary *,
div[data-testid="stExpander"] details > summary * {{
    color: {"#F8FAFC" if is_dark else "#0F172A"} !important;
}}
div[data-testid="stExpander"] summary svg,
div[data-testid="stExpander"] details > summary svg {{
    fill: {"#94A3B8" if is_dark else "#334155"} !important;
    color: {"#94A3B8" if is_dark else "#334155"} !important;
}}
div[data-testid="stExpander"] div[data-testid="stExpanderDetails"] {{
    background: {container_bg} !important;
    background-color: {container_bg} !important;
    border-top: 1px solid {container_border} !important;
}}

/* Divisores e legendas */
hr, div[data-testid="stDivider"] {{
    border-color: {container_border} !important;
}}
.stCaption, [data-testid="stCaptionContainer"] p, [data-testid="stCaptionContainer"] * {{
    color: {"#94A3B8" if is_dark else "#475569"} !important;
    font-weight: 500 !important;
}}

/* Tooltips Flutuantes e Balões de Ajuda (st.metric help / stTooltipContent / floating-ui) */
div[role="tooltip"],
div[data-testid="stTooltipContent"],
div[data-testid="stTooltipErrorContent"],
.stTooltipContent,
.stTooltipErrorContent {{
    background: {"#1E293B" if is_dark else "#FFFFFF"} !important;
    background-color: {"#1E293B" if is_dark else "#FFFFFF"} !important;
    color: {"#F8FAFC" if is_dark else "#0F172A"} !important;
    border: 1px solid {"#334155" if is_dark else "#CBD5E1"} !important;
    border-radius: 8px !important;
    box-shadow: {"0 10px 25px -5px rgba(0, 0, 0, 0.45)" if is_dark else "0 10px 25px -5px rgba(0, 0, 0, 0.12), 0 8px 10px -6px rgba(0, 0, 0, 0.08)"} !important;
    padding: 0.55rem 0.85rem !important;
    max-width: 320px !important;
    line-height: 1.45 !important;
    z-index: 999999 !important;
}}
div[role="tooltip"] *,
div[data-testid="stTooltipContent"] *,
div[data-testid="stTooltipErrorContent"] *,
.stTooltipContent *,
.stTooltipErrorContent * {{
    color: {"#F8FAFC" if is_dark else "#0F172A"} !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
}}
div[role="tooltip"] p,
div[data-testid="stTooltipContent"] p,
.stTooltipContent p {{
    color: {"#F8FAFC" if is_dark else "#0F172A"} !important;
    margin: 0 !important;
}}
div[role="tooltip"] b,
div[role="tooltip"] strong,
div[data-testid="stTooltipContent"] b,
div[data-testid="stTooltipContent"] strong,
.stTooltipContent b,
.stTooltipContent strong {{
    color: {"#FFFFFF" if is_dark else "#0F172A"} !important;
    font-weight: 700 !important;
}}
</style>
        """,
        unsafe_allow_html=True,
    )


def render_header() -> None:  # Renderiza o cabeçalho superior profissional
    dataset: StationDataset | None = st.session_state.get("dataset")  # Busca o StationDataset ativo na sessão
    df: pd.DataFrame | None = st.session_state.get("df")  # Busca o DataFrame ativo na sessão
    is_dark = st.session_state.get("dark_mode", True)

    if dataset is not None and df is not None:  # Se existir base histórica carregada
        meta = dataset.metadata
        subtitle = (
            f"Estação {meta.get('nome', 'Desconhecida')} "
            f"({meta.get('codigo_estacao', '-')}) • "
            f"{br_number(len(df), 0)} registros analisados • "
            f"Fonte: {dataset.source.name}"
        )
    else:  # Sem base histórica carregada
        subtitle = "Plataforma de Monitoramento Meteorológico em Tempo Real e Análise Climática"

    st.markdown(
        f"""
<div class="climaps-banner">
    <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:0.75rem;">
        <div>
            <div style="display:flex; align-items:center; gap:8px; margin-bottom:0.25rem;">
                <span class="status-dot"></span>
                <span class="platform-eyebrow">MONITORAMENTO METEOROLÓGICO</span>
            </div>
            <h1 class="platform-title">☁️ CLIMAPS</h1>
            <p class="platform-subtitle">{subtitle}</p>
        </div>
        <div style="display:flex; gap:6px; align-items:center; flex-wrap:wrap;">
            <span class="tech-chip">Open-Meteo API</span>
            <span class="tech-chip">Dados INMET</span>
            <span class="tech-chip tech-chip-live">● Tempo Real</span>
        </div>
    </div>
</div>
        """,
        unsafe_allow_html=True,
    )
