# Tallyora

Finanças pessoais, investimentos e eventos em um só lugar — receita do mês,
gastos na conta, fatura do cartão sem duplicidade, caixinhas, carteira de
investimentos e o **Saldo Livre** (o que realmente sobra).

Django 6.1 + PostgreSQL/SQLite + Tailwind (compilado localmente, sem CDN).

## Rodar em 5 passos (modo `dev`, SQLite)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # edite SECRET_KEY
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Abra `http://127.0.0.1:8000/`.

O CSS já vem compilado e versionado. Só rode
`python manage.py tailwind build` depois de mexer em template (a primeira vez
em uma máquina nova, rode também `python manage.py tailwind install`).

## Ambientes

| `APP_ENV` | Banco |
| :--- | :--- |
| `dev` (padrão) | SQLite em `db.sqlite3` |
| `prd` | PostgreSQL (`DB_*` no `.env`) |

Detalhes de setup, acesso por VS Code via SSH e port forwarding:
[`docs/07-setup-e-execucao.md`](docs/07-setup-e-execucao.md).

## Regras do projeto

- Código 100% em inglês, interface 100% em pt-BR.
- PEP8, linhas ≤ 79 colunas, aspas simples.
- Todo model herda de `BaseModel` (auditoria de criação/edição).
- Valores monetários em `Decimal` com `to_money()` (`ROUND_HALF_UP`, 2 casas).
- `.env` nunca é commitado.

## Documentação

| Arquivo | Conteúdo |
| :--- | :--- |
| [`docs/01-visao-geral.md`](docs/01-visao-geral.md) | Produto, personas, escopo |
| [`docs/02-arquitetura-e-estrutura.md`](docs/02-arquitetura-e-estrutura.md) | Apps, camadas, rotas |
| [`docs/03-padroes-de-codigo.md`](docs/03-padroes-de-codigo.md) | Convenções |
| [`docs/04-modelos-e-banco.md`](docs/04-modelos-e-banco.md) | Models e migrações |
| [`docs/05-regras-de-negocio-financeiras.md`](docs/05-regras-de-negocio-financeiras.md) | Motor de cálculo |
| [`docs/06-design-system.md`](docs/06-design-system.md) | Componentes e tema |
| [`docs/07-setup-e-execucao.md`](docs/07-setup-e-execucao.md) | Como rodar |
| [`docs/08-estado-do-projeto.md`](docs/08-estado-do-projeto.md) | O que existe hoje |
| [`PRD.md`](PRD.md) / [`TASKS.md`](TASKS.md) | Requisitos e backlog |
