# Documentação — Tallyora

Índice da documentação técnica e de produto do projeto **Tallyora**.

Tallyora é uma aplicação web de gestão de finanças pessoais, investimentos e planejamento de eventos, construída com Python, Django e TailwindCSS.

## Como navegar

| Documento | Responde |
| :--- | :--- |
| [01-visao-geral.md](01-visao-geral.md) | O que é o produto, para quem, qual o problema que resolve e qual o escopo por módulo |
| [02-arquitetura-e-estrutura.md](02-arquitetura-e-estrutura.md) | Stack real, estrutura de diretórios, papel de cada app e camadas do código |
| [03-padroes-de-codigo.md](03-padroes-de-codigo.md) | PEP8, idioma, aspas, uso de CBVs/forms/DTL, signals e isolamento de dados |
| [04-modelos-e-banco.md](04-modelos-e-banco.md) | `BaseModel`, `CustomUser`, models previstos por app e regras de banco de dados |
| [05-regras-de-negocio-financeiras.md](05-regras-de-negocio-financeiras.md) | Fórmulas de receita líquida, fatura sem duplicidade, saldo livre, caixinhas, eventos e carteira |
| [06-design-system.md](06-design-system.md) | Dark mode, paleta, tipografia, componentes TailwindCSS e layouts |
| [07-setup-e-execucao.md](07-setup-e-execucao.md) | Como rodar o projeto localmente (ambiente virtual, migrações, servidor) |
| [08-estado-do-projeto.md](08-estado-do-projeto.md) | O que já está implementado hoje e o que ainda é backlog |

## Leitura recomendada por perfil

- **Quem está começando no projeto:** `01` → `02` → `07` (sobe o ambiente) → `03`.
- **Quem vai implementar features:** `03` + `04` + `05` (regra de negócio) e só então o `PRD.md`.
- **Quem vai trabalhar em telas:** `06` e `03`.

## Documentos de origem

Esta pasta **não substitui** os documentos originais na raiz do projeto:

- `../PRD.md` — Product Requirement Document (visão de produto, requisitos funcionais RF01–RF16, requisitos não-funcionais RNF01–RNF08, ERD, user stories, KPIs, riscos).
- `../TASKS.md` — backlog granular em 6 sprints, com o status de cada tarefa.

## Convenção desta documentação

Todo documento desta pasta descreve **o que está definido no projeto** e, quando algo ainda não existe em código, marca explicitamente como **planejado**. Prefixos usados nas referências:

- `RFxx` — requisito funcional do PRD.
- `RNFxx` — requisito não-funcional do PRD.
- `USxx` — user story do PRD.

Última revisão: 23/10/2026.
