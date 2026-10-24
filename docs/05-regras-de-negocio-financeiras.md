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

## 1.1 Despesa fixa entra no período pelo vencimento

`RecurringExpense` tem `due_day` e `billing_cycle`. Uma despesa fixa entra no cálculo quando:

- o `billing_cycle` é compatível: `MONTHLY` vale em qualquer período; `FIRST_HALF` só na 1ª quinzena (e no mês completo); `SECOND_HALF` só na 2ª quinzena (e no mês completo);
- o `due_day` cai dentro dos dias do período (1–15 na 1ª quinzena, 16–fim na 2ª, 1–fim no mês completo).

Vencimento em dia que não existe no mês (31 em fevereiro) conta no mês completo e na 2ª quinzena — nunca desaparece. Consequência: **a soma das duas quinzenas é igual ao mês completo**, sem contar nada duas vezes. Despesas com `is_active=False` ficam fora.

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
- Método **implementado** no model: `calculate_period_contribution(available_balance)` → retorna o `R$` a separar no período. Base ≤ 0 devolve `0` (não se separa de onde não há); `FIXED` devolve o próprio valor, sem teto.
- Cada caixinha guarda `current_balance` (acumulado) e `target_amount` (meta), além de `storage_location` (onde o dinheiro está: cofrinho do banco, CDB de liquidez diária, etc.).
- Validação: cada alocação percentual não pode passar de 100% (validado no `clean()` do model e no `GoalBoxForm`). Alocações fixas que superem a receita líquida levam o saldo livre a negativo — o número é exibido assim mesmo, sem esconder o estouro.
- As caixinhas são abatidas **em sequência** (ordem alfabética do nome): cada uma recebe sua fatia sobre o que sobrou da anterior, e a soma nunca passa do disponível.

## 5. Eventos (RF12 / US06)

- `EventPlan` representa um grande projeto: casamento, viagem, reforma. Campos: `title`, `event_date`, `already_saved_amount`, `monthly_contribution_type`, `monthly_contribution_value`; vínculo opcional com uma `GoalBox`.
- O **aporte mensal do evento entra automaticamente como compromisso** no cálculo do salário/dashboard. Evento ativo não pode ser ignorado pelo motor de cálculo.
- Cada `EventExpenseItem` (fornecedor) guarda `total_cost`, `amount_paid`, `payment_status` (`PENDING`, `PARTIAL`, `PAID`) e deriva `remaining_amount = total_cost − amount_paid`.
- Consolidados do evento:
  - **Custo Total do Evento** = soma de `total_cost`.
  - **Total Já Pago** = soma de `amount_paid`.
  - **Falta Pagar** = soma de `remaining_amount`.
  - **Quanto Falta Guardar** = Falta Pagar − `already_saved_amount` (se positivo).
- O status do item é **derivado**, não digitado: `save()` normaliza para `PENDING` com `amount_paid == 0`, `PAID` com `amount_paid == total_cost` e `PARTIAL` no meio. Pagar mais que o custo é barrado no `clean()`.
- **Base do percentual:** quando `monthly_contribution_type = PERCENTAGE`, o aporte é `percentual × receita líquida`, a mesma base usada pela alocação de investimentos — não o que sobrou do mês. `FIXED` usa o valor cheio.
- Implementado na Sprint 4 em `goals_events/models.py` e no passo 7 do motor (ver §9).

## 6. Carteira de investimentos (RF13 / RF14 / US05)

- **Metas por classe:** `AssetAllocationTarget` define o `%` ideal por classe (`FII`, `STOCK`, `FIXED_INCOME`, `CRYPTO`). A soma das metas deve fechar **100%**; o `clean()` bloqueia qualquer configuração que **passe** de 100% (R04) e a tela mostra quanto falta para fechar quando está abaixo — bloquear a soma parcial impediria cadastrar uma classe por vez.
- **Meta por ativo:** `target_percentage_in_class` define o peso do ativo dentro da própria classe.
- **Cálculos por ativo:**
  - `total_invested = quantity × average_price`
  - `current_total_value = quantity × current_price`
  - `profit_loss_amount = current_total_value − total_invested`
  - `profit_loss_percentage = profit_loss_amount / total_invested × 100`
  - `% atual na carteira` comparado com `% ideal` → badge `Aportar` (abaixo da meta) ou `Aguardar` (na meta ou acima).
- **Cotações:** atualizadas pelo `QuoteUpdaterService`, acionado pelo botão "Atualizar cotações", gravando `current_price` e `last_quote_update`. Três fontes, nesta ordem:
  1. **B3 oficial** (`cotacao.b3.com.br/mds/api/v1/DailyFluctuationHistory/{ticker}`) — sem chave, é a fonte primária; devolve o último preço negociado.
  2. **brapi.dev** — usada só quando `BRAPI_TOKEN` está no `.env` (o plano gratuito exige token; sem ele a API responde 401). Até 10 tickers por chamada.
  3. **Yahoo Finance** — último recurso, um request por ticker.
- **Por que a B3 primeiro:** brapi sem token responde 401 e o Yahoo devolve 429 para IPs de servidor. Só a API oficial funciona sem cadastro — validado com cotações reais (PETR4, MXRF11, VALE3, ITSA4) nesta VPS.
- **Fallback obrigatório (R01):** se a API falhar ou estourar *rate limit*, manter a última cotação válida no banco e permitir edição manual de `current_price`. Renda Fixa é atualizada manualmente.

## 7. Alocação para investimentos no perfil (RF06)

`UserProfile` informa se o usuário investe (`has_investments`) e quanto: `investment_allocation_type` (`PERCENTAGE` ou `FIXED`) + `investment_allocation_value` sobre a renda líquida. Esse valor é o que entra como "Investimentos" na fórmula do saldo livre — e não o total da carteira.

## 8. Lembretes do dia (RF15)

- Exibidos apenas onde `reminder_date == timezone.localdate()`.
- **Sem checkbox de conclusão**: o usuário adiciona, edita e remove — não marca como feito.
- `external_google_event_id` existe para o espelho opcional do Google Calendar (leitura OAuth2). Sem token configurado, o módulo funciona 100% por cadastro manual (mitigação R03).
- **Espelho da agenda:** `GoogleCalendarSyncService.sync_today()` lê os eventos de hoje e faz `update_or_create` por `external_google_event_id`. Regras:
  - só remove/atualiza linhas **com** id externo — lembrete manual nunca é alterado pela sincronização;
  - se a leitura da agenda falhar, a sincronização **não apaga nada** (um erro de rede não pode zerar o mural);
  - evento de dia inteiro entra com horário `00:00` e rótulo "Dia inteiro";
  - falha de configuração/HTTP devolve lista vazia e explica o motivo em `last_error` — nunca derruba o dashboard.

## 9. Ordem de cálculo no fechamento do período

Sequência que o `FinancialCalculationService` (`transactions/services.py`) executa:

1. Determinar o período (mês / 1ª quinzena / 2ª quinzena).
2. Calcular **receita líquida** (CLT com descontos ou PJ do período).
3. Separar **gastos fora do cartão** (fixos + variáveis com `is_on_credit_card = False`).
4. Calcular **fatura do cartão** (itens com `is_on_credit_card = True` ou lançamento `CREDIT_CARD_BILL`).
5. Abater: `receita − gastos conta − fatura` = **saldo após gastos**.
6. Abater alocação de investimentos (`%` ou `R$`).
7. Abater caixinhas (`%` ou `R$`) e aportes de eventos ativos.
8. Resultado = **saldo livre do período**.

Nenhum valor pode ser abatido duas vezes; toda soma deve ser rastreável ao lançamento de origem.

Implementado nas Sprints 3 e 4: passos 1 a 8 completos. O passo 7 abate as caixinhas (sequenciais, ordem alfabética) e depois os aportes dos `EventPlan` ativos; o resumo devolve `goal_boxes` e `event_plans` com o detalhe de cada compromisso, para a tela poder mostrar de onde veio cada abatimento.

Ordem dentro do passo 7: caixinhas primeiro (elas são reserva do dia a dia), eventos depois (compromissos com data). Como o aporte percentual de evento usa a receita líquida e não o saldo corrente, a ordem não altera o valor de cada aporte — só a leitura do saldo final.
