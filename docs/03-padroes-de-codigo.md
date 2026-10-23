# 03 — Padrões de Código

Padrões obrigatórios para qualquer código escrito no Tallyora. Vêm dos requisitos não-funcionais do PRD (RNF01–RNF08).

## 1. PEP8 e formatação

- Todo `.py` adere à **PEP8**: 4 espaços de indentação, linhas até 79 caracteres, imports agrupados (stdlib, terceiros, Django/projeto) e duas linhas em branco entre definições de topo.
- **Aspas simples (`'`) por padrão** em strings Python (RNF02).
- Verificação planejada com `flake8` e `black --skip-string-normalization` (tarefa 6.1.1).

## 2. Idioma

| Onde | Idioma |
| :--- | :--- |
| Código-fonte (models, views, forms, urls, variáveis, comentários técnicos) | **Inglês** |
| Textos exibidos ao usuário (templates, labels, `help_text`, mensagens de erro/sucesso) | **Português do Brasil (pt-BR)** |

Nunca escrever nome de campo ou variável em português; nunca deixar texto visível ao usuário em inglês.

## 3. Nomenclatura

- Apps: `snake_case` (ex.: `goals_events`).
- Models: `PascalCase` singular (ex.: `EventPlan`, `DailyReminder`).
- Campos: `snake_case` descritivo, sem abreviações obscuras (`is_on_credit_card`, `monthly_contribution_value`).
- Choices: constantes em maiúsculas (`PENDING`, `PARTIAL`, `PAID`, `INCOME`, `EXPENSE`, `CREDIT_CARD_BILL`).
- Rotas: nomes com namespace da app (`core:dashboard`, `core:landing`), sempre nomeadas — nunca URL literal em template ou `redirect()`.

## 4. Recursos nativos do Django (RNF06)

Priorizar o que o framework já entrega:

- **Class-Based Views**: `ListView`, `CreateView`, `UpdateView`, `DeleteView`, `TemplateView`, `FormView`, `View`.
- **Django Forms / ModelForm** para toda entrada de dados — validação e widgets ficam no form, não na view.
- **Django Template Language (DTL)** para renderização, com `{% extends %}` e `{% include %}` para reaproveitamento.
- **ORM** para consultas. Sem SQL cru sem necessidade justificada.
- **View genérica antes de função**: só usar view de função ou `View` crua quando a genérica não cobrir (ex.: ação de "Atualizar Cotações", que dispara um serviço e redireciona).

## 5. Zero over-engineering (RNF01)

- Sem camada extra de abstração "por precaução".
- Sem microserviços, SPA, Celery, Redis, filas ou cache distribuído nas sprints iniciais.
- Lógica de negócio complexa que não cabe em um model vai para `<app>/services.py` como classe de serviço — não para dentro da view.
- Não criar campo, model ou tabela que o PRD não pede.

## 6. `BaseModel` obrigatório (RNF05)

**Todo** model do sistema herda de um model abstrato `BaseModel` com:

- `created_at` — `DateTimeField(auto_now_add=True)`
- `updated_at` — `DateTimeField(auto_now=True)`

Previsto em `core/models.py` (tarefa 1.1.5). Nenhum model novo deve ser criado sem essa herança.

## 7. Signals isolados (RNF07)

Qualquer `post_save`, `pre_save` e afins reside **exclusivamente** em `<app>/signals.py`, e o módulo é registrado no método `ready()` do `<app>/apps.py`:

```python
class AccountsConfig(AppConfig):
    name = 'accounts'

    def ready(self):
        from . import signals  # noqa: F401
```

Signal dentro de `models.py` ou `views.py` é proibido.

## 8. Isolamento de dados por usuário (RNF08)

Tallyora é multi-tenant lógico: cada usuário só enxerga os próprios dados financeiros. Toda view que lista ou altera dados deve:

1. Herdar de `LoginRequiredMixin`.
2. Filtrar o queryset por usuário:

```python
class GoalBoxListView(LoginRequiredMixin, ListView):
    model = GoalBox

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)
```

Em `CreateView`, o `user` vem de `form_valid()` (`obj.user = self.request.user`) — nunca de campo editável no formulário. Em `UpdateView`/`DeleteView`, o filtro no `get_queryset()` é o que impede um usuário de editar o registro do outro.

## 9. Segredos e configuração

- `SECRET_KEY`, credenciais de banco e chaves de API **nunca** ficam no código nem no `settings.py` em produção: vêm de `.env` lido com `python-dotenv`.
- `.env` não é versionado.
- `DEBUG` e `ALLOWED_HOSTS` também são definidos por ambiente.

## 10. Testes

- Testes ficam no `tests.py` da própria app.
- Obrigatório cobrir as regras de cálculo: não-duplicidade da fatura, descontos CLT, rateio de caixinhas e saldo pendente de eventos (tarefas 6.2.1–6.2.3).
- Meta do PRD: ≥ 80% de cobertura nas funções de cálculo financeiro.

## Checklist antes de abrir um PR / entregar uma tarefa

- [ ] Arquivo passa em `flake8`, aspas simples em todo o `.py`.
- [ ] Nenhuma string em inglês visível ao usuário; nenhum identificador em português.
- [ ] Model herda de `BaseModel`; migration gerada.
- [ ] View com `LoginRequiredMixin` e `get_queryset()` filtrando por `request.user`.
- [ ] Signal (se houver) em `signals.py`, registrado em `apps.py`.
- [ ] Regra de cálculo fora da view (model ou `services.py`) e coberta por teste.
