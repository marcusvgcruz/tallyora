# 08 — Estado do Projeto

Retrato do que existe em disco hoje (23/10/2026), verificado diretamente no código. O backlog completo e atualizado está em `../TASKS.md`.

## Implementado

| Item | Evidência |
| :--- | :--- |
| Ambiente virtual Python 3.12.3 | pasta `venv/` com Django 6.1.2 e dependências instaladas |
| `requirements.txt` com 5 dependências fixadas | Django, psycopg2-binary, python-dotenv, asgiref, sqlparse |
| Projeto Django `core` inicializado | `core/settings.py`, `core/urls.py`, `core/wsgi.py`, `core/asgi.py` |
| 8 apps de domínio criadas e registradas em `INSTALLED_APPS` | `users`, `profiles`, `accounts`, `categories`, `transactions`, `goals_events`, `investments`, `reminders` |
| Banco SQLite migrado com as tabelas padrão do Django | `db.sqlite3` com `auth_*`, `admin`, `sessions`, `contenttypes` |
| Rota do admin publicada | `core/urls.py` → `path('admin/', admin.site.urls)` |
| `manage.py check` sem erros | executado no ambiente atual |

Tarefas marcadas como concluídas no `TASKS.md`: **1.1.1** e **1.1.2**.

## Não implementado

Nenhum model de domínio existe. Todos os `models.py`, `views.py`, `forms.py` (inexistentes), `admin.py` e `tests.py` das apps estão no estado gerado pelo Django (só o cabeçalho/import, sem conteúdo).

Também não existem: `templates/`, `static/`, `.env`, `.gitignore`, `signals.py`, `services.py`, `urls.py` por app, `BaseModel`, `CustomUser`, migrations de domínio, Docker, testes.

## Próximos passos na ordem do backlog (Sprint 1)

| Tarefa | O que entrega |
| :--- | :--- |
| 1.1.3 | Remover `db.sqlite3` e configurar PostgreSQL via `.env` |
| 1.1.4 | `LANGUAGE_CODE = 'pt-br'`, `TIME_ZONE = 'America/Sao_Paulo'` |
| 1.1.5 | `BaseModel` abstrato em `core/models.py` |
| 1.2.x | `CustomUser` com login por e-mail + `AUTH_USER_MODEL` |
| 1.3.x | `base_public.html`, `base.html` e partials do design system |
| 1.4.x | Landing page, cadastro, login e logout |

Depois: Sprint 2 (perfil, descontos, contas, categorias) → Sprint 3 (transações, caixinhas, motor de cálculo) → Sprint 4 (eventos, investimentos) → Sprint 5 (dashboard, lembretes) → Sprint 6 (PEP8, testes, Docker).

## Divergências entre o que está definido e o que está no disco

| Tema | Definido (PRD/TASKS) | Real hoje |
| :--- | :--- | :--- |
| Versão do Django | Django 5.x | **6.1.2** instalado |
| Banco | PostgreSQL 16+ | **SQLite** (`db.sqlite3`) |
| Ambiente virtual | `.venv` | **`venv/`** |
| Idioma/timezone | `pt-br` / `America/Sao_Paulo` | `en-us` / `UTC` |
| Usuário | `CustomUser` por e-mail | `auth.User` padrão |
| Templates/statics | `templates/` + `static/` | não existem |

As duas primeiras divergências são resolvidas pelas próprias tarefas do backlog (1.1.3 e 1.1.4). A versão 6.1.2 do Django foi a instalada no ambiente — se o time precisar fixar 5.x, é uma decisão a registrar antes de escrever código dependente de API.

## Riscos ativos já mapeados no PRD

| ID | Risco | Mitigação definida |
| :--- | :--- | :--- |
| R01 | Rate limit / indisponibilidade das APIs de cotação (`brapi.dev`, `yfinance`) | Guardar última cotação válida e permitir edição manual de `current_price` |
| R02 | Usuário lançar a fatura e esquecer de marcar o gasto como "no cartão" | Toggle explícito "Pago no cartão de crédito?" com texto explicativo |
| R03 | Complexidade do OAuth2 do Google Calendar em ambiente local | Lembretes funcionam 100% por cadastro manual; conector desacoplado |
| R04 | Soma das alocações percentuais passar de 100% | Validação no `clean()` do model/form |
