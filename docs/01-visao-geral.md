# 01 — Visão Geral

## O que é

O **Tallyora** é uma aplicação web *full stack* de gestão de finanças pessoais, controle de investimentos e planejamento de eventos. Transforma a lógica de uma planilha financeira avançada em uma plataforma web com interface *Dark Mode*.

## Problema que resolve

Aplicativos financeiros comuns erram em três pontos do fluxo de caixa brasileiro:

1. Duplicam despesas que já estão dentro da fatura do cartão de crédito.
2. Não modelam salário quinzenal (adiantamento + pagamento final com descontos em folha).
3. Tratam o dinheiro reservado desconectado dos grandes projetos do usuário (casamento, viagem, reforma).

O Tallyora responde a três perguntas:

1. *Quanto realmente sobra na conta no período, depois de contas, fatura e objetivos?*
2. *Como está a evolução do patrimônio investido e onde aportar este mês?*
3. *Quanto já paguei, quanto falta pagar e quanto preciso guardar por mês nos eventos?*

## Público-alvo

- Profissionais **CLT** — renda mensal ou quinzenal, com descontos de folha (INSS, IRRF, consignado).
- **PJ / autônomos / freelancers** — receita variável (semanal, quinzenal ou mensal).
- **Investidores pessoa física** — FIIs, ações e renda fixa.
- Pessoas planejando **grandes eventos** — casamento, viagem, reforma.

## Os quatro pilares (RF de referência)

| Pilar | O que faz | Módulo |
| :--- | :--- | :--- |
| Fluxo de caixa realista (CLT e PJ) | Entradas brutas, descontos retidos, despesas fixas e variáveis, fatura de cartão sem duplicidade | `profiles`, `transactions` |
| Alocação inteligente (caixinhas e cofres) | Divisão do saldo por `%` ou `R$` fixo, revelando o saldo livre | `goals_events` |
| Carteira de investimentos | FIIs, ações e renda fixa com metas percentuais por classe e cotação atualizada | `investments` |
| Eventos e lembretes diários | Fornecedores, pagamentos e aportes mensais; mural diário de lembretes sem *check* | `goals_events`, `reminders` |

## Módulos do sistema

Cada módulo corresponde a uma app Django **já criada** no projeto. O conteúdo funcional de cada uma ainda é backlog.

| App | Responsabilidade |
| :--- | :--- |
| `core` | Configurações do projeto, `BaseModel`, Landing Page pública e Dashboard principal |
| `users` | `CustomUser` com autenticação exclusivamente por e-mail |
| `profiles` | Perfil financeiro: regime (CLT/PJ), periodicidade, descontos de folha, meta de investimento |
| `accounts` | Contas bancárias e cartões de crédito (dia de fechamento e vencimento) |
| `categories` | Categorias de receita e despesa |
| `transactions` | Despesas fixas recorrentes, transações e motor de cálculo do período |
| `goals_events` | Caixinhas/cofres e planejador de eventos com fornecedores |
| `investments` | Metas por classe de ativo, ativos da carteira e atualização de cotações |
| `reminders` | Lembretes do dia (mural visual, sem checkbox de conclusão) |

## Objetivos

1. **MVP funcional local (curto prazo):** autenticação por e-mail, onboarding de perfil CLT/PJ, motor de cálculo mensal/quinzenal/semanal sem duplicidade de cartão, caixinhas por `%` ou `R$`, dashboard consolidado, módulo de eventos, carteira de investimentos e lembretes do dia.
2. **Médio prazo:** leitura opcional do Google Calendar para os lembretes do dia e busca automática de cotações da B3 (`brapi.dev` / `yfinance`).
3. **Qualidade técnica:** código 100% PEP8, sem *over-engineering*, usando recursos nativos do Django (CBVs, DTL, ORM) e PostgreSQL.

## Fora de escopo (decidido no PRD)

Não usar, nas sprints iniciais: microserviços, SPA separada em React/Vue, Celery e Redis. A aplicação é monolítica e roda inteiramente em Django (RNF01).
