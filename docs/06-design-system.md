# 06 — Design System

Padrão visual obrigatório para todas as telas. Definido no PRD (seção 9). Ainda não há `templates/` nem `static/` no projeto — este documento é a especificação que a implementação deve seguir.

## 1. Estrutura de templates

Toda tela herda de um template mestre:

| Template | Uso |
| :--- | :--- |
| `templates/base_public.html` | Landing Page, cadastro, login, recuperação de senha (visitante) |
| `templates/base.html` | Área autenticada (sidebar + conteúdo + mensagens) |
| `templates/partials/` | Componentes reutilizáveis: `_card_kpi.html`, `_empty_state.html`, `_modal_confirm_delete.html`, `_form_field.html` (label + widget + ajuda + erros) |

Stack de apresentação: **DTL + TailwindCSS + Chart.js** (apenas gráficos de pizza/rosca do dashboard e da carteira). Nenhum framework JS de SPA.

O Tailwind é **compilado localmente** com `django-tailwind` (app `theme/`) e o CLI standalone — **não** há CDN. Isso significa que classe utilitária nova só aparece na página depois do build:

```bash
python manage.py tailwind build     # obrigatório a cada mudança de template
```

O CSS final fica em `theme/static/css/dist/styles.css` e é **versionado** (runtime depende dele). Os templates base carregam o arquivo com `{% tailwind_css %}`. O fonte é `theme/static_src/src/styles.css`, que importa o Tailwind e escaneia `templates/`, `*/templates/` e arquivos `.py`/`.js` em busca de classes.


## 2. Tema

Dark mode nativo — não é opção, é o padrão do produto. Fundo escuro profundo, cards com *glassmorphism* sutil.

## 3. Paleta de cores

### Superfícies

| Papel | Classe | Hex |
| :--- | :--- | :--- |
| Fundo da aplicação | `bg-slate-950` | `#020617` |
| Cards e containers | `bg-slate-900/80` + `border-slate-800` + `backdrop-blur-md` | `#0f172a` |
| Inputs e tabelas secundárias | `bg-slate-800/60` | `#1e293b` |

### Identidade e acentos

- Gradiente de destaque: `bg-gradient-to-r from-emerald-500 via-teal-500 to-cyan-500`
- Primária sólida: `emerald-500` (`#10b981`) — ações principais e indicadores positivos
- Secundária / acento: `indigo-500` (`#6366f1`) e `cyan-400` (`#22d3ee`) — gráficos, caixinhas, investimentos

### Cores semânticas financeiras

| Significado | Texto | Badge |
| :--- | :--- | :--- |
| Receita / lucro / quitado | `text-emerald-400` | `bg-emerald-500/10 text-emerald-400 border border-emerald-500/20` |
| Despesa / prejuízo / pendente | `text-rose-400` | `bg-rose-500/10 text-rose-400 border border-rose-500/20` |
| Fatura de cartão / alerta / parcial | `text-amber-400` | `bg-amber-500/10 text-amber-400 border border-amber-500/20` |
| Caixinhas e investimentos | `text-cyan-400` | `bg-cyan-500/10 text-cyan-400 border border-cyan-500/20` |

### Textos

| Papel | Classe |
| :--- | :--- |
| Título principal | `text-slate-100` |
| Texto secundário / labels | `text-slate-400` |
| Desabilitado / muted | `text-slate-500` |

## 4. Tipografia

- **UI e textos:** `Inter` ou `Plus Jakarta Sans`, importada via Google Fonts no `base.html`.
- **Valores monetários e percentuais:** obrigatório `tabular-nums` em todo `R$` e `%`, para alinhamento vertical em tabelas e cards.

## 5. Componentes

### Botão primário (CTA / salvar)

```html
<button class="inline-flex items-center justify-center px-5 py-2.5 rounded-xl font-semibold text-sm text-slate-950 bg-gradient-to-r from-emerald-400 to-cyan-400 hover:from-emerald-300 hover:to-cyan-300 transition-all duration-200 shadow-lg shadow-emerald-500/20">
  Salvar Registro
</button>
```

### Botão secundário (cancelar / auxiliar)

```html
<button class="inline-flex items-center justify-center px-4 py-2.5 rounded-xl font-medium text-sm text-slate-300 bg-slate-800 hover:bg-slate-700 border border-slate-700 transition-colors">
  Cancelar
</button>
```

### Botão de perigo (excluir)

```html
<button class="inline-flex items-center justify-center px-4 py-2.5 rounded-xl font-medium text-sm text-rose-400 bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/20 transition-colors">
  Excluir
</button>
```

### Inputs e selects

Estilizados pelos `widgets` do Django Form — o componente base é:

```html
<input class="w-full px-4 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition-all text-sm" />
```

### Card de indicador (KPI do dashboard)

```html
<div class="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 backdrop-blur-md shadow-xl flex flex-col justify-between">
  <span class="text-xs font-medium uppercase tracking-wider text-slate-400">Saldo Livre no Mês</span>
  <span class="text-2xl font-bold text-emerald-400 tabular-nums mt-2">R$ 1.850,00</span>
</div>
```

### Barra de progresso (caixinhas)

```html
<div class="h-1.5 rounded-full bg-slate-800 overflow-hidden" role="progressbar"
     aria-valuenow="25" aria-valuemin="0" aria-valuemax="100">
  <div class="h-full bg-gradient-to-r from-emerald-400 to-cyan-400" style="width: 25%"></div>
</div>
```

Largura em `style` inline (o valor vem do model, não é classe utilitária) e `aria-valuenow` sempre preenchido.

### Aviso de fatura (âmbar)

`bg-amber-500/5` + `border-amber-500/30` + texto `text-amber-300`. Usado para explicar que itens marcados como cartão compõem a fatura e **não** são descontados duas vezes, e para destacar o campo `is_on_credit_card` no formulário. Ciano (`bg-cyan-500/5`, `border-cyan-500/20`) é o par neutro para notas explicativas sem alerta.

### Cards de resumo do evento

Cinco KPIs em `lg:grid-cols-5` (partial `_card_kpi` com `tone`): Custo Total do Evento, Total Já Pago (`positive`), Falta Pagar (`warning`), Total Já Guardado (`info`) e Quanto Falta Guardar (`warning`). Sempre `tabular-nums` e `R$ 0,00`.

### Badge de status do fornecedor

`Pendente` (âmbar), `Parcial` (ciano), `Pago` (esmeralda). Derivado do valor pago, nunca digitado — a mesma pill usada nas categorias.

### Gráfico de rosca (carteira)

Chart.js 4.4.6 **local** (`theme/static/js/chart.umd.min.js`, sem CDN), dois anéis: divisão atual (interno) e meta por classe (externo). Os dados chegam por `{{ chart_data|json_script:"portfolio-chart-data" }}` — nunca por interpolação inline no script. Canvas `id="portfolio-chart"` com altura fixa (`h-72`).

### Badge Aportar / Aguardar

Compara o peso atual da classe com a meta: `Aportar` (abaixo da meta, esmeralda) ou `Aguardar` (na meta ou acima, slate). É a leitura de onde colocar o próximo aporte.

### Aviso de metas incompletas

Faixa âmbar (`bg-amber-500/5` + `border-amber-500/30`) quando a soma das metas não fecha 100%, mostrando quanto falta; o valor acompanha a digitação.

## 6. Layout da área logada

- **Sidebar fixa no desktop** (`w-64`, `bg-slate-900 border-r border-slate-800`): logo Tallyora em gradiente, links com ícone + texto e estado ativo destacado, botão de logout no rodapé.
- **Itens de navegação:** Dashboard, Meu Perfil & Salário, Transações & Fatura (`transactions:list`), Caixinhas & Eventos (`goals:list`), Investimentos P3X e Lembretes do Dia (estes dois ainda como "em breve", `div` não clicável, até as sprints 4 e 5).
- **Área de conteúdo:** `max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8`, com grids responsivos `grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6`.
- **Sidebar responsiva:** recolhe em telas pequenas; no mobile a navegação vira menu colapsável.
- **Mensagens do sistema:** bloco de alerta no topo do `base.html` usando `django.contrib.messages` (sucesso, erro, aviso).

## 7. Regras de interface

- **Todo texto visível em pt-BR.** Rótulo, placeholder, mensagem de erro, estado vazio, título de página e nome de botão.
- Valores monetários sempre formatados como `R$ 1.850,00` (padrão brasileiro: vírgula decimal, ponto de milhar) e com `tabular-nums`.
- Estados vazios sempre com texto explicativo e ação sugerida (`_empty_state.html`) — nunca tela em branco.
- Exclusão sempre com confirmação: página dedicada `<app>/*_confirm_delete.html` (padrão das listas de contas, categorias, transações, despesas fixas e caixinhas) ou `_modal_confirm_delete.html` quando a exclusão acontece dentro de outra tela, como os descontos de folha no perfil. Sempre via `POST` com `csrf_token`.
- Formulários de transação e despesa fixa usam `_form_field.html` e destacam o campo de cartão com o painel âmbar.
- O card `Saldo Livre (O que sobra no mês)` é o elemento de maior destaque do dashboard.
- Indicadores de aporte na carteira usam badge: `Aportar` (abaixo da meta) ou `Aguardar` (na meta ou acima).
