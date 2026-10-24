# Tallyora

Finanças pessoais, investimentos e eventos em um só lugar — receita do mês,
gastos na conta, fatura do cartão sem duplicidade, caixinhas, carteira de
investimentos e o **Saldo Livre** (o que realmente sobra).

Django 6.1 + PostgreSQL/SQLite + Tailwind (compilado localmente, sem CDN).

## Rodar sem Docker (modo `dev`, SQLite)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # edite SECRET_KEY e mantenha APP_ENV=dev
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Abra `http://127.0.0.1:8000/`.

O CSS já vem compilado e versionado. Só rode
`python manage.py tailwind build` depois de mexer em template (a primeira vez
em uma máquina nova, rode também `python manage.py tailwind install`).

## Rodar com Docker (Django + PostgreSQL 16)

Sobe o app com o banco real (`APP_ENV=prd`) em dois containers: `web` e `db`.

```bash
cp .env.example .env                    # edite SECRET_KEY; DB_* pode ficar como está
docker compose up --build               # http://localhost:8080/
```

O que acontece no start:

- O `db` espera o `pg_isready` ficar saudável (`healthcheck`) e só então o
  `web` sobe (`depends_on: condition: service_healthy`).
- O `web` roda `python manage.py migrate --noinput` antes de iniciar o
  servidor — não é preciso migrar à mão.
- O compose força `APP_ENV=prd`, `DB_HOST=db` e `DB_PORT=5432`; o resto
  (`SECRET_KEY`, `ALLOWED_HOSTS`, `DB_*`) vem do `.env`. Sem `DB_PASSWORD` no
  `.env`, o compose usa `tallyora_dev` nos dois lados.
- Os dados do Postgres ficam no volume nomeado `tallyora_pgdata`.

Comandos do dia a dia:

```bash
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py test          # 124 testes, no Postgres
docker compose exec web python manage.py check
docker compose exec web python manage.py shell
docker compose exec db psql -U tallyora -d tallyora     # console do banco
docker compose logs -f web
docker compose down            # para a stack, mantém os dados
docker compose down -v         # para e APAGA o volume do Postgres
```

Ajustes:

- **Porta 8080 ocupada?** O mapeamento padrão é `8080:8000`, mas a porta é
  configurável: `WEB_PORT=8081 docker compose up -d` (na VPS a 8080 pertence
  ao `evolution_api`).
- A porta **5432 do host não é publicada** — de propósito, para não conflitar
  com o PostgreSQL da VPS. O Django fala com o banco pela rede interna do
  compose (`db:5432`).
- O servidor na imagem é o `runserver` (`python manage.py runserver
  0.0.0.0:8000`), porque **`gunicorn` não está no `requirements.txt`**. Para
  produção de verdade, adicione `gunicorn` ao requirements e troque o `CMD`.
- O build **não** roda `tailwind build` nem `collectstatic`: o CSS é
  versionado em `theme/static/css/dist/styles.css` (o CLI do Tailwind baixa
  binário da internet e quebraria o build offline) e o `collectstatic` exige
  `STATIC_ROOT`, que ainda não está definido em `core/settings.py`.
- Se `docker compose config` imprimir avisos `variable "bg"/"c" is not set`,
  é o `$` da `SECRET_KEY` do `.env` sendo lido como interpolação. É inofensivo:
  o container recebe a chave literal via `env_file`.

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
