# 07 — Setup e Execução Local

## Requisitos

- Python 3.12+
- Git (opcional, o projeto ainda não é um repositório versionado)
- PostgreSQL 16+ (necessário apenas quando a tarefa 1.1.3 for concluída; hoje roda em SQLite)

## Ambiente já existente

O projeto já tem um ambiente virtual criado em `venv/` (Python 3.12.3) com as dependências de `requirements.txt` instaladas:

```text
Django==6.1.2
psycopg2-binary==2.9.13
python-dotenv==1.2.4
asgiref==3.13.0
sqlparse==0.6.0
```

Verificação de sanidade do projeto:

```bash
cd ~/projetos/tallyora
./venv/bin/python manage.py check
# System check identified no issues (0 silenced).
```

## Ativar o ambiente

```bash
cd ~/projetos/tallyora
source venv/bin/activate
```

> O diretório do ambiente virtual é `venv/` (sem ponto). O PRD menciona `.venv`; o que existe no disco é `venv/`.

## Rodar o servidor de desenvolvimento

```bash
python manage.py runserver
```

Disponível em `http://127.0.0.1:8000/`. Rotas publicadas hoje:

| Rota | O que é |
| :--- | :--- |
| `/` | Landing page pública (logado é redirecionado para `/dashboard/`) |
| `/register/` | Cadastro por e-mail |
| `/login/` | Login por e-mail |
| `/logout/` | Logout (aceita **somente POST**) |
| `/dashboard/` | Painel provisório (dados chegam na Sprint 5) |
| `/admin/` | Django admin |

## Recriar o ambiente do zero (se necessário)

```bash
cd ~/projetos/tallyora
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Banco de dados (PostgreSQL)

O projeto usa **PostgreSQL 16** (serviço `postgresql` na VPS). Provisionamento já feito:

```bash
# executado como superusuário do sistema
sudo -u postgres psql -c "CREATE ROLE tallyora WITH LOGIN PASSWORD '<senha>';"
sudo -u postgres psql -c "CREATE DATABASE tallyora OWNER tallyora ENCODING 'UTF8';"
```

A senha fica **somente** no `.env` (`DB_PASSWORD`). Para conferir a conexão:

```bash
PGPASSWORD="$(grep '^DB_PASSWORD=' .env | cut -d= -f2-)" \
  psql -h 127.0.0.1 -U tallyora -d tallyora -c 'select current_user;'
```

## Migrações

```bash
python manage.py makemigrations   # após criar/alterar models
python manage.py migrate          # aplica no banco
```

Estado atual: todas as migrações aplicadas, incluindo `users.0001_initial` (o `CustomUser`).

## Tailwind (CSS)

O CSS é compilado localmente com `django-tailwind` (app `theme/`, CLI standalone). **A cada mudança de template é obrigatório rebuildar:**

```bash
python manage.py tailwind build
```

- Fonte: `theme/static_src/src/styles.css` (importa o Tailwind e escaneia templates/py/js).
- Saída: `theme/static/css/dist/styles.css` — **versionada**, é o arquivo servido em runtime.
- Se uma classe nova não aparecer na página, faltou o build (ou a classe está em arquivo fora do `@source`).
- Primeira instalação do CLI (uma vez por ambiente): `python manage.py tailwind install`.

## Superusuário (painel admin)

```bash
python manage.py createsuperuser
```

O `createsuperuser` pede **e-mail** (não username), porque `USERNAME_FIELD = 'email'`.


## Variáveis de ambiente

O projeto **já possui** dois arquivos na raiz:

| Arquivo | Estado |
| :--- | :--- |
| `.env` | **Criado localmente, não versionado** (permissão `600`, `SECRET_KEY` já gerada com 50 caracteres). Está no `.gitignore`. |
| `.env.example` | Versionado — template com as chaves e valores de exemplo, sem segredo. |

Chaves existentes:

```text
SECRET_KEY=<gerada>
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

DB_NAME=tallyora
DB_USER=tallyora
DB_PASSWORD=
DB_HOST=127.0.0.1
DB_PORT=5432
```

O `core/settings.py` **lê o `.env`** via `python-dotenv` e falha ao subir sem `SECRET_KEY`. O bloco `DB_*` está preenchido com as credenciais reais do PostgreSQL local.

Regra: `.env` nunca é commitado; qualquer chave nova entra primeiro no `.env.example`.

## Execução com Docker

Planejada para a Sprint 6 (tarefas 6.3.1–6.3.3): `Dockerfile` em `python:3.12-slim` e `docker-compose.yml` com os serviços `web` (Django) e `db` (PostgreSQL 16), volume persistente e `healthcheck`. **Ainda não existe nada disso no projeto.**

## Versionamento

O projeto é um repositório Git com branch padrão `main` e remoto público:

```text
https://github.com/marcusvgcruz/tallyora
```

Fluxo:

```bash
git add -A
git commit -m "mensagem"
git push
```

**Não versionados** (por `.gitignore`): `venv/`, `__pycache__/`, `db.sqlite3`, `.env`, arquivos de cobertura e caches de ferramentas. Antes de commitar, confirme com `git status` que nada disso aparece na lista.

## Comandos úteis

| Comando | Para quê |
| :--- | :--- |
| `python manage.py check` | Valida a configuração do projeto |
| `python manage.py makemigrations` | Gera migração a partir dos models |
| `python manage.py migrate` | Aplica migrações pendentes |
| `python manage.py createsuperuser` | Cria usuário do admin |
| `python manage.py shell` | Shell interativo com o ORM carregado |
| `python manage.py test` | Roda a suíte de testes |
