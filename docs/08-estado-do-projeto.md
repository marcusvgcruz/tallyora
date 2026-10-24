# 08 — Estado do Projeto

Retrato do que existe em disco hoje (24/10/2026), verificado no código e no banco. O backlog completo e atualizado está em `../TASKS.md`.

**Backlog concluído: Sprints 1 a 6 fechadas.** A Sprint 6 entregou PEP8 sem avisos (`flake8` 0), **124 testes automatizados** verdes em SQLite e em PostgreSQL, revisão de pt-BR nos 38 templates e a aplicação dockerizada (`web` + `db`). O `TASKS.md` não tem nenhum item em aberto.

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
| `EventPlan` (4.1.1) | evento com data, já guardado, aporte mensal percentual ou fixo, vínculo opcional com caixinha e `is_active` |
| `EventExpenseItem` (4.1.2) | fornecedor do evento com custo, pago, status **derivado** e `remaining_amount` |
| Aportes de eventos no motor (4.1.3) | `FinancialCalculationService` abate os eventos ativos depois das caixinhas e devolve `event_plans` com o detalhe |
| CRUD de eventos (4.1.4) | lista, criação, edição, detalhe, exclusão e CRUD de fornecedores — 8 CBVs filtradas por usuário |
| Tela do evento (4.1.5) | 5 cards (Custo Total, Já Pago, Falta Pagar, Já Guardado, Falta Guardar), barra de progresso e tabela de fornecedores com totais |
| `AssetAllocationTarget` (4.2.1) | meta por classe com `UniqueConstraint(user, asset_class)` e bloqueio da soma acima de 100% |
| `InvestmentAsset` (4.2.2 / 4.2.3) | ativo com quantidade, preço médio/atual, `last_quote_update` e properties de valor investido, valor atual e lucro/prejuízo (R$ e %) |
| `QuoteUpdaterService` (4.2.4) | cotações pela **API oficial da B3** (sem chave), com brapi.dev (token opcional) e Yahoo como fallbacks; falha nunca sobrescreve o preço anterior |
| Portfólio (4.2.5 / 4.2.6) | KPIs, gráfico de rosca atual vs meta, formset de metas, tabelas por classe com badge Aportar/Aguardar e botão de atualizar cotações |
| Motor de cálculo (3.3.1 a 3.3.4) | `transactions/services.py`: `Period` + `FinancialCalculationService.summary()` — receita, gastos na conta, fatura sem duplicidade, investimentos, caixinhas e **saldo livre** |
| Regra da fatura (3.3.3) | se existe lançamento `CREDIT_CARD_BILL` no período, ele é a fatura; os itens de cartão não são somados de novo |
| Telas (3.1.4 / 3.2.3) | transações com filtro e KPIs, despesas fixas, caixinhas com barra de progresso |
| Sidebar | todos os links ativos: Perfil, Contas & Cartões, Categorias, Transações & Fatura, Caixinhas & Eventos, Investimentos e Lembretes do Dia |
| Design system | `base.html`/`base_public.html` + partials (`_card_kpi`, `_empty_state`, `_modal_confirm_delete`, `_form_field`) |
| Tailwind compilado | `django-tailwind` + CLI standalone; `manage.py tailwind build` → `theme/static/css/dist/styles.css` (versionado, sem CDN) |
| Isolamento de dados (RNF08) | `get_queryset()` filtrado por `request.user`; objeto de outro usuário devolve 404 |
| Dashboard (5.2.1 / 5.2.2) | `DashboardView` consome `summary()` e monta o contexto; tela com seletor de período, 4 KPIs + Saldo Livre em destaque, rosca Chart.js local com legenda server-side, painel de lembretes do dia, resumo de caixinhas e eventos, patrimônio e estado vazio |
| `DailyReminder` (5.1.1) | lembrete com `scheduled_time`, `reminder_date` e `external_google_event_id`; **sem estado de concluído**; unicidade por dia/horário/título |
| CRUD de lembretes (5.1.2) | lista (hoje + próximos dias), criação e exclusão, tudo filtrado por usuário, sem nenhuma ação de "marcar como feito" |
| `GoogleCalendarSyncService` (5.1.3) | leitura opcional via OAuth2 refresh token (Calendar API v3, só `urllib`), `todays_events()` e `sync_today()` com espelho em `DailyReminder`; sem credencial degrada para lista vazia |
| Testes automatizados (6.2.1 a 6.2.3) | **124 testes** em `tests.py` de 9 apps: usuários/perfis (53), transações (28), eventos e investimentos (23), contas/categorias/lembretes (20). Rode com `APP_ENV=dev python manage.py test` |
| Qualidade de código (6.1.1) | `black` (linha 79, aspas simples preservadas) + `flake8` com **0 avisos**; configs em `setup.cfg` e `pyproject.toml`; 6 models que estavam sem registro ganharam admin |
| pt-BR na interface (6.1.2) | 38 templates revisados; `locale/pt_BR/` traduz o rótulo vazio dos selects (`- Selecione uma opção -`), único texto em inglês que sobrava |
| Docker (6.3.1 / 6.3.2) | `Dockerfile` (`python:3.12-slim`, não-root, healthcheck) + `docker-compose.yml` (`web` + `postgres:16-alpine`, volume `pgdata`, `pg_isready`, migração automática, `WEB_PORT`) |
| Documentação de execução (6.3.3) | `README.md` com os dois caminhos (SQLite sem Docker e Compose), provados rodando |
| `.gitignore` + `.env.example` | excluem `venv/`, `__pycache__/`, `db.sqlite3`, `.env`, `staticfiles/` e `node_modules/`; CSS compilado é versionado |
| Repositório publicado | `main` → https://github.com/marcusvgcruz/tallyora (público) |

## Não implementado

- **A integração com o Google Calendar nunca foi exercitada contra a API real** — não há credencial nesta VPS. Tudo (token, eventos, 401/403, JSON inválido) foi validado com `urlopen` mockado.
- Não existe tela para disparar `sync_today()`: o serviço está pronto e testado, mas o gatilho (botão ou cron) não foi pedido por nenhuma sub-tarefa.
- Cripto não tem cotação automática (só renda fixa manual e renda variável pela B3); a classe entra em `skipped` com motivo "cotação manual".
- O peso por ativo (`target_percentage_in_class`) é guardado e exibido, mas ainda não compara com o real — o badge é por classe, não por ativo.
- Sem recuperação de senha, onboarding em `/profile/setup/` e verificação de e-mail.
- Sem paginação ou busca nas listagens.
- **O container roda `runserver`**, não um servidor de produção: `gunicorn` não está nas dependências e entrar com ele é decisão de deploy (o `STATIC_ROOT` já existe para o `collectstatic`).
- `docker compose` usa a porta 8080 do host por padrão; na VPS ela é do `evolution_api`, então lá é `WEB_PORT=8081 docker compose up -d`.
- **Duas regras de negócio ficaram registradas como frágeis** (comportamento real, sem correção porque não estavam no backlog): fatura consolidada é autoritativa mesmo quando menor que a soma dos itens (subestima a dívida se o valor for digitado errado) e `PayrollDeduction.amount` aceita valor negativo no banco (só o form barra).

## Próximos passos (fora do backlog atual)

| Tema | O que falta |
| :--- | :--- |
| Disparo da agenda | botão ou cron chamando `GoogleCalendarSyncService.sync_today()` |
| Cotações | cripto (CoinGecko responde sem chave) e comparação do peso por **ativo**, não só por classe |
| Deploy real | `gunicorn`/`uvicorn` + `collectstatic` servido por nginx, HTTPS e backup do Postgres |
| Conta | recuperação de senha, verificação de e-mail e onboarding |
| Listagens | paginação e busca onde a lista crescer |

## Divergências entre o que está definido e o que está no disco

| Tema | Definido (PRD/TASKS) | Real hoje |
| :--- | :--- | :--- |
| Versão do Django | Django 5.x | **6.1.2** instalado |
| Ambiente virtual | `.venv` | **`venv/`** |
| Rotas raiz | `core/urls.py` como `ROOT_URLCONF` | `core/root_urls.py` é o root (necessário para o namespace `core:` existir); `core/urls.py` é a URLconf da app |
| Prefixo das rotas de dados | não definido | `/perfil/`, `/contas/`, `/categorias/`, `/transacoes/`, `/caixinhas/` — com `path('', include(...))` os `name='list'`/`name='profile'` colidiriam entre apps e com a landing em `/` |
| Onboarding | `/profile/setup/` no PRD | edição direta em `/perfil/` (onboarding não é tarefa do backlog) |
| Dashboard | RF16 completo | entregue na Sprint 5 (5.2.1 / 5.2.2) |
| Tailwind | "CDN configurada ou CLI standalone" | CLI standalone via `django-tailwind` (build local, sem CDN) |
| Exclusão de desconto de folha | "exclusão sempre com confirmação" | `confirm()` + POST na própria página de perfil (as listas usam página de confirmação) |
| Despesa fixa e quinzenas | TASKS só define `billing_cycle` | além do ciclo, o `due_day` decide a quinzena — sem isso a despesa `MONTHLY` desaparecia das visões de quinzena (ver `docs/05`, §1.1) |
| Fonte das cotações (4.2.4) | brapi.dev (ou yfinance) | **API oficial da B3** como primária, porque brapi exige token (401 sem ele) e o Yahoo devolve 429 para o IP da VPS; brapi (com `BRAPI_TOKEN`) e Yahoo ficam como fallback |
| Metas por classe | "a soma deve validar exatamente 100%" | bloqueio quando **passa** de 100% e aviso na tela com quanto falta — exigir 100% a cada linha impediria cadastrar uma classe por vez |
| Nomes de properties (6.2.3) | `invested_value` / `profit_loss` | no código são `total_invested` / `profit_loss_amount` (os testes cobrem os nomes reais) |
| Custo do evento (6.2.3) | "custo do evento" como campo | não existe campo: `total_cost` e `remaining_to_pay` vêm da soma dos fornecedores, então `saved_percentage` usa `custo − pago` como denominador |
| Pagamento acima do custo (6.2.3) | "pago maior que o custo barrado" | `save()` grava e satura `remaining_amount` em 0; a rejeição só acontece em `full_clean()`/form |
| Banco | PostgreSQL no PRD | `APP_ENV=dev` usa SQLite e `APP_ENV=prd` usa PostgreSQL, para rodar local sem instalar banco |
| Caixinhas sequenciais | RF11 não define a ordem | abatimento em sequência alfabética sobre o que sobra, para a soma nunca passar do disponível |

Resolvidas nas Sprints 1 a 3: banco PostgreSQL, idioma/timezone pt-BR, usuário customizado, existência de `templates/`, Tailwind local, perfil/contas/categorias, transações/despesas fixas, caixinhas e motor de cálculo.

Resolvidas nas Sprints 4 a 6: eventos e carteira, dashboard, lembretes, cotações pela B3, testes automatizados, PEP8 e Docker.

## Riscos ativos já mapeados no PRD

| ID | Risco | Mitigação definida |
| :--- | :--- | :--- |
| R01 | Rate limit / indisponibilidade das APIs de cotação (`brapi.dev`, `yfinance`) | Guardar última cotação válida e permitir edição manual de `current_price` |
| R02 | Usuário lançar a fatura e esquecer de marcar o gasto como "no cartão" | Toggle explícito "Este gasto está na fatura do cartão de crédito?" com texto explicativo na tela |
| R03 | Complexidade do OAuth2 do Google Calendar em ambiente local | Lembretes funcionam 100% por cadastro manual; conector desacoplado |
| R04 | Soma das alocações percentuais passar de 100% | Validação no `clean()` do model/form |
