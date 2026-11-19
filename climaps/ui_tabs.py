import pandas as pd  # Manipulação de DataFrames
import plotly.express as px  # Interface de alto nível do Plotly para gráficos rápidos (barras, heatmap)
import plotly.graph_objects as go  # Interface detalhada do Plotly para gráficos customizados (linhas preenchidas)
import streamlit as st  # Componentes da interface web

from climaps.core.analysis import (  # Importa funções analíticas e constantes do módulo core
    MESES_PT,  # Mapa de números de mês para siglas em português
    calculate_kpis,  # Cálculo dos 5 KPIs principais
    correlation_matrix,  # Matriz de correlação entre chuva e temperaturas
    daily_summary,  # Agregação diária
    generate_insights,  # Geração automática de frases analíticas
    monthly_summary,  # Agregação mensal
    quality_report,  # Diagnóstico de qualidade dos dados
)  # Fecha importação
from climaps.ui_styles import BLUE, ORANGE, br_number  # Importa paleta de cores e formatador numérico brasileiro


def render_summary_tab(filtered: pd.DataFrame, full_df: pd.DataFrame) -> None:  # Renderiza a aba "📊 Resumo"
    if filtered.empty:  # Se os filtros não retornarem nenhuma linha
        st.warning("Nenhum registro atende aos filtros selecionados.")  # Exibe aviso amarelo ao usuário
        return  # Encerra a renderização desta aba

    kpis = calculate_kpis(filtered)  # Calcula os KPIs usando apenas o recorte filtrado
    c1, c2, c3, c4, c5 = st.columns(5)  # Divide a largura em 5 colunas iguais para os cards de KPI
    c1.metric("Registros", br_number(kpis["registros"], 0))  # Card 1: número de registros
    c2.metric("Chuva acumulada", f"{br_number(kpis['precipitacao_total'])} mm")  # Card 2: soma da chuva
    c3.metric("Temp. máx. média", f"{br_number(kpis['temp_max_media'])} °C")  # Card 3: média da temp. máxima
    c4.metric("Temp. mín. média", f"{br_number(kpis['temp_min_media'])} °C")  # Card 4: média da temp. mínima
    c5.metric("Completude", f"{br_number(kpis['completude'])}%")  # Card 5: percentual de células preenchidas

    st.subheader("💡 Insights do recorte")  # Subtítulo da seção de insights automáticos
    for insight in generate_insights(filtered):  # Gera e percorre cada frase de insight
        st.info(insight)  # Exibe cada insight dentro de uma caixa azul informativa

    col_left, col_right = st.columns([1.4, 1])  # Cria duas colunas: esquerda 40% maior que a direita
    with col_left:  # Entra na coluna da esquerda
        with st.container(border=True):  # Cria um cartão com borda ao redor do resumo mensal
            st.subheader("📅 Resumo mensal")  # Título do bloco
            mensal = monthly_summary(filtered).copy()  # Calcula resumo mensal e faz cópia segura
            st.dataframe(  # Exibe a tabela interativa do resumo mensal
                mensal[["mes_nome", "registros", "precipitacao_mm", "temp_max_media", "temp_min_media", "horas_com_chuva"]],  # Seleciona ordem das colunas
                hide_index=True,  # Oculta o índice numérico do pandas
                column_config={  # Configura rótulos e formatação de cada coluna na UI
                    "mes_nome": "Mês",  # Rótulo da coluna de mês
                    "registros": st.column_config.NumberColumn("Registros", format="%d"),  # Inteiro
                    "precipitacao_mm": st.column_config.NumberColumn("Chuva (mm)", format="%.1f"),  # 1 casa decimal
                    "temp_max_media": st.column_config.NumberColumn("Máx. média (°C)", format="%.1f"),  # 1 casa decimal
                    "temp_min_media": st.column_config.NumberColumn("Mín. média (°C)", format="%.1f"),  # 1 casa decimal
                    "horas_com_chuva": st.column_config.NumberColumn("Horas c/ chuva", format="%d"),  # Inteiro
                },  # Fecha column_config
            )  # Fecha st.dataframe

    with col_right:  # Entra na coluna da direita
        with st.container(border=True):  # Cria um cartão com borda ao redor do relatório de qualidade
            st.subheader("🩺 Qualidade da base completa")  # Título do bloco (usa full_df, sem filtros)
            report = quality_report(full_df)  # Executa auditoria de qualidade na base completa
            missing = report["valores_ausentes"]  # Extrai subdicionário de valores ausentes
            outliers = report["outliers_iqr"]  # Extrai subdicionário de outliers IQR
            qualidade_df = pd.DataFrame(  # Monta uma tabela simples de Indicador x Valor
                [  # Lista de linhas do diagnóstico
                    {"Indicador": "Lacunas de timestamp", "Valor": report["timestamps_ausentes"]},  # Horas faltantes na sequência
                    {"Indicador": "Timestamps duplicados", "Valor": report["timestamps_duplicados"]},  # Horários repetidos
                    {"Indicador": "Chuva negativa", "Valor": report["chuva_negativa"]},  # Chuva < 0
                    {"Indicador": "Máxima < Mínima", "Valor": report["temp_inconsistente"]},  # Inconsistência térmica
                    {"Indicador": "Ausentes em chuva", "Valor": missing["precipitacao_mm"]},  # Nulos em chuva
                    {"Indicador": "Ausentes em temp. máx.", "Valor": missing["temp_max_c"]},  # Nulos em temp. máx.
                    {"Indicador": "Ausentes em temp. mín.", "Valor": missing["temp_min_c"]},  # Nulos em temp. mín.
                    {"Indicador": "Outliers (IQR)", "Valor": sum(outliers.values())},  # Soma total de outliers detectados
                ]  # Fecha lista de linhas
            )  # Fecha DataFrame
            st.dataframe(qualidade_df, hide_index=True)  # Exibe a tabela de qualidade sem índice


def render_charts_tab(filtered: pd.DataFrame) -> None:  # Renderiza a aba "📈 Gráficos"
    if filtered.empty:  # Verifica se há dados no recorte filtrado
        st.warning("Nenhum dado disponível para os filtros atuais.")  # Aviso caso não haja registros
        return  # Interrompe a renderização

    col_ctrl1, col_ctrl2 = st.columns([1, 1])  # Cria duas colunas iguais para os controles dos gráficos
    with col_ctrl1:  # Primeira coluna de controle
        granularity = st.radio("Agrupamento", ["Por mês", "Por dia"], horizontal=True)  # Seletor de granularidade temporal

    if granularity == "Por mês":  # Se o usuário escolheu visão mensal
        chart_df = monthly_summary(filtered).copy()  # Agrega os dados por mês
        chart_df["label"] = chart_df["mes_nome"]  # Define rótulo do eixo X como o nome do mês
        x_title = "Mês"  # Título do eixo X
    else:  # Se o usuário escolheu visão diária ("Por dia")
        months = sorted(int(m) for m in filtered["mes"].dropna().unique())  # Lista ordenada dos meses presentes no recorte
        with col_ctrl2:  # Segunda coluna de controle (exibida apenas no modo diário)
            selected_month = st.selectbox(  # Caixa de seleção para escolher um mês específico ou todos
                "Filtrar mês",  # Rótulo do selectbox
                options=["todos", *months],  # Opção "todos" seguida dos números de mês disponíveis
                format_func=lambda m: "Todos os meses" if m == "todos" else MESES_PT.get(m, str(m)),  # Formata número para nome do mês
            )  # Fecha selectbox
        chart_df = daily_summary(filtered).copy()  # Agrega os dados por dia
        if selected_month != "todos":  # Se um mês específico foi selecionado
            chart_df = chart_df[chart_df["dia"].dt.month == selected_month]  # Filtra apenas os dias daquele mês
        chart_df["label"] = chart_df["dia"].dt.strftime("%d/%m")  # Formata o eixo X como "DD/MM"
        x_title = "Dia"  # Título do eixo X

    if chart_df.empty:  # Verifica se sobrou algum registro após filtrar o mês no gráfico diário
        st.info("Sem registros para a seleção atual.")  # Mensagem informativa
        return  # Encerra renderização

    with st.container(border=True):  # Cartão com borda para o gráfico de precipitação
        fig_rain = px.bar(  # Cria gráfico de barras de chuva com Plotly Express
            chart_df,  # DataFrame base
            x="label",  # Eixo X: mês ou dia
            y="precipitacao_mm",  # Eixo Y: precipitação acumulada
            title="Precipitação acumulada (mm)",  # Título do gráfico
            labels={"label": x_title, "precipitacao_mm": "Chuva (mm)"},  # Rótulos dos eixos
            color="precipitacao_mm",  # Colore as barras conforme intensidade da chuva
            color_continuous_scale="Blues",  # Escala de azul
        )  # Fecha px.bar
        fig_rain.update_layout(  # Ajusta aparência do gráfico de barras
            template="plotly_white",  # Tema limpo
            paper_bgcolor="rgba(0,0,0,0)",  # Fundo externo transparente
            plot_bgcolor="rgba(0,0,0,0)",  # Fundo interno transparente
            coloraxis_showscale=False,  # Oculta barra lateral da escala de cores
            hovermode="x unified",  # Tooltip unificado no eixo X
            height=360,  # Altura em pixels
            margin=dict(t=45, b=20),  # Margens superior e inferior
        )  # Fecha update_layout
        st.plotly_chart(fig_rain, width="stretch")  # Exibe o gráfico ocupando toda a largura disponível

    with st.container(border=True):  # Cartão com borda para o gráfico de amplitude térmica
        fig_temp = go.Figure()  # Inicializa uma figura vazia do Plotly Graph Objects
        fig_temp.add_trace(  # Adiciona a primeira curva: temperatura máxima média
            go.Scatter(  # Tipo dispersão/linha
                x=chart_df["label"],  # Eixo X: mês ou dia
                y=chart_df["temp_max_media"],  # Eixo Y: máxima média
                name="Temp. máxima média (°C)",  # Nome na legenda
                mode="lines+markers",  # Linha com marcadores nos pontos
                line=dict(color=ORANGE, width=2.5),  # Cor laranja e espessura 2.5
            )  # Fecha Scatter
        )  # Fecha add_trace
        fig_temp.add_trace(  # Adiciona a segunda curva: temperatura mínima média
            go.Scatter(  # Tipo dispersão/linha
                x=chart_df["label"],  # Eixo X: mês ou dia
                y=chart_df["temp_min_media"],  # Eixo Y: mínima média
                name="Temp. mínima média (°C)",  # Nome na legenda
                mode="lines+markers",  # Linha com marcadores
                line=dict(color=BLUE, width=2.5),  # Cor azul e espessura 2.5
                fill="tonexty",  # Preenche a área entre esta curva e a curva anterior (mostra a amplitude térmica)
                fillcolor="rgba(40, 120, 181, 0.12)",  # Azul translúcido para o preenchimento entre as linhas
            )  # Fecha Scatter
        )  # Fecha add_trace
        fig_temp.update_layout(  # Configura layout do gráfico de temperatura
            title="Amplitude térmica média (°C)",  # Título do gráfico
            xaxis_title=x_title,  # Rótulo do eixo X
            yaxis_title="Temperatura (°C)",  # Rótulo do eixo Y
            template="plotly_white",  # Tema branco
            paper_bgcolor="rgba(0,0,0,0)",  # Fundo externo transparente
            plot_bgcolor="rgba(0,0,0,0)",  # Fundo interno transparente
            hovermode="x unified",  # Mostra máxima e mínima juntas no hover
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),  # Legenda horizontal no topo direito
            height=380,  # Altura em pixels
            margin=dict(t=55, b=20),  # Margens
        )  # Fecha update_layout
        st.plotly_chart(fig_temp, width="stretch")  # Renderiza o gráfico na interface

    with st.container(border=True):  # Cartão com borda para a matriz de correlação
        corr = correlation_matrix(filtered).rename(  # Calcula correlação e renomeia índices/colunas para exibição amigável
            index={"precipitacao_mm": "Chuva", "temp_max_c": "Temp. máx.", "temp_min_c": "Temp. mín."},  # Rótulos das linhas
            columns={"precipitacao_mm": "Chuva", "temp_max_c": "Temp. máx.", "temp_min_c": "Temp. mín."},  # Rótulos das colunas
        )  # Fecha rename
        fig_corr = px.imshow(  # Gera mapa de calor (heatmap) da matriz de correlação
            corr,  # Matriz 3x3
            text_auto=".2f",  # Exibe os valores numéricos com 2 casas decimais dentro de cada célula
            zmin=-1,  # Limite mínimo da escala de correlação (-1)
            zmax=1,  # Limite máximo da escala de correlação (+1)
            color_continuous_scale="RdBu_r",  # Paleta divergente vermelho/azul invertida
            title="Correlação entre variáveis",  # Título do gráfico
        )  # Fecha px.imshow
        fig_corr.update_layout(  # Ajusta layout do mapa de calor
            template="plotly_white",  # Tema branco
            paper_bgcolor="rgba(0,0,0,0)",  # Fundo transparente
            plot_bgcolor="rgba(0,0,0,0)",  # Fundo interno transparente
            height=350,  # Altura em pixels
            margin=dict(t=45, b=20),  # Margens
        )  # Fecha update_layout
        st.plotly_chart(fig_corr, width="stretch")  # Renderiza o heatmap


def render_table_tab(full_df: pd.DataFrame) -> None:  # Renderiza a aba "✏️ Tabela editável"
    st.caption("Edite chuva, temperatura máxima ou mínima diretamente na tabela e clique em **Salvar edições**.")  # Instrução ao usuário
    editable_cols = ["data_hora", "precipitacao_mm", "temp_max_c", "temp_min_c"]  # Colunas exibidas no editor

    with st.form("editor_form"):  # Agrupa a tabela e o botão dentro de um formulário para evitar recargas a cada célula editada
        edited = st.data_editor(  # Componente interativo de tabela editável
            full_df[editable_cols],  # Passa a base completa com as 4 colunas principais
            disabled=["data_hora"],  # Impede edição da coluna de data e hora
            hide_index=True,  # Oculta índice do pandas
            height=480,  # Altura fixa com rolagem
            column_config={  # Regras de validação e formato por coluna
                "data_hora": st.column_config.DatetimeColumn("Data e hora", format="DD/MM/YYYY HH:mm"),  # Formato data/hora BR
                "precipitacao_mm": st.column_config.NumberColumn("Chuva (mm)", min_value=0.0, step=0.1, format="%.1f"),  # Não permite chuva negativa
                "temp_max_c": st.column_config.NumberColumn("Temp. máx. (°C)", step=0.1, format="%.1f"),  # Passo de 0.1 °C
                "temp_min_c": st.column_config.NumberColumn("Temp. mín. (°C)", step=0.1, format="%.1f"),  # Passo de 0.1 °C
            },  # Fecha column_config
        )  # Fecha st.data_editor
        submitted = st.form_submit_button("💾 Salvar edições", type="primary")  # Botão de envio do formulário

    if submitted:  # Quando o usuário clicar em "Salvar edições"
        for col in ["precipitacao_mm", "temp_max_c", "temp_min_c"]:  # Percorre as 3 colunas editáveis
            st.session_state["df"].loc[edited.index, col] = pd.to_numeric(edited[col], errors="coerce")  # Atualiza o DataFrame na sessão convertendo para numérico
        st.success("Edições salvas na sessão atual! Os gráficos e KPIs já foram atualizados.")  # Mensagem de confirmação
        st.rerun()  # Reexecuta o app para refletir imediatamente os novos valores em todas as abas


def render_explorer_tab(filtered: pd.DataFrame) -> None:  # Renderiza a aba "🔍 Explorador"
    st.caption(f"Exibindo {br_number(len(filtered), 0)} registros conforme os filtros da barra lateral.")  # Informa quantas linhas passaram pelos filtros
    st.dataframe(  # Exibe tabela somente leitura com os registros filtrados
        filtered[["data_hora", "precipitacao_mm", "temp_max_c", "temp_min_c"]],  # Seleciona as 4 colunas principais
        hide_index=True,  # Oculta o índice
        height=480,  # Altura fixa da tabela
        column_config={  # Formatação visual das colunas
            "data_hora": st.column_config.DatetimeColumn("Data e hora", format="DD/MM/YYYY HH:mm"),  # Formato de data e hora
            "precipitacao_mm": st.column_config.NumberColumn("Chuva (mm)", format="%.1f"),  # 1 casa decimal
            "temp_max_c": st.column_config.NumberColumn("Temp. máx. (°C)", format="%.1f"),  # 1 casa decimal
            "temp_min_c": st.column_config.NumberColumn("Temp. mín. (°C)", format="%.1f"),  # 1 casa decimal
        },  # Fecha column_config
    )  # Fecha st.dataframe