# 08 — Estado do Projeto

Retrato do que existe em disco hoje (23/10/2026), verificado diretamente no código. O backlog completo e atualizado está em `../TASKS.md`.

**Sprint 1 concluída.** Tarefas marcadas no backlog: 1.1.1 a 1.1.5, 1.2.1 a 1.2.4, 1.3.1 a 1.3.3 e 1.4.1 a 1.4.3.

## Implementado

| Item | Evidência |
| :--- | :--- |
| Ambiente virtual Python 3.12.3 | `venv/` com Django 6.1.2 e dependências instaladas |
| `requirements.txt` com 5 dependências fixadas | Django, psycopg2-binary, python-dotenv, asgiref, sqlparse |
| PostgreSQL 16.15 provisionado | serviço `postgresql` ativo/habilitado; database e role `tallyora`; migrações aplicadas |
| Configuração por ambiente | `core/settings.py` carrega `.env` com `python-dotenv`; `SECRET_KEY` obrigatória; `DEBUG`/`ALLOWED_HOSTS` tipados |
| Localização | `LANGUAGE_CODE = 'pt-br'`, `TIME_ZONE = 'America/Sao_Paulo'`, I18N e TZ ativos |
| `BaseModel` abstrato | `core/models.py` com `created_at`/`updated_at`; já herdado pelo `CustomUser` (verificado em registro criado) |
| `CustomUser` por e-mail | `users/models.py` com `CustomUserManager` (`create_user`/`create_superuser`), `username = None`, `email` único e `USERNAME_FIELD = 'email'` |
| `AUTH_USER_MODEL` + migração | `users.0001_initial` gerada e aplicada; tabela `users_customuser` no Postgres |
| Admin do usuário | `CustomUserAdmin` com lista, busca e formulários próprios (sem campo `username`) |
| Design system | `templates/base_public.html`, `templates/base.html` (sidebar, topbar, mensagens, menu mobile) |
| Componentes parciais | `templates/partials/_card_kpi.html`, `_empty_state.html`, `_modal_confirm_delete.html` |
| Landing page | `LandingPageView` + `templates/core/landing.html` com os 4 pilares e CTAs |
| Autenticação | cadastro (`/register/`), login por e-mail (`/login/`), logout POST (`/logout/`); `LOGIN_REDIRECT_URL = 'core:dashboard'` |
| Dashboard provisório | `DashboardView` + `templates/core/dashboard.html` (KPIs vazios + aviso de que os dados entram na Sprint 5) |
| `.gitignore` + `.env.example` | excluem `venv/`, `__pycache__/`, `db.sqlite3` e `.env` |
| Repositório publicado | `main` → https://github.com/marcusvgcruz/tallyora (público) |

## Não implementado

- Nenhum model de domínio além do `CustomUser`: `profiles`, `accounts`, `categories`, `transactions`, `goals_events`, `investments` e `reminders` continuam com `models.py`, `views.py`, `admin.py` e `tests.py` vazios.
- Sem `signals.py`, `services.py`, `urls.py` por app (só `users` tem) e sem motor de cálculo.
- Sem `static/` (Tailwind via CDN) e sem Chart.js.
- Sem recuperação de senha, onboarding de perfil e verificação de e-mail.
- Sem Docker, sem suíte de testes automatizados (as verificações da Sprint 1 foram feitas por script de smoke, não por `tests.py`).

## Próximos passos (Sprint 2)

| Tarefa | O que entrega |
| :--- | :--- |
| 2.1.x | `UserProfile` (CLT/PJ, periodicidade, alocação), `PayrollDeduction`, signal de criação automática, tela de perfil |
| 2.2.x | `BankAccount` (contas e cartões) com CRUD |
| 2.3.x | `Category` com categorias padrão por signal e CRUD |

Depois: Sprint 3 (transações, caixinhas, motor de cálculo) → Sprint 4 (eventos, investimentos) → Sprint 5 (dashboard, lembretes) → Sprint 6 (PEP8, testes, Docker).

## Divergências entre o que está definido e o que está no disco

| Tema | Definido (PRD/TASKS) | Real hoje |
| :--- | :--- | :--- |
| Versão do Django | Django 5.x | **6.1.2** instalado |
| Ambiente virtual | `.venv` | **`venv/`** |
| Rotas raiz | `core/urls.py` como `ROOT_URLCONF` | `core/root_urls.py` é o root (necessário para o namespace `core:` existir); `core/urls.py` é a URLconf da app |
| Dashboard | RF16 completo na Sprint 5 | tela provisória, só com aviso e KPIs vazios |

Resolvidas na Sprint 1: banco PostgreSQL, idioma/timezone pt-BR, usuário customizado e existência de `templates/`.

## Riscos ativos já mapeados no PRD

| ID | Risco | Mitigação definida |
| :--- | :--- | :--- |
| R01 | Rate limit / indisponibilidade das APIs de cotação (`brapi.dev`, `yfinance`) | Guardar última cotação válida e permitir edição manual de `current_price` |
| R02 | Usuário lançar a fatura e esquecer de marcar o gasto como "no cartão" | Toggle explícito "Pago no cartão de crédito?" com texto explicativo |
| R03 | Complexidade do OAuth2 do Google Calendar em ambiente local | Lembretes funcionam 100% por cadastro manual; conector desacoplado |
| R04 | Soma das alocações percentuais passar de 100% | Validação no `clean()` do model/form |
