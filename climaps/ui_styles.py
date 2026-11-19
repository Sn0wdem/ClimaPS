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


def inject_custom_css() -> None:  # Injeta CSS personalizado na página do Streamlit
    st.markdown(  # Escreve um bloco HTML/CSS bruto na página
        f"""
<style> /* Abre o bloco de estilos CSS */
.stApp {{ /* Estiliza o container principal da aplicação Streamlit */
    background-color: #F2F6FA; /* Define fundo cinza-azulado claro */
}}
section[data-testid="stSidebar"] {{ /* Estiliza a barra lateral */
    background-color: #FFFFFF; /* Fundo branco na barra lateral */
    border-right: 1px solid #E3EAF2; /* Borda direita sutil separando da área principal */
}}
.climaps-banner {{ /* Classe do banner superior principal */
    background: linear-gradient(135deg, {NAVY} 0%, {BLUE} 65%, #3A8FD4 100%); /* Gradiente azul diagonal */
    color: white; /* Texto branco */
    padding: 1.4rem 1.8rem; /* Espaçamento interno vertical e horizontal */
    border-radius: 16px; /* Cantos arredondados */
    margin-bottom: 1.2rem; /* Espaço abaixo do banner */
    border-left: 6px solid {ORANGE}; /* Faixa laranja decorativa na esquerda */
    box-shadow: 0 10px 25px rgba(18, 53, 91, 0.14); /* Sombra suave */
}}
.climaps-banner h1 {{ /* Estiliza o título H1 dentro do banner */
    margin: 0; /* Remove margens padrão */
    font-size: 2rem; /* Tamanho da fonte do título */
    font-weight: 700; /* Negrito forte */
    letter-spacing: -0.5px; /* Aproxima levemente as letras */
    color: white; /* Garante cor branca no título */
}}
.climaps-banner p {{ /* Estiliza o subtítulo dentro do banner */
    margin: 0.3rem 0 0 0; /* Pequeno espaço acima do parágrafo */
    color: #DCE9F5; /* Azul bem claro para contraste suave */
    font-size: 0.95rem; /* Tamanho da fonte do subtítulo */
}}
div[data-testid="stMetric"] {{ /* Estiliza os cards de métricas (st.metric) */
    background-color: #FFFFFF; /* Fundo branco */
    border: 1px solid #E2E9F1; /* Borda cinza clara */
    border-top: 3px solid {BLUE}; /* Borda superior azul de destaque */
    border-radius: 12px; /* Cantos arredondados */
    padding: 0.95rem 1.1rem; /* Espaçamento interno */
    box-shadow: 0 4px 12px rgba(18, 53, 91, 0.05); /* Sombra discreta */
    transition: transform 0.15s ease, box-shadow 0.15s ease; /* Animação suave ao passar o mouse */
}}
div[data-testid="stMetric"]:hover {{ /* Efeito hover nos cards de métricas */
    transform: translateY(-2px); /* Eleva levemente o card */
    box-shadow: 0 8px 18px rgba(18, 53, 91, 0.10); /* Aumenta a sombra no hover */
}}
div[data-testid="stTabs"] button[data-baseweb="tab"] {{ /* Estiliza os botões das abas */
    background-color: #FFFFFF; /* Fundo branco nas abas inativas */
    border: 1px solid #DCE6EF; /* Borda suave */
    border-radius: 999px; /* Formato de pílula */
    padding: 0.45rem 1rem; /* Espaçamento interno do botão da aba */
    margin-right: 0.35rem; /* Espaço entre abas */
    font-weight: 600; /* Seminegrito */
    color: {NAVY}; /* Texto azul-marinho */
}}
div[data-testid="stTabs"] button[aria-selected="true"] {{ /* Estiliza a aba atualmente selecionada */
    background-color: {NAVY} !important; /* Fundo azul-marinho forçado */
    color: #FFFFFF !important; /* Texto branco forçado */
    border-color: {NAVY} !important; /* Borda da mesma cor do fundo */
}}
div[data-testid="stTabs"] div[data-baseweb="tab-highlight"] {{ /* Seleciona a linha indicadora padrão do Streamlit */
    display: none; /* Oculta a barra sublinhada padrão das abas */
}}
.stButton > button, .stDownloadButton > button {{ /* Estiliza botões normais e de download */
    border-radius: 10px; /* Cantos arredondados */
    font-weight: 600; /* Texto em seminegrito */
}}
.hero-weather {{ /* Cartão principal de telemetria climática na aba Mundo Ao Vivo */
    background: linear-gradient(135deg, #FFFFFF 0%, #F7FAFD 100%); /* Gradiente sutil claro */
    border: 1px solid #DCE6EF; /* Borda suave */
    border-radius: 16px; /* Cantos arredondados */
    padding: 1.25rem 1.5rem; /* Espaçamento interno */
    margin: 0.6rem 0 1rem 0; /* Margens vertical superior e inferior */
    box-shadow: 0 6px 18px rgba(18, 53, 91, 0.06); /* Sombra suave */
    display: flex; /* Layout flexível lado a lado */
    justify-content: space-between; /* Empurra esquerda (cidade) e direita (temperatura) para as pontas */
    align-items: center; /* Centraliza verticalmente */
    flex-wrap: wrap; /* Permite quebrar linha em telas pequenas */
    gap: 1rem; /* Espaçamento mínimo entre os blocos */
}}
.hero-temp {{ /* Destaque numérico da temperatura atual */
    font-size: 2.7rem; /* Fonte grande */
    font-weight: 800; /* Negrito extra */
    color: {NAVY}; /* Cor azul-marinho */
    line-height: 1; /* Altura de linha compacta */
}}
.hero-badge {{ /* Etiqueta superior com período (Dia/Noite) e fuso horário */
    display: inline-block; /* Comporta-se como bloco em linha */
    background-color: #EAF2FA; /* Fundo azul bem claro */
    color: {BLUE}; /* Texto azul */
    padding: 0.25rem 0.7rem; /* Espaçamento interno da pílula */
    border-radius: 999px; /* Bordas totalmente arredondadas */
    font-size: 0.82rem; /* Fonte menor */
    font-weight: 600; /* Seminegrito */
    margin-bottom: 0.4rem; /* Espaço abaixo do badge */
}}
</style> <!-- Fecha o bloco CSS -->
        """,  # Fecha a f-string do CSS
        unsafe_allow_html=True,  # Permite ao Streamlit renderizar HTML/CSS bruto
    )  # Fecha chamada st.markdown


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