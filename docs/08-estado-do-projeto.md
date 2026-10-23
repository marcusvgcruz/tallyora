# 08 — Estado do Projeto

Retrato do que existe em disco hoje (23/10/2026), verificado no código e no banco. O backlog completo e atualizado está em `../TASKS.md`.

**Sprints 1 e 2 concluídas.** Na Sprint 2 foram fechadas as sub-tarefas 2.1.1 a 2.1.6, 2.2.1 a 2.2.4 e 2.3.1 a 2.3.3.

## Implementado

| Item | Evidência |
| :--- | :--- |
| Ambiente virtual Python 3.12.3 | `venv/` com Django 6.1.2 e dependências instaladas |
| `requirements.txt` com dependências fixadas | Django, psycopg2-binary, python-dotenv, django-tailwind, pytailwindcss, asgiref, sqlparse |
| PostgreSQL 16.15 provisionado | serviço `postgresql` ativo/habilitado; database e role `tallyora`; migrações aplicadas |
| Configuração por ambiente | `core/settings.py` carrega `.env` com `python-dotenv`; `SECRET_KEY` obrigatória; `DEBUG`/`ALLOWED_HOSTS` tipados |
| Localização | `LANGUAGE_CODE = 'pt-br'`, `TIME_ZONE = 'America/Sao_Paulo'`, I18N e TZ ativos |
| `BaseModel` abstrato | `core/models.py` com `created_at`/`updated_at`, herdado por todos os models |
| `CustomUser` por e-mail | `CustomUserManager`, `username = None`, `email` único, `USERNAME_FIELD = 'email'`, admin próprio |
| Autenticação | cadastro (`/register/`), login por e-mail (`/login/`), logout POST (`/logout/`) funcionando ponta a ponta |
| `UserProfile` (2.1.1) | 1:1 com o usuário (`related_name='profile'`), regime CLT/PJ, periodicidade, bruto, `advance_percentage`, alocação de investimentos |
| `PayrollDeduction` (2.1.2) | descontos fixos de folha com `is_active` |
| Signals (2.1.3 / 2.3.2) | `post_save` no `CustomUser` cria o `UserProfile` e as 8 categorias padrão (2 receitas, 6 despesas) |
| Forms (2.1.4 / 2.2.2) | `UserProfileForm` (percentuais 0–100), `PayrollDeductionForm`, `BankAccountForm` (fechamento/vencimento 1–31 só com cartão), `CategoryForm` (hex + duplicidade) |
| CRUDs (2.1.5 / 2.2.3 / 2.3.3) | perfil + descontos, contas/cartões e categorias, todos com `LoginRequiredMixin` e filtro por usuário |
| Telas (2.1.6 / 2.2.4 / 2.3.3) | perfil com resumo salarial, listas/formulários/confirmações de contas e de categorias |
| Sidebar | links reais para Perfil, Contas & Cartões e Categorias; itens futuros seguem "em breve" |
| Design system | `base.html`/`base_public.html` + partials (`_card_kpi`, `_empty_state`, `_modal_confirm_delete`, `_form_field`) |
| Tailwind compilado | `django-tailwind` + CLI standalone; `manage.py tailwind build` → `theme/static/css/dist/styles.css` (versionado, sem CDN) |
| Isolamento de dados (RNF08) | `get_queryset()` filtrado por `request.user`; objeto de outro usuário devolve 404 |
| Dashboard provisório | `DashboardView` + `templates/core/dashboard.html` (KPIs vazios + aviso de que os dados entram na Sprint 5) |
| `.gitignore` + `.env.example` | excluem `venv/`, `__pycache__/`, `db.sqlite3`, `.env` e `node_modules/`; CSS compilado é versionado |
| Repositório publicado | `main` → https://github.com/marcusvgcruz/tallyora (público) |

## Não implementado

- `transactions`, `goals_events`, `investments` e `reminders` continuam com `models.py`, `views.py`, `admin.py` e `tests.py` vazios.
- Sem `services.py` (motor de cálculo) — as properties do `UserProfile` cobrem apenas o salário.
- Sem Chart.js, sem dashboard real e sem lembretes.
- Sem recuperação de senha, onboarding em `/profile/setup/` e verificação de e-mail.
- Sem Docker e sem suíte de testes automatizados (as verificações são scripts de smoke com rollback, não `tests.py`).
- Sem paginação ou busca nas listagens de contas e categorias.

## Próximos passos (Sprint 3)

| Bloco | O que entrega |
| :--- | :--- |
| 3.1.x | `RecurringExpense` (despesas fixas com dia de vencimento e ciclo de fatura) |
| 3.2.x | `Transaction` (receita/despesa/fatura) com `is_on_credit_card` e `is_paid` |
| 3.3.x | `FinancialCalculationService` — receita do período, gastos, fatura e saldo livre |
| 3.4.x | `GoalBox` (caixinhas) com alocação percentual/fixa |

Depois: Sprint 4 (eventos, investimentos) → Sprint 5 (dashboard, lembretes) → Sprint 6 (PEP8, testes, Docker).

## Divergências entre o que está definido e o que está no disco

| Tema | Definido (PRD/TASKS) | Real hoje |
| :--- | :--- | :--- |
| Versão do Django | Django 5.x | **6.1.2** instalado |
| Ambiente virtual | `.venv` | **`venv/`** |
| Rotas raiz | `core/urls.py` como `ROOT_URLCONF` | `core/root_urls.py` é o root (necessário para o namespace `core:` existir); `core/urls.py` é a URLconf da app |
| Prefixo das rotas de perfil/conta/categoria | não definido | `/perfil/`, `/contas/`, `/categorias/` — com `path('', include(...))` os `name='profile'`/`name='list'` colidiriam entre apps e com a landing em `/` |
| Onboarding | `/profile/setup/` no PRD | edição direta em `/perfil/` (onboarding não é tarefa do backlog) |
| Dashboard | RF16 completo na Sprint 5 | tela provisória, só com aviso e KPIs vazios |
| Tailwind | "CDN configurada ou CLI standalone" | CLI standalone via `django-tailwind` (build local, sem CDN) |
| Exclusão de desconto de folha | "exclusão sempre com confirmação" | `confirm()` + POST na própria página de perfil (contas e categorias usam página de confirmação) |

Resolvidas nas Sprints 1 e 2: banco PostgreSQL, idioma/timezone pt-BR, usuário customizado, existência de `templates/`, Tailwind local, perfil/contas/categorias.

## Riscos ativos já mapeados no PRD

| ID | Risco | Mitigação definida |
| :--- | :--- | :--- |
| R01 | Rate limit / indisponibilidade das APIs de cotação (`brapi.dev`, `yfinance`) | Guardar última cotação válida e permitir edição manual de `current_price` |
| R02 | Usuário lançar a fatura e esquecer de marcar o gasto como "no cartão" | Toggle explícito "Pago no cartão de crédito?" com texto explicativo |
| R03 | Complexidade do OAuth2 do Google Calendar em ambiente local | Lembretes funcionam 100% por cadastro manual; conector desacoplado |
| R04 | Soma das alocações percentuais passar de 100% | Validação no `clean()` do model/form |
