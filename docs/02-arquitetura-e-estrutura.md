# 02 — Arquitetura e Estrutura

## Stack atual (verificada no ambiente)

| Item | Versão / estado real |
| :--- | :--- |
| Python | 3.12.3 (`venv/bin/python`) |
| Django | 6.1.2 |
| psycopg2-binary | 2.9.13 (instalado; conexão PostgreSQL **ainda não configurada**) |
| python-dotenv | 1.2.4 (instalado; **nenhum `.env` existe ainda**) |
| Banco de dados | SQLite (`db.sqlite3`) com as migrações padrão do Django aplicadas |
| Frontend | Ainda não implementado — previsto DTL + TailwindCSS + Chart.js |

> O PRD cita "Django 5.x" e banco PostgreSQL. O que está instalado hoje é **Django 6.1.2** sobre **SQLite**. A migração para PostgreSQL é a tarefa 1.1.3 do backlog. Ver `08-estado-do-projeto.md`.

## Estrutura de diretórios real

```text
tallyora/
├── manage.py
├── requirements.txt
├── db.sqlite3              # banco atual (SQLite)
├── venv/                   # ambiente virtual Python 3.12.3
├── PRD.md                  # documento de produto
├── TASKS.md                # backlog por sprints
├── docs/                   # esta documentação
├── core/                   # projeto Django: settings, urls, wsgi, asgi
├── users/                  # app de usuários
├── profiles/               # app de perfil financeiro
├── accounts/               # app de contas e cartões
├── categories/             # app de categorias
├── transactions/           # app de transações e motor de cálculo
├── goals_events/           # app de caixinhas e eventos
├── investments/            # app de carteira
└── reminders/              # app de lembretes
```

Cada app segue o esqueleto gerado pelo Django: `models.py`, `views.py`, `admin.py`, `apps.py`, `tests.py`, `migrations/`.

**Ainda não existem** as pastas `templates/` e `static/`. Elas estão previstas na estrutura-alvo do PRD e serão criadas na tarefa 1.3 (design system).

## Camadas e responsabilidades

| Camada | Arquivo | Regra |
| :--- | :--- | :--- |
| Configuração | `core/settings.py`, `core/urls.py` | Único ponto de configuração do projeto; URL raiz inclui as rotas de cada app |
| Rotas | `<app>/urls.py` | Arquivo por app, incluído no `core/urls.py`; rotas nomeadas com namespace da app (`core:dashboard`, `core:landing`) |
| Regras de dados | `<app>/models.py` | Todo model herda de `BaseModel`; campos em inglês |
| Entrada de dados | `<app>/forms.py` | `ModelForm`/`Form` com validação em `clean()` e widgets estilizados via Tailwind |
| Interface | `<app>/views.py` | Class-Based Views com `LoginRequiredMixin`, `get_queryset()` filtrado por usuário |
| Cálculo | `transactions/services.py`, `investments/services.py`, `reminders/services.py` | Regra de negócio fora das views (ver `05-regras-de-negocio-financeiras.md`) |
| Efeitos colaterais | `<app>/signals.py` | Registrados no `ready()` do `apps.py` |
| Templates | `templates/` | DTL, herdam de `base.html` (área logada) ou `base_public.html` (pública) |

`services.py` e `signals.py` aparecem no backlog (`TASKS.md` 3.3.1, 4.2.4, 5.1.3 e 2.1.3/2.3.2) — são a convenção adotada para onde a lógica deve ir, ainda não existem em disco.

## Configuração atual do `core/settings.py`

Valores presentes hoje no arquivo:

- `INSTALLED_APPS`: apps padrão do Django + as 8 apps do projeto.
- `DEBUG = True`, `ALLOWED_HOSTS = []`, `SECRET_KEY` de desenvolvimento gerada pelo `startproject`.
- `DATABASES`: SQLite em `BASE_DIR / 'db.sqlite3'`.
- `LANGUAGE_CODE = 'en-us'`, `TIME_ZONE = 'UTC'`, `USE_I18N = True`, `USE_TZ = True`.
- `TEMPLATES`: backend DTL com `APP_DIRS = True` (as pastas `templates/` das apps são lidas automaticamente).
- `MAILERS`: backend de e-mail no console (útil para testar a recuperação de senha sem servidor SMTP).
- `STATIC_URL = 'static/'`.
- `MIDDLEWARE` e `AUTH_PASSWORD_VALIDATORS` padrão do Django.

## Rotas atuais

`core/urls.py` expõe apenas:

```python
path('admin/', admin.site.urls)
```

Todas as outras rotas definidas no PRD (`/`, `/register/`, `/login/`, `/profile/setup/`, `/dashboard/`, `/transactions/`, `/investments/`, `/events/`, `/reminders/`) são **planejadas** e ainda não existem.

## O que não usar

Decisão explícita do PRD (RNF01): nada de microserviços, SPA separada, Celery, Redis. A aplicação é um monólito Django com DTL.
