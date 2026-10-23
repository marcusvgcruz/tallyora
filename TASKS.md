## 13. Lista de Tarefas (Backlog Granular em Sprints)

### Sprint 1: Fundação do Projeto, Banco PostgreSQL, BaseModel, Autenticação por E-mail e Design System — [x] CONCLUÍDA
- [x] **1.1. Configuração Inicial do Projeto e PostgreSQL (`core`)**
  - [x] **1.1.1.** Criar ambiente virtual Python (`.venv`), instalar `django`, `psycopg2-binary`, `python-dotenv` e gerar `requirements.txt`.
  - [x] **1.1.2.** Inicializar o projeto Django `core` na raiz e criar as apps iniciais: `users`, `profiles`, `accounts`, `categories`, `transactions`, `goals_events`, `investments`, `reminders`.
  - [x] **1.1.3.** Remover o arquivo `db.sqlite3` e configurar a conexão exclusiva com o banco de dados **PostgreSQL** no `core/settings.py` lendo variáveis de ambiente (`.env`).
  - [x] **1.1.4.** Configurar `LANGUAGE_CODE = 'pt-br'`, `TIME_ZONE = 'America/Sao_Paulo'`, `USE_I18N = True` e `USE_TZ = True` no `core/settings.py`.
  - [x] **1.1.5.** Criar o model abstrato `BaseModel` em `core/models.py` contendo `created_at` e `updated_at` para ser herdado por todas as entidades do sistema.
- [x] **1.2. Modelo de Usuário Customizado com Login por E-mail (`users`)**
  - [x] **1.2.1.** Criar `CustomUserManager` em `users/models.py` sobrescrevendo `create_user` e `create_superuser` para utilizar `email` como identificador obrigatório em vez de `username`.
  - [x] **1.2.2.** Criar o model `CustomUser(AbstractUser, BaseModel)` definindo `username = None`, `email = models.EmailField(unique=True)`, `USERNAME_FIELD = 'email'` e `REQUIRED_FIELDS = ['first_name', 'last_name']`.
  - [x] **1.2.3.** Definir `AUTH_USER_MODEL = 'users.CustomUser'` no `core/settings.py`, gerar e executar as migrações iniciais (`makemigrations` e `migrate`).
  - [x] **1.2.4.** Registrar `CustomUser` no `users/admin.py` com listagem e busca por e-mail e nome.
- [x] **1.3. Design System TailwindCSS e Templates Base (`templates`)**
  - [x] **1.3.1.** Criar `templates/base_public.html` com configuração do TailwindCSS, fonte `Inter`, fundo escuro `bg-slate-950`, navbar pública e rodapé.
  - [x] **1.3.2.** Criar `templates/base.html` para a área autenticada contendo Sidebar responsiva fixa (`bg-slate-900 border-slate-800`), links de navegação com estado ativo, topo com saudação ao usuário e bloco de mensagens de alerta (`django.contrib.messages`).
  - [x] **1.3.3.** Criar componentes parciais reutilizáveis em `templates/partials/` (`_card_kpi.html`, `_empty_state.html`, `_modal_confirm_delete.html`).
- [x] **1.4. Landing Page Pública e Fluxo de Autenticação (`core` & `users`)**
  - [x] **1.4.1.** Implementar `LandingPageView(TemplateView)` em `core/views.py` apresentando os recursos do Tallyora e botões "Cadastre-se" e "Entrar" (redirecionando usuários já logados para `/dashboard/`).
  - [x] **1.4.2.** Criar `UserRegistrationForm` e `EmailAuthenticationForm` em `users/forms.py` aplicando as classes do Design System TailwindCSS nos widgets e labels em pt-BR.
  - [x] **1.4.3.** Implementar `UserRegisterView(CreateView)`, `UserLoginView(LoginView)` e `UserLogoutView(LogoutView)` em `users/views.py`, configurando `LOGIN_REDIRECT_URL = 'core:dashboard'` e `LOGOUT_REDIRECT_URL = 'core:landing'`.

---

### Sprint 2: Perfil Financeiro (CLT / PJ), Descontos de Folha, Contas e Categorias
- [ ] **2.1. Perfil Financeiro e Descontos Salariais (`profiles`)**
  - [ ] **2.1.1.** Criar o model `UserProfile(BaseModel)` em `profiles/models.py` com `OneToOneField` para `CustomUser`, campos `work_regime` (`CLT`, `PJ`), `payment_frequency` (`WEEKLY`, `BIWEEKLY`, `MONTHLY`), `base_gross_income`, `advance_percentage` (padrão `40.00`), `has_investments`, `investment_allocation_type` (`PERCENTAGE`, `FIXED`) e `investment_allocation_value`.
  - [ ] **2.1.2.** Criar o model `PayrollDeduction(BaseModel)` em `profiles/models.py` para registrar descontos fixos de contracheque CLT (ex: INSS, IRRF, Consignado, Plano de Saúde).
  - [ ] **2.1.3.** Criar `profiles/signals.py` com signal `post_save` vinculado ao `CustomUser` para criar automaticamente um `UserProfile` padrão assim que um novo usuário se cadastrar, registrando-o em `profiles/apps.py`.
  - [ ] **2.1.4.** Criar `UserProfileForm` e `PayrollDeductionForm` em `profiles/forms.py` com validações de porcentagem ($0\%$ a $100\%$) e estilização Tailwind.
  - [ ] **2.1.5.** Implementar as CBVs `ProfileConfigView(LoginRequiredMixin, UpdateView)`, `PayrollDeductionCreateView(LoginRequiredMixin, CreateView)` e `PayrollDeductionDeleteView(LoginRequiredMixin, DeleteView)` em `profiles/views.py`.
  - [ ] **2.1.6.** Criar o template `profiles/profile_detail.html` exibindo o resumo salarial (Bruto, Descontos de Folha, Valor 1ª Quinzena Dia 15, Valor 2ª Quinzena Dia 30 e Salário Líquido Total).
- [ ] **2.2. Contas Bancárias e Cartões de Crédito (`accounts`)**
  - [ ] **2.2.1.** Criar o model `BankAccount(BaseModel)` em `accounts/models.py` contendo `user`, `name`, `initial_balance`, `has_credit_card`, `closing_day` e `due_day`.
  - [ ] **2.2.2.** Criar `BankAccountForm` em `accounts/forms.py` validando que `closing_day` e `due_day` estejam entre 1 e 31 quando `has_credit_card=True`.
  - [ ] **2.2.3.** Implementar `AccountListView`, `AccountCreateView`, `AccountUpdateView` e `AccountDeleteView` em `accounts/views.py` filtrando por `request.user`.
  - [ ] **2.2.4.** Criar os templates de listagem e formulário de contas/cartões em `templates/accounts/`.
- [ ] **2.3. Categorias de Transações (`categories`)**
  - [ ] **2.3.1.** Criar o model `Category(BaseModel)` em `categories/models.py` com `user`, `name`, `category_type` (`INCOME`, `EXPENSE`) e `color_hex`.
  - [ ] **2.3.2.** Implementar signal em `categories/signals.py` para popular categorias padrão (Salário, Adiantamento, Moradia, Alimentação, Transporte, Lazer, Saúde, Assinaturas) ao criar um novo usuário.
  - [ ] **2.3.3.** Implementar CRUD completo via CBVs (`CategoryListView`, `CategoryCreateView`, `CategoryUpdateView`, `CategoryDeleteView`) e templates em `templates/categories/`.

---

### Sprint 3: Motor de Transações, Despesas Fixas, Fatura sem Duplicidade e Caixinhas
- [ ] **3.1. Despesas Fixas Recorrentes e Transações (`transactions`)**
  - [ ] **3.1.1.** Criar o model `RecurringExpense(BaseModel)` em `transactions/models.py` com `title`, `amount`, `due_day`, `billing_cycle` (`FIRST_HALF`, `SECOND_HALF`, `MONTHLY`), `is_on_credit_card` (`BooleanField`) e `is_active`.
  - [ ] **3.1.2.** Criar o model `Transaction(BaseModel)` em `transactions/models.py` com `title`, `amount`, `transaction_type` (`INCOME`, `EXPENSE`, `CREDIT_CARD_BILL`), `reference_date`, `is_on_credit_card` (`BooleanField`) e `is_paid`.
  - [ ] **3.1.3.** Criar `RecurringExpenseForm` e `TransactionForm` em `transactions/forms.py` destacando o campo `is_on_credit_card` ("Este gasto está na fatura do cartão de crédito?").
  - [ ] **3.1.4.** Implementar CBVs de CRUD para `RecurringExpense` e `Transaction` em `transactions/views.py` com filtros por mês/ano e período (1ª quinzena, 2ª quinzena ou mês completo).
- [ ] **3.2. Caixinhas / Objetivos com Suporte a % ou R$ Fixo (`goals_events`)**
  - [ ] **3.2.1.** Criar o model `GoalBox(BaseModel)` em `goals_events/models.py` com `name`, `storage_location`, `allocation_type` (`PERCENTAGE`, `FIXED`), `allocation_value`, `current_balance` e `target_amount`.
  - [ ] **3.2.2.** Implementar método utilitário `calculate_period_contribution(available_balance)` no model `GoalBox` que retorna o valor exato em `R$` a ser separado no mês conforme a escolha do usuário (`%` sobre a base disponível ou valor fixo em `R$`).
  - [ ] **3.2.3.** Implementar CRUD via CBVs (`GoalBoxListView`, `GoalBoxCreateView`, `GoalBoxUpdateView`, `GoalBoxDeleteView`) e templates com barra de progresso em `templates/goals_events/`.
- [ ] **3.3. Motor de Cálculo Financeiro Detalhado (`transactions/services.py`)**
  - [ ] **3.3.1.** Criar a classe de serviço `FinancialCalculationService` em `transactions/services.py` para consolidar os números do período selecionado pelo usuário.
  - [ ] **3.3.2.** Implementar o cálculo da Receita Líquida do período (considerando salário bruto CLT menos `PayrollDeduction` ou entradas variáveis PJ do período).
  - [ ] **3.3.3.** Implementar a regra de **Evitação de Duplicidade da Fatura**: somar separadamente (A) Despesas Fixas e Variáveis onde `is_on_credit_card=False` e (B) Total da Fatura do Cartão (composta pelo lançamento de fatura ou soma dos itens `is_on_credit_card=True`), garantindo que nenhum item no cartão seja subtraído duas vezes do saldo em conta.
  - [ ] **3.3.4.** Implementar o abatimento sequencial das alocações de Investimento (`%` ou `R$`), Caixinhas (`%` ou `R$`) e Aportes de Eventos Ativos, retornando o valor exato do **"Saldo Livre no Mês (O que sobra)"**.

---

### Sprint 4: Administrador de Eventos (Casamento / Viagens) e Carteira de Investimentos P3X
- [ ] **4.1. Módulo Administrador de Eventos (`goals_events`)**
  - [ ] **4.1.1.** Criar o model `EventPlan(BaseModel)` em `goals_events/models.py` com `title` (ex: Casamento, Viagem), `event_date`, `already_saved_amount`, `monthly_contribution_type` (`PERCENTAGE`, `FIXED`), `monthly_contribution_value` e vínculo opcional com `GoalBox`.
  - [ ] **4.1.2.** Criar o model `EventExpenseItem(BaseModel)` em `goals_events/models.py` vinculado ao `EventPlan` com `supplier_name` (ex: Assessoria, Buffet, Hospedagem), `category_name`, `total_cost`, `amount_paid`, `payment_status` (`PENDING`, `PARTIAL`, `PAID`) e properties `remaining_amount` (`total_cost - amount_paid`).
  - [ ] **4.1.3.** Integrar o `monthly_contribution_value` dos eventos ativos ao `FinancialCalculationService` para que apareça automaticamente como separador/compromisso na tela principal do salário.
  - [ ] **4.1.4.** Implementar `EventPlanListView`, `EventPlanCreateView`, `EventPlanDetailView`, `EventExpenseItemCreateView`, `EventExpenseItemUpdateView` e `EventExpenseItemDeleteView` em `goals_events/views.py`.
  - [ ] **4.1.5.** Criar o template `goals_events/event_detail.html` exibindo os cards de resumo do evento (Custo Total do Evento, Total Já Pago, Falta Pagar, Total Já Guardado, Quanto Falta Guardar) e a tabela detalhada de fornecedores.
- [ ] **4.2. Carteira de Investimentos Inspirada na P3X (`investments`)**
  - [ ] **4.2.1.** Criar o model `AssetAllocationTarget(BaseModel)` em `investments/models.py` para definir a meta percentual de cada classe (`FII`, `STOCK`, `FIXED_INCOME`, `CRYPTO`).
  - [ ] **4.2.2.** Criar o model `InvestmentAsset(BaseModel)` em `investments/models.py` com `asset_class`, `ticker`, `name`, `quantity`, `average_price`, `current_price`, `target_percentage_in_class` e `last_quote_update`.
  - [ ] **4.2.3.** Implementar properties de cálculo no model `InvestmentAsset`: `total_invested` (`quantity * average_price`), `current_total_value` (`quantity * current_price`), `profit_loss_amount` e `profit_loss_percentage`.
  - [ ] **4.2.4.** Criar o serviço `QuoteUpdaterService` em `investments/services.py` utilizando a API gratuita `brapi.dev` (ou `yfinance`) para buscar as cotações atuais dos tickers de Ações e FIIs na B3 e atualizar `current_price` e `last_quote_update`.
  - [ ] **4.2.5.** Implementar `PortfolioDashboardView(LoginRequiredMixin, TemplateView)`, `AssetCreateView`, `AssetUpdateView`, `AssetDeleteView` e `RefreshQuotesView(LoginRequiredMixin, View)` em `investments/views.py`.
  - [ ] **4.2.6.** Construir o template `investments/portfolio.html` inspirado na plataforma P3X: cards de Patrimônio Total, Lucro/Prejuízo, gráfico de rosca da divisão atual vs meta por classe, e abas/tabelas separadas para FIIs, Ações e Renda Fixa com indicação de onde aportar.

---

### Sprint 5: Dashboard Consolidado e Lembretes do Dia (To-Do sem Check + Google Calendar)
- [ ] **5.1. Lembretes Diários sem Checkbox (`reminders`)**
  - [ ] **5.1.1.** Criar o model `DailyReminder(BaseModel)` em `reminders/models.py` com `user`, `title`, `scheduled_time`, `reminder_date` (default `timezone.localdate`) e `external_google_event_id`.
  - [ ] **5.1.2.** Criar `DailyReminderForm` e implementar `ReminderListView`, `ReminderCreateView` e `ReminderDeleteView` em `reminders/views.py` (sem campo ou ação de "marcar como concluído/check").
  - [ ] **5.1.3.** Criar serviço opcional `GoogleCalendarSyncService` em `reminders/services.py` para ler os compromissos do dia da agenda do usuário (caso o token OAuth2 esteja configurado) e espelhá-los na listagem do dia.
- [ ] **5.2. Construção do Dashboard Principal (`core`)**
  - [ ] **5.2.1.** Implementar `DashboardView(LoginRequiredMixin, TemplateView)` em `core/views.py` consumindo dados do `FinancialCalculationService`, resumo das `GoalBox`, `EventPlan`, `InvestmentAsset` e `DailyReminder` do dia.
  - [ ] **5.2.2.** Criar o template `core/dashboard.html` contendo:
    - Seletor de período (Mês/Ano e visão Mensal / 1ª Quinzena / 2ª Quinzena).
    - Linha de Cards principais: `Receita Líquida`, `Gastos na Conta`, `Fatura do Cartão`, `Investimentos & Caixinhas` e o card em destaque `Saldo Livre (O que sobra no mês)`.
    - Gráfico de Pizza/Donut (Chart.js) simples e limpo exibindo a distribuição do orçamento mensal.
    - Painel lateral de **Lembretes de Hoje** (sem check, com botão rápido de adicionar lembrete).
    - Resumo rápido das Caixinhas e Eventos ativos.

---

### Sprint 6: Testes Automatizados, Refinamento PEP8 e Dockerização (Sprint Final)
- [ ] **6.1. Padronização PEP8 e Revisão de Código**
  - [ ] **6.1.1.** Instalar e executar `flake8` / `black --skip-string-normalization` (ou configurar para forçar aspas simples `'`) garantindo 100% de aderência à PEP8 e uso de aspas simples em todos os arquivos `.py`.
  - [ ] **6.1.2.** Revisar todos os templates HTML garantindo que 100% dos textos visíveis, mensagens de formulário e estados vazios estejam em Português Brasileiro (`pt-BR`).
- [ ] **6.2. Testes Automatizados (`tests.py` de cada app)**
  - [ ] **6.2.1.** Implementar testes unitários em `users/tests.py` e `profiles/tests.py` validando login por e-mail, criação automática de perfil via signal e cálculo de descontos CLT.
  - [ ] **6.2.2.** Implementar testes unitários em `transactions/tests.py` validando a regra de não-duplicidade de despesas marcadas com `is_on_credit_card=True` e o cálculo de caixinhas por `%` e por `R$` fixo.
  - [ ] **6.2.3.** Implementar testes em `goals_events/tests.py` e `investments/tests.py` validando o cálculo de saldo pendente de fornecedores de eventos e o cálculo de rentabilidade da carteira.
- [ ] **6.3. Dockerização da Aplicação**
  - [ ] **6.3.1.** Criar `Dockerfile` enxuto baseado em `python:3.12-slim` configurando variáveis de ambiente, instalação de dependências e comando de inicialização.
  - [ ] **6.3.2.** Criar `docker-compose.yml` orquestrando os containers `web` (Django) e `db` (PostgreSQL 16) com volume persistente e `healthcheck`.
  - [ ] **6.3.3.** Documentar o passo a passo de execução local (com e sem Docker) no arquivo `README.md`.

  ---