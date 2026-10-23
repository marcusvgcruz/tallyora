# 04 — Modelos e Banco de Dados

Nenhum model do domínio existe em código hoje: todos os `models.py` das apps contêm apenas o cabeçalho gerado pelo Django. Este documento fixa as convenções e o desenho de dados já definido no PRD (seção 8.3), para que a implementação siga um padrão único.

## Convenções gerais

1. Todo model herda de `BaseModel` (RNF05) — `created_at` e `updated_at` em todas as tabelas.
2. Todo model de domínio tem `user = models.ForeignKey(...)` para o `CustomUser`, exceto os que pertencem a outro model (ex.: `EventExpenseItem` → `EventPlan`).
3. Valores monetários em `DecimalField(max_digits=12, decimal_places=2)` — nunca `FloatField`.
4. Percentuais em `DecimalField(max_digits=5, decimal_places=2)` (`0.00` a `100.00`).
5. Datas em `DateField`; timestamps em `DateTimeField` com `timezone.localdate` como default quando for "hoje".
6. Opções fechadas via `TextChoices` em maiúsculas (`CLT`, `PJ`, `PENDING`, ...), sem string solta no código.
7. Regras derivadas (ex.: total pago, falta pagar) são `@property` no model — não colunas duplicadas no banco.

## `BaseModel` — `core/models.py` (planejado, tarefa 1.1.5)

```python
from django.db import models


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
```

## `CustomUser` — `users/models.py` (planejado, Sprint 1.2)

- `username = None`; `email = models.EmailField(unique=True)` é o `USERNAME_FIELD`.
- `REQUIRED_FIELDS = ['first_name', 'last_name']`.
- `CustomUserManager` sobrescrevendo `create_user` e `create_superuser`.
- `AUTH_USER_MODEL = 'users.CustomUser'` no `settings.py` — precisa ser definido **antes** da primeira migração.

## Desenho de dados por app (PRD 8.3)

### `profiles`

| Model | Campos principais |
| :--- | :--- |
| `UserProfile` (1:1 com `CustomUser`, criado por signal) | `work_regime` (`CLT`/`PJ`), `payment_frequency` (`WEEKLY`/`BIWEEKLY`/`MONTHLY`), `base_gross_income`, `advance_percentage` (padrão `40.00`), `has_investments`, `investment_allocation_type` (`PERCENTAGE`/`FIXED`), `investment_allocation_value` |
| `PayrollDeduction` | `user`, `name` (INSS, IRRF, consignado), `amount`, `is_active` |

### `accounts`

| Model | Campos principais |
| :--- | :--- |
| `BankAccount` | `user`, `name`, `initial_balance`, `has_credit_card`, `closing_day`, `due_day` |

### `categories`

| Model | Campos principais |
| :--- | :--- |
| `Category` | `user`, `name`, `category_type` (`INCOME`/`EXPENSE`), `color_hex` |

### `transactions`

| Model | Campos principais |
| :--- | :--- |
| `RecurringExpense` | `user`, `category`, `account`, `title`, `amount`, `due_day`, `is_on_credit_card`, `billing_cycle` (`FIRST_HALF`/`SECOND_HALF`/`MONTHLY`), `is_active` |
| `Transaction` | `user`, `account`, `category`, `title`, `amount`, `transaction_type` (`INCOME`/`EXPENSE`/`CREDIT_CARD_BILL`), `reference_date`, `is_on_credit_card`, `is_paid` |

### `goals_events`

| Model | Campos principais |
| :--- | :--- |
| `GoalBox` | `user`, `name`, `storage_location`, `allocation_type` (`PERCENTAGE`/`FIXED`), `allocation_value`, `current_balance`, `target_amount` |
| `EventPlan` | `user`, `linked_goal_box` (FK opcional), `title`, `event_date`, `already_saved_amount`, `monthly_contribution_type` (`PERCENTAGE`/`FIXED`), `monthly_contribution_value` |
| `EventExpenseItem` | `event` (FK), `supplier_name`, `category_name`, `total_cost`, `amount_paid`, `payment_status` (`PENDING`/`PARTIAL`/`PAID`), `notes` |

Relação: um `GoalBox` pode financiar no máximo um `EventPlan`; um `EventPlan` tem vários `EventExpenseItem`.

### `investments`

| Model | Campos principais |
| :--- | :--- |
| `AssetAllocationTarget` | `user`, `asset_class` (`FII`/`STOCK`/`FIXED_INCOME`/`CRYPTO`), `target_percentage` |
| `InvestmentAsset` | `user`, `asset_class`, `ticker`, `name`, `quantity`, `average_price`, `current_price`, `target_percentage_in_class`, `last_quote_update` |

`InvestmentAsset` expõe properties calculadas: `total_invested` (`quantity * average_price`), `current_total_value` (`quantity * current_price`), `profit_loss_amount`, `profit_loss_percentage`.

### `reminders`

| Model | Campos principais |
| :--- | :--- |
| `DailyReminder` | `user`, `title`, `scheduled_time`, `reminder_date` (default `timezone.localdate`), `external_google_event_id` |

Não existe campo de conclusão/`is_done` — decisão de produto: o mural não tem check (RF15).

## Banco de dados

### Situação atual

- `core/settings.py` usa `django.db.backends.sqlite3` apontando para `db.sqlite3`.
- O `db.sqlite3` já tem as migrações padrão do Django aplicadas (`auth_*`, `admin`, `sessions`, `contenttypes`) — nenhuma tabela de domínio.
- `psycopg2-binary` está instalado mas não é usado por nenhuma configuração.

### Alvo (RNF04)

- **PostgreSQL 16+** como único banco. O `db.sqlite3` deve ser removido do projeto e ignorado.
- Credenciais (`NAME`, `USER`, `PASSWORD`, `HOST`, `PORT`) lidas de variáveis de ambiente via `.env` com `python-dotenv`.
- Caminho: tarefa 1.1.3 do backlog.

### Migrações

- Gerar com `makemigrations` e aplicar com `migrate` a cada model novo ou alteração de campo.
- Migração versionada junto com o código que a gerou — nunca editar migração já aplicada.
- Como o `AUTH_USER_MODEL` será alterado para `users.CustomUser`, a troca precisa ocorrer antes de existirem dados de usuário em produção (ou com banco recriado).

## Índices e integridade

- Unicidade por usuário onde faz sentido: `Category` (`user` + `name`), `AssetAllocationTarget` (`user` + `asset_class`), `InvestmentAsset` (`user` + `ticker`).
- `on_delete=models.CASCADE` a partir do usuário; em `EventPlan.linked_goal_box`, `on_delete=models.SET_NULL` com `null=True` para o vínculo ser opcional.
- Validação de regra de negócio (soma de percentuais ≤ 100%) no `clean()` do model/form, não só na view.
