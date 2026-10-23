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

Disponível em `http://127.0.0.1:8000/`. Hoje a única rota publicada é `http://127.0.0.1:8000/admin/`.

## Recriar o ambiente do zero (se necessário)

```bash
cd ~/projetos/tallyora
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Migrações

```bash
python manage.py makemigrations   # após criar/alterar models
python manage.py migrate          # aplica no banco
```

O banco atual (`db.sqlite3`) já está migrado com as tabelas padrão do Django.

## Superusuário (painel admin)

```bash
python manage.py createsuperuser
```

Ainda não há model de usuário customizado — quando o `CustomUser` entrar (Sprint 1.2), o `createsuperuser` passa a pedir **e-mail** em vez de username.

## Variáveis de ambiente

Ainda **não existe** arquivo `.env` no projeto. Quando a tarefa 1.1.3 for executada, o padrão é:

1. Criar `.env` na raiz (não versionado).
2. Ler com `python-dotenv` no `core/settings.py`.
3. Chaves previstas: credenciais do PostgreSQL (`DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`), `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`.

Nunca commitar `.env` nem deixar credenciais no `settings.py`.

## Execução com Docker

Planejada para a Sprint 6 (tarefas 6.3.1–6.3.3): `Dockerfile` em `python:3.12-slim` e `docker-compose.yml` com os serviços `web` (Django) e `db` (PostgreSQL 16), volume persistente e `healthcheck`. **Ainda não existe nada disso no projeto.**

## Comandos úteis

| Comando | Para quê |
| :--- | :--- |
| `python manage.py check` | Valida a configuração do projeto |
| `python manage.py makemigrations` | Gera migração a partir dos models |
| `python manage.py migrate` | Aplica migrações pendentes |
| `python manage.py createsuperuser` | Cria usuário do admin |
| `python manage.py shell` | Shell interativo com o ORM carregado |
| `python manage.py test` | Roda a suíte de testes |
