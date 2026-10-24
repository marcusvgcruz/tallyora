# 04 — Modelos e Banco de Dados

Estado real do código (24/10/2026): **Sprints 1 a 4 implementadas** — `BaseModel`, `CustomUser`, `UserProfile`, `PayrollDeduction`, `BankAccount`, `Category`, `Transaction`, `RecurringExpense`, `GoalBox`, `EventPlan`, `EventExpenseItem`, `AssetAllocationTarget` e `InvestmentAsset` existem e estão migrados. Só `reminders` (Sprint 5) segue desenhado como *planejado*.

## Convenções gerais

1. Todo model herda de `BaseModel` (RNF05) — `created_at` e `updated_at` em todas as tabelas.
2. Todo model de domínio tem `user = models.ForeignKey(...)` para o `CustomUser`, exceto os que pertencem a outro model (ex.: `EventExpenseItem` → `EventPlan`).
3. Valores monetários em `DecimalField(max_digits=12, decimal_places=2)` — nunca `FloatField`.
4. Percentuais em `DecimalField(max_digits=5, decimal_places=2)` (`0.00` a `100.00`), com `MinValueValidator`/`MaxValueValidator`.
5. Datas em `DateField`; timestamps em `DateTimeField` com `timezone.localdate` como default quando for "hoje".
6. Opções fechadas via `TextChoices` em maiúsculas (`CLT`, `PJ`, `PENDING`, ...), sem string solta no código.
7. Regras derivadas (ex.: total pago, falta pagar) são `@property` no model — não colunas duplicadas no banco.
8. `verbose_name` dos campos em pt-BR (aparece em formulário e admin); nomes de campo e código em inglês.

## `BaseModel` — `core/models.py`

```python
class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
```

## `CustomUser` — `users/models.py`

- `username = None`; `email = models.EmailField(unique=True)` é o `USERNAME_FIELD`.
- `REQUIRED_FIELDS = ['first_name', 'last_name']`.
- `CustomUserManager` sobrescreve `create_user` e `create_superuser`, normalizando o e-mail para minúsculas e levantando `ValueError` sem e-mail.
- `AUTH_USER_MODEL = 'users.CustomUser'` no `settings.py`.
- Admin próprio (`CustomUserAdmin`) por e-mail, sem campo `username`.

## Models implementados

### `profiles`

| Model | Campos | Regras |
| :--- | :--- | :--- |
| `UserProfile` | `user` (1:1, `related_name='profile'`), `work_regime` (`CLT`/`PJ`), `payment_frequency` (`WEEKLY`/`BIWEEKLY`/`MONTHLY`), `base_gross_income`, `advance_percentage` (padrão `40.00`, 0–100), `has_investments`, `investment_allocation_type` (`PERCENTAGE`/`FIXED`), `investment_allocation_value` | Criado automaticamente por signal ao cadastrar o usuário |
| `PayrollDeduction` | `user` (`related_name='payroll_deductions'`), `name`, `amount`, `is_active` | Só afeta o cálculo quando `is_active=True` e o regime é CLT |

Properties do `UserProfile` (fonte única da regra, ver `05-regras-de-negocio-financeiras.md`):

| Property | Regra |
| :--- | :--- |
| `deductions_total` | Soma dos descontos ativos; **`0` quando o regime é PJ** |
| `net_income` | `base_gross_income - deductions_total` |
| `first_half_income` | CLT **quinzenal**: `base_gross_income × advance_percentage / 100` (sem descontos). Outros regimes: `0` |
| `second_half_income` | CLT quinzenal: `net_income - first_half_income`. Regime de pagamento único: `net_income` |

Arredondamento: helper `to_money()` com `ROUND_HALF_UP` em 2 casas — evita centavo perdido na divisão das quinzenas. O helper vive em `core/models.py` (junto de `ZERO` e `MONEY_PLACES`) e é importado por `profiles` e `goals_events`.

### `accounts`

| Model | Campos | Regras |
| :--- | :--- | :--- |
| `BankAccount` | `user` (`related_name='bank_accounts'`), `name`, `initial_balance`, `has_credit_card`, `closing_day`, `due_day` | `closing_day`/`due_day` são `PositiveSmallIntegerField` nulos; obrigatórios (1–31) apenas quando `has_credit_card=True`, e gravados como `None` quando não há cartão |

### `categories`

| Model | Campos | Regras |
| :--- | :--- | :--- |
| `Category` | `user` (`related_name='categories'`), `name`, `category_type` (`INCOME`/`EXPENSE`), `color_hex` | `color_hex` validado por regex `^#[0-9a-fA-F]{6}$`; `UniqueConstraint(user, name, category_type)` |

## Signals (criação automática por usuário)

| Signal | App | Efeito |
| :--- | :--- | :--- |
| `post_save` em `CustomUser` (`created=True`) | `profiles` | Cria o `UserProfile` 1:1 (`get_or_create`) |
| `post_save` em `CustomUser` (`created=True`) | `categories` | Cria as 8 categorias padrão via `bulk_create(ignore_conflicts=True)` |

Categorias padrão: **Receitas** — Salário (`#10b981`), Adiantamento (`#34d399`); **Despesas** — Moradia (`#6366f1`), Alimentação (`#f59e0b`), Transporte (`#3b82f6`), Lazer (`#ec4899`), Saúde (`#ef4444`), Assinaturas (`#8b5cf6`).

Os dois receivers ficam em `<app>/signals.py` e são registrados no `ready()` do `apps.py`.

### `transactions`

| Model | Campos | Regras |
| :--- | :--- | :--- |
| `RecurringExpense` | `user` (`related_name='recurring_expenses'`), `category`, `account`, `title`, `amount`, `due_day`, `billing_cycle` (`FIRST_HALF`/`SECOND_HALF`/`MONTHLY`), `is_on_credit_card`, `is_active` | `due_day` validado 1–31; `category`/`account` com `SET_NULL`; property `applies_every_cycle` |
| `Transaction` | `user` (`related_name='transactions'`), `account`, `category`, `title`, `amount`, `transaction_type` (`INCOME`/`EXPENSE`/`CREDIT_CARD_BILL`), `reference_date`, `is_on_credit_card`, `is_paid` | `reference_date` com default `timezone.localdate`; properties `is_card_bill`, `is_income`, `signed_amount` |

### `goals_events` — caixinhas

| Model | Campos | Regras |
| :--- | :--- | :--- |
| `GoalBox` | `user` (`related_name='goal_boxes'`), `name`, `storage_location`, `allocation_type` (`PERCENTAGE`/`FIXED`), `allocation_value`, `current_balance`, `target_amount` | `allocation_value ≥ 0`; percentual ≤ 100 validado no `clean()` do model e no form; properties `progress_percentage` (limitada a 100) e `remaining_amount` |

`GoalBox.calculate_period_contribution(available_balance)` é a regra única do aporte: percentual aplica a fatia sobre a base disponível, valor fixo devolve o próprio valor e base ≤ 0 devolve `0`.

O motor de cálculo fica em `transactions/services.py` (`Period` + `FinancialCalculationService`), não no model — ver `05-regras-de-negocio-financeiras.md`.

### `goals_events` — eventos (Sprint 4)

| Model | Campos | Regras |
| :--- | :--- | :--- |
| `EventPlan` | `user` (`related_name='event_plans'`), `linked_goal_box` (FK opcional, `SET_NULL`), `title`, `event_date`, `already_saved_amount`, `monthly_contribution_type` (`PERCENTAGE`/`FIXED`), `monthly_contribution_value`, `is_active` | `monthly_contribution(base_amount)` calcula o aporte; percentual ≤ 100 no `clean()`; properties `total_cost`, `total_paid`, `remaining_to_pay`, `amount_still_needed`, `saved_percentage` |
| `EventExpenseItem` | `event` (FK, `related_name='expense_items'`), `supplier_name`, `category_name`, `total_cost`, `amount_paid`, `payment_status` (`PENDING`/`PARTIAL`/`PAID`), `notes` | `payment_status` **derivado no `save()`** (0 → PENDING, igual ao custo → PAID, resto → PARTIAL); pago > custo barrado no `clean()`; property `remaining_amount` |

Relação: um `GoalBox` pode financiar vários `EventPlan` (FK opcional, `SET_NULL`); um `EventPlan` tem vários `EventExpenseItem` (`CASCADE`).

### `investments` (Sprint 4)

| Model | Campos | Regras |
| :--- | :--- | :--- |
| `AssetAllocationTarget` | `user` (`related_name='allocation_targets'`), `asset_class` (`FII`/`STOCK`/`FIXED_INCOME`/`CRYPTO`), `target_percentage` | `UniqueConstraint(user, asset_class)`; `clean()` recusa a soma das metas passando de 100%; classmethods `total_percentage(user)` e `targets_by_class(user)` |
| `InvestmentAsset` | `user` (`related_name='investment_assets'`), `asset_class`, `ticker`, `name`, `quantity` (18,8), `average_price` (14,4), `current_price` (14,4), `target_percentage_in_class`, `last_quote_update` | `ticker` em maiúsculas no `save()`; `UniqueConstraint(user, ticker)`; properties `total_invested`, `current_total_value`, `profit_loss_amount`, `profit_loss_percentage`, `is_quoted` |

`InvestmentAsset` expõe properties calculadas: `total_invested` (`quantity * average_price`), `current_total_value` (`quantity * current_price`), `profit_loss_amount`, `profit_loss_percentage` (0 quando o investido é 0, para não dividir por zero).

## Desenho de dados das sprints futuras (*planejado*)

### `reminders` (Sprint 5)

| Model | Campos principais |
| :--- | :--- |
| `DailyReminder` | `user`, `title`, `scheduled_time`, `reminder_date` (default `timezone.localdate`), `external_google_event_id` |

Não existe campo de conclusão/`is_done` — decisão de produto: o mural não tem check (RF15).

## Banco de dados

### Situação atual (real)

- **PostgreSQL 16.15** é o único banco: `django.db.backends.postgresql`, database/role `tallyora` em `127.0.0.1:5432`.
- Credenciais (`DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`) vêm do `.env` via `python-dotenv`; `SECRET_KEY` é obrigatória.
- `db.sqlite3` foi removido do projeto e está no `.gitignore`.
- Migrações aplicadas: `users.0001_initial`, `profiles.0001_initial`, `accounts.0001_initial`, `categories.0001_initial`, `transactions.0001_initial`, `goals_events.0001_initial`, `goals_events.0002_eventplan_eventexpenseitem`, `investments.0001_initial` + migrações padrão do Django.

### Migrações

- Gerar com `makemigrations` e aplicar com `migrate` a cada model novo ou alteração de campo.
- Migração versionada junto com o código que a gerou — nunca editar migração já aplicada.
- `makemigrations --check --dry-run` deve sair limpo antes de qualquer commit.

## Índices e integridade

- Implementado: `UniqueConstraint(user, name, category_type)` em `Category` (`unique_category_per_user_type`), `UniqueConstraint(user, asset_class)` em `AssetAllocationTarget` (`unique_target_per_user_class`) e `UniqueConstraint(user, ticker)` em `InvestmentAsset` (`unique_ticker_per_user`).
- A `UniqueConstraint` que inclui `user` **não é validada pelo `ModelForm`** — a validação de duplicidade precisa acontecer no `clean()` do form da app (`categories/forms.py`), senão o POST duplicado estoura `IntegrityError`.
- `on_delete=models.CASCADE` a partir do usuário e de `EventPlan` para `EventExpenseItem`; em `EventPlan.linked_goal_box`, `on_delete=models.SET_NULL` com `null=True` para o vínculo ser opcional.
- Validação de regra de negócio (soma de percentuais ≤ 100%) no `clean()` do model/form, não só na view.
