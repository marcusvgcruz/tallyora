# Tallyora — imagem de execução (Django 6.1 / Python 3.12)
# Build:  docker build -t tallyora:sprint6 .
# Run:    docker compose up --build   (ver docker-compose.yml)

FROM python:3.12-slim

# Não gera .pyc e não bufferiza stdout/stderr (logs em tempo real).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DJANGO_SETTINGS_MODULE=core.settings

WORKDIR /app

# Dependências primeiro: o cache da layer só é invalidado quando
# o requirements.txt muda. psycopg2-binary já traz libpq e libssl
# embutidas, então não é preciso compilador nem libpq-dev nesta imagem.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Usuário sem privilégios (não-root).
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin appuser

# O CSS compilado é versionado em theme/static/css/dist/styles.css.
# Por isso o build NÃO roda `tailwind build` (o CLI baixaria binário
# da internet e quebraria build offline). Ver docs/07.
COPY --chown=appuser:appuser . .

USER appuser

EXPOSE 8000

# gunicorn não está no requirements.txt; o servidor é o runserver do
# Django (desvio consciente, documentado no README).
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import sys, urllib.request; \
sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/login/').status == 200 else 1)"

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
