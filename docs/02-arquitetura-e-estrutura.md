# 02 — Arquitetura e Estrutura

## Stack atual (verificada no ambiente)

| Item | Versão / estado real |
| :--- | :--- |
| Python | 3.12.3 (`venv/bin/python`) |
| Django | 6.1.2 |
| PostgreSQL | 16.15 (instalado na VPS, serviço `postgresql` ativo e habilitado) |
| psycopg2-binary | 2.9.13 (driver em uso) |
| python-dotenv | 1.2.4 (`core/settings.py` carrega o `.env`) |
| Banco de dados | PostgreSQL, database `tallyora`, role `tallyora` em `127.0.0.1:5432` |
| Frontend | DTL + TailwindCSS 4 compilado localmente (`django-tailwind` 4.6.0 + CLI standalone v4.3.3); Chart.js ainda pendente |

> O PRD cita "Django 5.x". O instalado é **Django 6.1.2** — decisão pendente de registro. A migração para PostgreSQL já foi feita (tarefa 1.1.3). Ver `08-estado-do-projeto.md`.

## Estrutura de diretórios real

```text
tallyora/
├── manage.py
├── requirements.txt
├── .env                    # credenciais locais (NÃO versionado)
├── .env.example            # template versionado
├── PRD.md
├── TASKS.md
├── docs/                   # esta documentação
├── templates/              # DTL: bases, partials e telas
│   ├── base.html           # área autenticada (sidebar + conteúdo)
│   ├── base_public.html    # área pública (landing, login, cadastro)
│   ├── core/               # landing.html, dashboard.html
│   ├── users/              # login.html, register.html
│   ├── profiles/           # profile_detail.html (perfil + descontos)
│   ├── accounts/           # account_list, account_form, account_confirm_delete
│   ├── categories/         # category_list, category_form, category_confirm_delete
│   ├── transactions/       # transaction_list|form|confirm_delete, recurring_*
│   ├── goals_events/       # goalbox_list|form|confirm_delete
│   └── partials/           # _card_kpi, _empty_state, _modal_confirm_delete, _form_field
├── theme/                  # app do django-tailwind: fonte (static_src) e CSS compilado
│   └── static/css/dist/styles.css   # saída do build (versionada)
├── venv/                   # ambiente virtual Python 3.12.3
├── core/                   # projeto Django: settings, root_urls, urls, views, models (BaseModel)
├── users/                  # CustomUser, forms, views, urls, admin, migração inicial
├── profiles/               # app de perfil financeiro
├── accounts/               # app de contas e cartões
├── categories/             # app de categorias
├── transactions/           # app de transações, despesas fixas e motor de cálculo
├── goals_events/           # app de caixinhas (eventos entram na Sprint 4)
├── investments/            # app de carteira
└── reminders/              # app de lembretes
```

`static/` ainda **não existe**. O CSS vem do app `theme/` (`django-tailwind`), compilado para `theme/static/css/dist/styles.css` com `python manage.py tailwind build`. `STATICFILES_DIRS` só é populado se a pasta `static/` existir.

## Camadas e responsabilidades

| Camada | Arquivo | Regra |
| :--- | :--- | :--- |
| Configuração | `core/settings.py` | Única fonte de configuração; lê o `.env` via `python-dotenv` |
| Rotas raiz | `core/root_urls.py` | `ROOT_URLCONF`: publica `admin/` e inclui as URLconfs das apps com prefixo (`perfil/`, `contas/`, `categorias/`, `transacoes/`, `caixinhas/`) |
| Rotas de app | `<app>/urls.py` | Arquivo por app com `app_name`; rotas nomeadas (`core:dashboard`, `core:landing`) |
| Regras de dados | `<app>/models.py` | Todo model herda de `BaseModel`; campos em inglês |
| Entrada de dados | `<app>/forms.py` | `ModelForm`/`Form` com validação em `clean()` e widgets estilizados via Tailwind |
| Interface | `<app>/views.py` | Class-Based Views com `LoginRequiredMixin`, `get_queryset()` filtrado por usuário |
| Cálculo | `transactions/services.py`, `investments/services.py`, `reminders/services.py` | Regra de negócio fora das views (ver `05-regras-de-negocio-financeiras.md`) |
| Efeitos colaterais | `<app>/signals.py` | Registrados no `ready()` do `apps.py` |
| Templates | `templates/` | DTL, herdam de `base.html` (área logada) ou `base_public.html` (pública) |

> **Por que existe `core/root_urls.py`:** o namespace `core:` é criado pelo `include('core.urls')`. Colocar `app_name` direto no `ROOT_URLCONF` **não** registra namespace (verificado na prática: resulta em `NoReverseMatch`). Por isso o root é um arquivo separado e `core/urls.py` continua sendo a URLconf da app.


`signals.py` existe em `profiles/` (cria o `UserProfile`) e `categories/` (categorias padrão). `services.py` existe em `transactions/` (motor de cálculo da Sprint 3) e é a convenção para `investments/` (4.2.4) e `reminders/` (5.1.3).

## Configuração atual do `core/settings.py`

Valores presentes hoje no arquivo:

- `INSTALLED_APPS`: apps padrão do Django + `tailwind` + `theme` + as 8 apps do projeto.
- `TAILWIND_APP_NAME = 'theme'`, `INTERNAL_IPS = ['127.0.0.1']`, `NPM_BIN_PATH` do env (o build usa o CLI standalone, não precisa de Node).
- `load_dotenv(BASE_DIR / '.env')` no topo: toda configuração sensível vem do ambiente.
- `SECRET_KEY` obrigatória — se faltar no `.env`, o projeto não sobe (`ImproperlyConfigured`).
- `DEBUG` e `ALLOWED_HOSTS` parseados do `.env` por helpers `env_bool()` e `env_list()`.
- `DATABASES`: PostgreSQL (`django.db.backends.postgresql`) com `NAME`, `USER`, `PASSWORD`, `HOST` e `PORT` vindos do `.env`.
- `AUTH_USER_MODEL = 'users.CustomUser'`.
- `LOGIN_URL = 'users:login'`, `LOGIN_REDIRECT_URL = 'core:dashboard'`, `LOGOUT_REDIRECT_URL = 'core:landing'`.
- `LANGUAGE_CODE = 'pt-br'`, `TIME_ZONE = 'America/Sao_Paulo'`, `USE_I18N = True`, `USE_TZ = True`.
- `TEMPLATES['DIRS'] = [BASE_DIR / 'templates']`, com `APP_DIRS = True`.
- `STATICFILES_DIRS` só é populado quando a pasta `static/` existe.
- `MAILERS`: backend de e-mail no console (permite testar recuperação de senha sem SMTP).
- `DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'`.

## Rotas publicadas

| Rota | Nome | View | Acesso |
| :--- | :--- | :--- | :--- |
| `/` | `core:landing` | `LandingPageView` (redireciona logado para o dashboard) | público |
| `/register/` | `users:register` | `UserRegisterView` | público |
| `/login/` | `users:login` | `UserLoginView` | público |
| `/logout/` | `users:logout` | `UserLogoutView` | **somente POST** |
| `/dashboard/` | `core:dashboard` | `DashboardView` (provisória, dados na Sprint 5) | autenticado |
| `/admin/` | — | Django admin | staff |
| `/perfil/` | `profiles:profile` | `ProfileConfigView` (exibe e edita o perfil) | autenticado |
| `/perfil/descontos/novo/` | `profiles:deduction_create` | `PayrollDeductionCreateView` | autenticado (**POST**) |
| `/perfil/descontos/<pk>/excluir/` | `profiles:deduction_delete` | `PayrollDeductionDeleteView` | autenticado (**POST**) |
| `/contas/` | `accounts:list` | `AccountListView` | autenticado |
| `/contas/novo/` | `accounts:create` | `AccountCreateView` | autenticado |
| `/contas/<pk>/editar/` | `accounts:update` | `AccountUpdateView` | autenticado |
| `/contas/<pk>/excluir/` | `accounts:delete` | `AccountDeleteView` | autenticado (**POST**) |
| `/categorias/` | `categories:list` | `CategoryListView` | autenticado |
| `/categorias/nova/` | `categories:create` | `CategoryCreateView` | autenticado |
| `/categorias/<pk>/editar/` | `categories:update` | `CategoryUpdateView` | autenticado |
| `/categorias/<pk>/excluir/` | `categories:delete` | `CategoryDeleteView` | autenticado (**POST**) |
| `/transacoes/` | `transactions:list` | `TransactionListView` (filtros `mes`, `ano`, `periodo`) | autenticado |
| `/transacoes/nova/` | `transactions:create` | `TransactionCreateView` | autenticado |
| `/transacoes/<pk>/editar/` | `transactions:update` | `TransactionUpdateView` | autenticado |
| `/transacoes/<pk>/excluir/` | `transactions:delete` | `TransactionDeleteView` | autenticado (**POST**) |
| `/transacoes/fixas/` | `transactions:recurring_list` | `RecurringExpenseListView` | autenticado |
| `/transacoes/fixas/nova/` | `transactions:recurring_create` | `RecurringExpenseCreateView` | autenticado |
| `/transacoes/fixas/<pk>/editar/` | `transactions:recurring_update` | `RecurringExpenseUpdateView` | autenticado |
| `/transacoes/fixas/<pk>/excluir/` | `transactions:recurring_delete` | `RecurringExpenseDeleteView` | autenticado (**POST**) |
| `/caixinhas/` | `goals:list` | `GoalBoxListView` | autenticado |
| `/caixinhas/nova/` | `goals:create` | `GoalBoxCreateView` | autenticado |
| `/caixinhas/<pk>/editar/` | `goals:update` | `GoalBoxUpdateView` | autenticado |
| `/caixinhas/<pk>/excluir/` | `goals:delete` | `GoalBoxDeleteView` | autenticado (**POST**) |

`Todo `.py` de dados (contas, categorias, descontos, transações, despesas fixas e caixinhas) usa `get_queryset()` filtrado por `request.user` — objeto de outro usuário devolve **404**, não 403 (RNF08).

Ainda **não existem**: `/investments/`, `/events/`, `/reminders/` — são das sprints 4 e 5. O PRD cita `/profile/setup/` como onboarding; o projeto expõe a edição do perfil em `/perfil/` (o onboarding não é tarefa do backlog).


## O que não usar

Decisão explícita do PRD (RNF01): nada de microserviços, SPA separada, Celery, Redis. A aplicação é um monólito Django com DTL.
