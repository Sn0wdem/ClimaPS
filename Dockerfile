# ==============================================================================
# Dockerfile - ClimaPS
# Imagem otimizada para o painel Streamlit com usuário não-root e persistência
# ==============================================================================

# Imagem base oficial do Python (slim para reduzir tamanho e superfície de ataque)
FROM python:3.12-slim

# Metadados e variáveis de ambiente essenciais para Python e Streamlit
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Diretório padrão da aplicação no container
WORKDIR /app

# Instala curl para healthcheck e certificados CA para requisições HTTPS seguras
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Cria usuário e grupo não-privilegiados para execução segura
RUN groupadd -r -g 1000 appuser && \
    useradd -r -u 1000 -g appuser -m appuser

# Copia e instala as dependências antes do código para aproveitar o cache de camadas
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copia o código-fonte da aplicação
COPY . .

# Cria as pastas de persistência e ajusta as permissões para o appuser
RUN mkdir -p /app/data/importados /app/exportacoes && \
    chown -R appuser:appuser /app

# Altera para o usuário não-root
USER appuser

# Expõe a porta padrão do Streamlit
EXPOSE 8501

# Verificação de saúde nativa via endpoint do Streamlit
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Comando padrão de inicialização
CMD ["streamlit", "run", "app_streamlit.py", "--server.port=8501", "--server.address=0.0.0.0"]
