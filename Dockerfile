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

# O WORKDIR é criado como root: sem o chown abaixo o `collectstatic` (que roda
# como appuser na entrada do container) não consegue escrever em staticfiles/.
RUN mkdir -p /app/staticfiles && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# gunicorn serve o WSGI e o WhiteNoise entrega os estáticos coletados
# (`collectstatic` roda na entrada do container, quando o .env já existe).
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import sys, urllib.request; \
sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/login/').status == 200 else 1)"

CMD ["sh", "-c", "python manage.py migrate --noinput && \
python manage.py collectstatic --noinput --clear && \
exec gunicorn core.wsgi:application \
--bind 0.0.0.0:8000 --workers 3 --timeout 60 --access-logfile -"]
