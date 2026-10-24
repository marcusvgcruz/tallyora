# 07 — Setup e Execução Local

## Requisitos

- Python 3.12+
- Git
- Nada de banco instalado para desenvolvimento: em `dev` o projeto usa **SQLite**.
- PostgreSQL 16+ apenas para o modo `prd`.

## Dois ambientes: `dev` e `prd`

O banco é escolhido pela variável `APP_ENV` do `.env`:

| `APP_ENV` | Banco | Uso |
| :--- | :--- | :--- |
| `dev` (**padrão**) | SQLite em `db.sqlite3` na raiz | máquina local, testes, primeiro contato |
| `prd` | PostgreSQL (`DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`) | VPS/produção |

- Valor inválido em `APP_ENV` derruba o start com `ImproperlyConfigured` — não existe "meio ambiente".
- `DEBUG` cai no default de cada ambiente (`True` em `dev`, `False` em `prd`) quando não está no `.env`.
- `db.sqlite3` é **por máquina** e está no `.gitignore`: nunca é commitado nem compartilhado.
- O mesmo banco não é compartilhado entre modos; migrar em `prd` não cria tabelas no SQLite e vice-versa.

## Variáveis de ambiente

| Variável | Obrigatória? | Para que serve |
| :--- | :--- | :--- |
| `SECRET_KEY` | **sim** | chave do Django; gere uma por ambiente |
| `DEBUG` | não | default por ambiente (`True` em `dev`, `False` em `prd`) |
| `APP_ENV` | não | `dev` (SQLite) ou `prd` (PostgreSQL); default `dev` |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` | só em `prd` | conexão PostgreSQL |
| `BRAPI_TOKEN` | não | cotações extras; a B3 não pede chave |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` / `GOOGLE_REFRESH_TOKEN` | não | espelho opcional do Google Calendar |

### Google Calendar (opcional)

Sem as três variáveis `GOOGLE_*`, os lembretes funcionam 100% por cadastro manual e o
dashboard apenas informa que a integração não está configurada. Para ligar:

1. No Google Cloud Console, crie um OAuth Client do tipo *Desktop app* e habilite a
   **Google Calendar API**.
2. Autorize uma vez com o escopo `https://www.googleapis.com/auth/calendar.readonly` e
   guarde o `refresh_token` devolvido.
3. Preencha `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` e `GOOGLE_REFRESH_TOKEN` no `.env`
   (nunca no código, nunca no Git) e reinicie o processo.

O serviço fala direto com a API v3 usando só a biblioteca padrão do Python — não há
dependência nova. Ele **lê** a agenda e espelha os eventos do dia em `DailyReminder`;
não escreve nada no Google.

## Primeira execução (5 comandos)

```bash
cd ~/projetos/tallyora
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # depois edite SECRET_KEY
```

Gere a `SECRET_KEY` sem copiar de ninguém:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Depois:

```bash
python manage.py migrate                 # cria o db.sqlite3 e as tabelas
python manage.py tailwind install        # uma vez por ambiente (baixa o CLI)
python manage.py tailwind build          # compila o CSS
python manage.py createsuperuser         # pede e-mail, não username
python manage.py runserver
```

Aplicação em `http://127.0.0.1:8000/`.

## Acesso pelo VS Code via SSH (código na VPS)

O projeto roda **na VPS**; o navegador do seu PC precisa de um túnel. Duas formas:

**1. Port forwarding do VS Code (mais simples)**

1. `Ctrl+Shift+P` → *Ports: Focus on Ports View* (aba **PORTS** no painel inferior).
2. **Forward a Port** → `8000`.
3. Rode `python manage.py runserver 127.0.0.1:8000` no terminal do VS Code.
4. Abra `http://127.0.0.1:8000` no navegador do seu PC. O VS Code encaminha para a VPS.

**2. Túnel SSH manual (fora do VS Code)**

```bash
# no seu PC
ssh -L 8000:127.0.0.1:8000 hermes@<ip-da-vps>
# na VPS
python manage.py runserver 127.0.0.1:8000
```

Se a porta 8000 já estiver ocupada na VPS, use outra e encaminhe a mesma:

```bash
python manage.py runserver 127.0.0.1:8001     # e encaminhe 8001
```

Para o `runserver` aceitar o host encaminhado, mantenha `ALLOWED_HOSTS=127.0.0.1,localhost` no `.env` e acesse pelo `127.0.0.1` do seu PC (o forwarding preserva o `Host`).

## Rodando em `prd` (PostgreSQL)

```bash
# .env
APP_ENV=prd
DB_NAME=tallyora
DB_USER=tallyora
DB_PASSWORD=<senha>
DB_HOST=127.0.0.1
DB_PORT=5432
```

Provisionamento do banco (uma vez, como superusuário do sistema):

```bash
sudo -u postgres psql -c "CREATE ROLE tallyora WITH LOGIN PASSWORD '<senha>' CREATEDB;"
sudo -u postgres psql -c "CREATE DATABASE tallyora OWNER tallyora ENCODING 'UTF8';"
python manage.py migrate
```

`CREATEDB` no role é necessário para o Django criar o banco de teste ao rodar `manage.py test`.

## Migrações

```bash
python manage.py makemigrations   # após criar/alterar models
python manage.py migrate          # aplica no banco do APP_ENV atual
```

Nunca edite uma migração já aplicada; gere uma nova.

## Tailwind (CSS)

O CSS é compilado localmente com `django-tailwind` (app `theme/`, CLI standalone). **A cada mudança de template é obrigatório rebuildar:**

```bash
python manage.py tailwind build
```

- Fonte: `theme/static_src/src/styles.css` (importa o Tailwind e escaneia templates/py/js).
- Saída: `theme/static/css/dist/styles.css` — **versionada**, é o arquivo servido em runtime.
- Se uma classe nova não aparecer na página, faltou o build.
- `tailwind install` baixa o binário do CLI; é por ambiente, não por projeto.
- Chart.js é local (`theme/static/js/chart.umd.min.js`), sem CDN.

## Variáveis de ambiente

| Arquivo | Estado |
| :--- | :--- |
| `.env` | **Não versionado** (permissão `600`), criado a partir do `.env.example`. |
| `.env.example` | Versionado — template com as chaves e valores de exemplo, sem segredo. |

Chaves:

```text
APP_ENV=dev            # dev (sqlite) | prd (postgresql)

SECRET_KEY=<gerada>
DEBUG=True             # opcional; default por ambiente
ALLOWED_HOSTS=127.0.0.1,localhost

DB_NAME=tallyora       # só em prd
DB_USER=tallyora
DB_PASSWORD=
DB_HOST=127.0.0.1
DB_PORT=5432
```

O `core/settings.py` lê o `.env` via `python-dotenv` e falha ao subir sem `SECRET_KEY`. Regra: `.env` nunca é commitado; chave nova entra primeiro no `.env.example`.

## Superusuário (painel admin)

```bash
python manage.py createsuperuser
```

Pede **e-mail** (não username), porque `USERNAME_FIELD = 'email'`.

## Rotas publicadas

| Rota | O que é |
| :--- | :--- |
| `/` | Landing page pública (logado é redirecionado para `/dashboard/`) |
| `/register/`, `/login/`, `/logout/` | Autenticação por e-mail (logout só via POST) |
| `/dashboard/` | Painel provisório (dados chegam na Sprint 5) |
| `/perfil/` | Perfil financeiro e descontos de folha |
| `/contas/`, `/categorias/` | Contas/cartões e categorias |
| `/transacoes/`, `/transacoes/fixas/` | Transações com filtro de período e despesas fixas |
| `/caixinhas/`, `/caixinhas/eventos/` | Caixinhas e eventos (casamento, viagens) |
| `/investimentos/` | Carteira P3X com cotações |
| `/admin/` | Django admin |

## Execução com Docker

`Dockerfile` (`python:3.12-slim`, usuário não-root, `HEALTHCHECK` em `/login/`) e
`docker-compose.yml` com `web` + `db` (`postgres:16-alpine`, volume nomeado `pgdata`,
`healthcheck` com `pg_isready` e `depends_on: service_healthy`).

```bash
cp .env.example .env      # preencha SECRET_KEY
docker compose up --build # http://localhost:8080/
docker compose down       # derruba (mantém os dados)
docker compose down -v    # derruba e apaga o volume do banco
```

- O `web` roda `migrate --noinput` → `collectstatic --noinput` → **`gunicorn core.wsgi`**
  (3 workers). O `collectstatic` roda na entrada do container porque depende do `.env`
  (o `SECRET_KEY`) — não dá para fazê-lo no build sem vazar segredo em camada.
- O WhiteNoise serve os estáticos coletados (`CompressedManifestStaticFilesStorage`), então
  não é preciso nginx para o CSS/JS neste cenário.
- **A porta 5432 não é publicada** — o banco só existe na rede interna do Compose, para
  não conflitar com um PostgreSQL instalado na máquina.
- A porta do host é configurável: `WEB_PORT=8081 docker compose up -d` (o default é 8080;
  na VPS a 8080 já é do `evolution_api`).
- Sem `collectstatic` no build: o CSS do Tailwind é versionado em
  `theme/static/css/dist/` e o `runserver` serve os estáticos. Para uso atrás de um servidor
  de verdade, rode `python manage.py collectstatic` (destino: `staticfiles/`, não versionado).
- Servidor: `gunicorn==23.0.0` está no `requirements.txt` (as ferramentas de
  desenvolvimento ficam em `requirements-dev.txt`).
- Testes dentro do container: `docker compose exec web python manage.py test`.

## Recuperação de senha e e-mail

O fluxo "esqueci minha senha" funciona sem SMTP: com `EMAIL_HOST` vazio, o Django imprime
o e-mail no terminal (`console.EmailBackend`) — serve para desenvolvimento e testes.
Para enviar de verdade, preencha no `.env`:

```bash
EMAIL_HOST=smtp.seudominio.com
EMAIL_PORT=587
EMAIL_HOST_USER=no-reply@seudominio.com
EMAIL_HOST_PASSWORD=...
EMAIL_USE_TLS=True
```

O projeto usa o dicionário **`MAILERS`** (padrão do Django 6.1); as opções do backend SMTP
vão dentro de `OPTIONS` (`host`, `port`, `username`, `password`, `use_tls`). Conviver com
`EMAIL_BACKEND`/`EMAIL_HOST` soltos faz o Django 6.1 levantar `ImproperlyConfigured`.

## Versionamento

Repositório Git, branch `main`, remoto público: `https://github.com/marcusvgcruz/tallyora`.

```bash
git add -A && git commit -m "mensagem" && git push
```

**Não versionados** (`.gitignore`): `venv/`, `__pycache__/`, `db.sqlite3`, `.env`, `node_modules/`, caches. Confirme com `git status` antes de commitar.

## Comandos úteis

| Comando | Para quê |
| :--- | :--- |
| `python manage.py check` | Valida a configuração do projeto |
| `python manage.py makemigrations` | Gera migração a partir dos models |
| `python manage.py migrate` | Aplica migrações pendentes |
| `python manage.py createsuperuser` | Cria usuário do admin |
| `python manage.py shell` | Shell interativo com o ORM carregado |
| `python manage.py test` | Roda a suíte de testes |
| `python manage.py tailwind build` | Recompila o CSS após mudar template |
