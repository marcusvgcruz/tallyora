# 05 — Regras de Negócio Financeiras

Regras que definem o funcionamento do motor de cálculo. Estão no PRD (RF09, RF10, RF11, RF12, RF14) e são o coração do produto: **toda alteração aqui exige teste**.

## 1. Receita líquida do período

| Regime | Regra |
| :--- | :--- |
| `CLT` mensal | `base_gross_income` − soma das `PayrollDeduction` ativas do usuário |
| `CLT` quinzenal | 1ª quinzena (dia 15) = `base_gross_income × advance_percentage`, **sem descontos**; 2ª quinzena (dia 30) = restante (`100% − advance_percentage`) **menos** os descontos de folha. `advance_percentage` padrão `40.00`. |
| `PJ` | Receita realizada no período selecionado (semana, quinzena ou mês); não há desconto de folha. |
| `CLT` semanal (`WEEKLY`) | Pagamento único no fechamento do período: não há divisão em quinzenas (`first_half_income = 0`, `second_half_income = líquido`). |

O período selecionado pode ser: **mês completo**, **1ª quinzena** ou **2ª quinzena**.

## 2. Fatura do cartão sem duplicidade (RF09 / US03)

Todo lançamento de despesa — `RecurringExpense` e `Transaction` — carrega a flag `is_on_credit_card`, exibida ao usuário como *"Este gasto está na fatura do cartão de crédito?"*.

**Regra:**

- `is_on_credit_card = True` → o valor **compõe o total da fatura** do período e **não** é subtraído individualmente do saldo em conta.
- `is_on_credit_card = False` → o valor é subtraído diretamente do saldo em conta ("Gastos na Conta").
- A fatura entra no cálculo uma única vez, seja pelo lançamento consolidado `CREDIT_CARD_BILL`, seja pela soma dos itens marcados.

Isso evita exatamente o erro clássico: lançar a fatura e, além dela, descontar cada despesa do cartão novamente.

## 3. Saldo do período e saldo livre (RF10 / US04)

```
Saldo Após Gastos = Receita Líquida
                  − (Gastos Fixos fora do cartão + Gastos Variáveis fora do cartão + Total da Fatura do Cartão)

Saldo Livre Final = Saldo Após Gastos
                  − (Alocação para Investimentos + Total separado em Caixinhas + Aportes mensais de Eventos ativos)
```

A linha de cálculo exibida na tela principal segue a ordem:

```
Receita Líquida (−) Gastos Conta (−) Fatura Cartão (−) Investimentos (−) Caixinhas/Eventos (=) Saldo Livre
```

`Saldo Livre` é o **único** número que responde "quanto sobra de verdade na conta corrente". É o card de destaque do dashboard.

## 4. Caixinhas / cofres (RF11)

- Cada caixinha define a alocação por `allocation_type`:
  - `PERCENTAGE`: `allocation_value` é `%` sobre o saldo disponível.
  - `FIXED`: `allocation_value` é `R$` fixo.
- Método previsto no model: `calculate_period_contribution(available_balance)` → retorna o `R$` a separar no período.
- Cada caixinha guarda `current_balance` (acumulado) e `target_amount` (meta), além de `storage_location` (onde o dinheiro está: cofrinho do banco, CDB de liquidez diária, etc.).
- Validação: a soma das alocações **percentuais ativas** não pode passar de 100% (R04 do PRD); alocações fixas que superem a receita líquida devem gerar alerta.

## 5. Eventos (RF12 / US06)

- `EventPlan` representa um grande projeto: casamento, viagem, reforma. Campos: `title`, `event_date`, `already_saved_amount`, `monthly_contribution_type`, `monthly_contribution_value`; vínculo opcional com uma `GoalBox`.
- O **aporte mensal do evento entra automaticamente como compromisso** no cálculo do salário/dashboard. Evento ativo não pode ser ignorado pelo motor de cálculo.
- Cada `EventExpenseItem` (fornecedor) guarda `total_cost`, `amount_paid`, `payment_status` (`PENDING`, `PARTIAL`, `PAID`) e deriva `remaining_amount = total_cost − amount_paid`.
- Consolidados do evento:
  - **Custo Total do Evento** = soma de `total_cost`.
  - **Total Já Pago** = soma de `amount_paid`.
  - **Falta Pagar** = soma de `remaining_amount`.
  - **Quanto Falta Guardar** = Falta Pagar − `already_saved_amount` (se positivo).
- O status do item deve ser coerente com o valor pago: `PAID` só com `amount_paid == total_cost`, `PENDING` com `amount_paid == 0`.

## 6. Carteira de investimentos (RF13 / RF14 / US05)

- **Metas por classe:** `AssetAllocationTarget` define o `%` ideal por classe (`FII`, `STOCK`, `FIXED_INCOME`, `CRYPTO`). A soma das metas deve validar exatamente **100%**.
- **Meta por ativo:** `target_percentage_in_class` define o peso do ativo dentro da própria classe.
- **Cálculos por ativo:**
  - `total_invested = quantity × average_price`
  - `current_total_value = quantity × current_price`
  - `profit_loss_amount = current_total_value − total_invested`
  - `profit_loss_percentage = profit_loss_amount / total_invested × 100`
  - `% atual na carteira` comparado com `% ideal` → badge `Aportar` (abaixo da meta) ou `Aguardar` (na meta ou acima).
- **Cotações:** atualizadas por serviço (`QuoteUpdaterService`) via `brapi.dev` ou `yfinance`, acionado por botão/ação "Atualizar Cotações", gravando `current_price` e `last_quote_update`.
- **Fallback obrigatório (R01):** se a API falhar ou estourar *rate limit*, manter a última cotação válida no banco e permitir edição manual de `current_price`. Renda Fixa é atualizada manualmente.

## 7. Alocação para investimentos no perfil (RF06)

`UserProfile` informa se o usuário investe (`has_investments`) e quanto: `investment_allocation_type` (`PERCENTAGE` ou `FIXED`) + `investment_allocation_value` sobre a renda líquida. Esse valor é o que entra como "Investimentos" na fórmula do saldo livre — e não o total da carteira.

## 8. Lembretes do dia (RF15)

- Exibidos apenas onde `reminder_date == timezone.localdate()`.
- **Sem checkbox de conclusão**: o usuário adiciona, edita e remove — não marca como feito.
- `external_google_event_id` existe para o espelho opcional do Google Calendar (leitura OAuth2). Sem token configurado, o módulo funciona 100% por cadastro manual (mitigação R03).

## 9. Ordem de cálculo no fechamento do período

Sequência que o `FinancialCalculationService` deve seguir:

1. Determinar o período (mês / 1ª quinzena / 2ª quinzena).
2. Calcular **receita líquida** (CLT com descontos ou PJ do período).
3. Separar **gastos fora do cartão** (fixos + variáveis com `is_on_credit_card = False`).
4. Calcular **fatura do cartão** (itens com `is_on_credit_card = True` ou lançamento `CREDIT_CARD_BILL`).
5. Abater: `receita − gastos conta − fatura` = **saldo após gastos**.
6. Abater alocação de investimentos (`%` ou `R$`).
7. Abater caixinhas (`%` ou `R$`) e aportes de eventos ativos.
8. Resultado = **saldo livre do período**.

Nenhum valor pode ser abatido duas vezes; toda soma deve ser rastreável ao lançamento de origem.
