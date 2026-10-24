# 08 — Estado do Projeto

Retrato do que existe em disco hoje (24/10/2026), verificado no código e no banco. O backlog completo e atualizado está em `../TASKS.md`.

**Sprints 1, 2 e 3 concluídas.** Na Sprint 3 foram fechadas as sub-tarefas 3.1.1 a 3.1.4, 3.2.1 a 3.2.3 e 3.3.1 a 3.3.4.

## Implementado

| Item | Evidência |
| :--- | :--- |
| Ambiente virtual Python 3.12.3 | `venv/` com Django 6.1.2 e dependências instaladas |
| `requirements.txt` com dependências fixadas | Django, psycopg2-binary, python-dotenv, django-tailwind, pytailwindcss, asgiref, sqlparse |
| PostgreSQL 16.15 provisionado | serviço `postgresql` ativo/habilitado; database e role `tallyora`; migrações aplicadas |
| Configuração por ambiente | `core/settings.py` carrega `.env` com `python-dotenv`; `SECRET_KEY` obrigatória; `DEBUG`/`ALLOWED_HOSTS` tipados |
| Localização | `LANGUAGE_CODE = 'pt-br'`, `TIME_ZONE = 'America/Sao_Paulo'`, I18N e TZ ativos |
| `BaseModel` abstrato | `core/models.py` com `created_at`/`updated_at`, herdado por todos os models; helpers `to_money`/`ZERO`/`MONEY_PLACES` no mesmo módulo |
| `CustomUser` por e-mail | `CustomUserManager`, `username = None`, `email` único, `USERNAME_FIELD = 'email'`, admin próprio |
| Autenticação | cadastro (`/register/`), login por e-mail (`/login/`), logout POST (`/logout/`) funcionando ponta a ponta |
| `UserProfile` (2.1.1) | 1:1 com o usuário (`related_name='profile'`), regime CLT/PJ, periodicidade, bruto, `advance_percentage`, alocação de investimentos |
| `PayrollDeduction` (2.1.2) | descontos fixos de folha com `is_active` |
| Signals (2.1.3 / 2.3.2) | `post_save` no `CustomUser` cria o `UserProfile` e as 8 categorias padrão (2 receitas, 6 despesas) |
| Forms | `UserProfileForm`, `PayrollDeductionForm`, `BankAccountForm`, `CategoryForm`, `TransactionForm`, `RecurringExpenseForm`, `GoalBoxForm` — todos com widgets Tailwind e validação em `clean()` |
| CRUDs (2.x e 3.x) | perfil + descontos, contas/cartões, categorias, transações, despesas fixas e caixinhas — `LoginRequiredMixin` e filtro por usuário |
| `RecurringExpense` (3.1.1) | despesa fixa com `due_day`, `billing_cycle` (quinzena 1/2 ou mensal), `is_on_credit_card`, `is_active` |
| `Transaction` (3.1.2) | receita/despesa/fatura do cartão, `reference_date`, `is_on_credit_card`, `is_paid` |
| Filtros de período (3.1.4) | `transactions:list` aceita `mes`, `ano` e `periodo` (`full`/`first`/`second`), com totais de receita, despesa e fatura |
| `GoalBox` (3.2.1 / 3.2.2) | caixinha com alocação percentual ou fixa, saldo, meta, `progress_percentage` e `calculate_period_contribution()` |
| Motor de cálculo (3.3.1 a 3.3.4) | `transactions/services.py`: `Period` + `FinancialCalculationService.summary()` — receita, gastos na conta, fatura sem duplicidade, investimentos, caixinhas e **saldo livre** |
| Regra da fatura (3.3.3) | se existe lançamento `CREDIT_CARD_BILL` no período, ele é a fatura; os itens de cartão não são somados de novo |
| Telas (3.1.4 / 3.2.3) | transações com filtro e KPIs, despesas fixas, caixinhas com barra de progresso |
| Sidebar | links reais para Perfil, Contas & Cartões, Categorias, Transações & Fatura e Caixinhas & Eventos; investimentos e lembretes seguem "em breve" |
| Design system | `base.html`/`base_public.html` + partials (`_card_kpi`, `_empty_state`, `_modal_confirm_delete`, `_form_field`) |
| Tailwind compilado | `django-tailwind` + CLI standalone; `manage.py tailwind build` → `theme/static/css/dist/styles.css` (versionado, sem CDN) |
| Isolamento de dados (RNF08) | `get_queryset()` filtrado por `request.user`; objeto de outro usuário devolve 404 |
| Dashboard provisório | `DashboardView` + `templates/core/dashboard.html` (KPIs vazios + aviso de que os dados entram na Sprint 5) |
| `.gitignore` + `.env.example` | excluem `venv/`, `__pycache__/`, `db.sqlite3`, `.env` e `node_modules/`; CSS compilado é versionado |
| Repositório publicado | `main` → https://github.com/marcusvgcruz/tallyora (público) |

## Não implementado

- `investments` e `reminders` continuam com `models.py`, `views.py`, `admin.py` e `tests.py` vazios; `EventPlan`/`EventExpenseItem` ainda não existem (Sprint 4).
- O aporte de eventos no motor de cálculo vale `0` até o `EventPlan` existir — o método `_event_contributions()` já está no lugar.
- O `FinancialCalculationService` não tem tela própria: o dashboard que consome `summary()` é a Sprint 5.
- Sem Chart.js, sem dashboard real e sem lembretes.
- Sem recuperação de senha, onboarding em `/profile/setup/` e verificação de e-mail.
- Sem Docker e sem suíte de testes automatizados (as verificações são scripts de smoke com rollback, não `tests.py`).
- Sem paginação ou busca nas listagens.

## Próximos passos (Sprint 4)

| Bloco | O que entrega |
| :--- | :--- |
| 4.1.x | Eventos (`EventPlan`, `EventExpenseItem`) e consolidação de custo/pago/falta |
| 4.2.x | Carteira de investimentos (`AssetAllocationTarget`, `InvestmentAsset`, cotações) |
| 4.3.x | Ligação dos aportes de eventos ao motor de cálculo e telas |

Depois: Sprint 5 (dashboard, lembretes) → Sprint 6 (PEP8, testes, Docker).

## Divergências entre o que está definido e o que está no disco

| Tema | Definido (PRD/TASKS) | Real hoje |
| :--- | :--- | :--- |
| Versão do Django | Django 5.x | **6.1.2** instalado |
| Ambiente virtual | `.venv` | **`venv/`** |
| Rotas raiz | `core/urls.py` como `ROOT_URLCONF` | `core/root_urls.py` é o root (necessário para o namespace `core:` existir); `core/urls.py` é a URLconf da app |
| Prefixo das rotas de dados | não definido | `/perfil/`, `/contas/`, `/categorias/`, `/transacoes/`, `/caixinhas/` — com `path('', include(...))` os `name='list'`/`name='profile'` colidiriam entre apps e com a landing em `/` |
| Onboarding | `/profile/setup/` no PRD | edição direta em `/perfil/` (onboarding não é tarefa do backlog) |
| Dashboard | RF16 completo na Sprint 5 | tela provisória, só com aviso e KPIs vazios |
| Tailwind | "CDN configurada ou CLI standalone" | CLI standalone via `django-tailwind` (build local, sem CDN) |
| Exclusão de desconto de folha | "exclusão sempre com confirmação" | `confirm()` + POST na própria página de perfil (as listas usam página de confirmação) |
| Despesa fixa e quinzenas | TASKS só define `billing_cycle` | além do ciclo, o `due_day` decide a quinzena — sem isso a despesa `MONTHLY` desaparecia das visões de quinzena (ver `docs/05`, §1.1) |
| Caixinhas sequenciais | RF11 não define a ordem | abatimento em sequência alfabética sobre o que sobra, para a soma nunca passar do disponível |

Resolvidas nas Sprints 1 a 3: banco PostgreSQL, idioma/timezone pt-BR, usuário customizado, existência de `templates/`, Tailwind local, perfil/contas/categorias, transações/despesas fixas, caixinhas e motor de cálculo.

## Riscos ativos já mapeados no PRD

| ID | Risco | Mitigação definida |
| :--- | :--- | :--- |
| R01 | Rate limit / indisponibilidade das APIs de cotação (`brapi.dev`, `yfinance`) | Guardar última cotação válida e permitir edição manual de `current_price` |
| R02 | Usuário lançar a fatura e esquecer de marcar o gasto como "no cartão" | Toggle explícito "Este gasto está na fatura do cartão de crédito?" com texto explicativo na tela |
| R03 | Complexidade do OAuth2 do Google Calendar em ambiente local | Lembretes funcionam 100% por cadastro manual; conector desacoplado |
| R04 | Soma das alocações percentuais passar de 100% | Validação no `clean()` do model/form |
