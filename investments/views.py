"""Views for the investment portfolio."""

from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, TemplateView
from django.views.generic.edit import UpdateView

from core.models import ZERO, to_money

from .forms import AllocationTargetFormSet, InvestmentAssetForm
from .models import AssetAllocationTarget, AssetClass, InvestmentAsset
from .services import (
    ACTION_BUY,
    ACTION_WAIT,
    QuoteUpdaterService,
    asset_weights,
)

ONE_HUNDRED = Decimal('100.00')
PORTFOLIO_URL = reverse_lazy('investments:portfolio')
BADGE_BUY = ACTION_BUY
BADGE_WAIT = ACTION_WAIT
FORMSET_PREFIX = 'targets'
TARGETS_TOTAL_LIMIT = 'A soma das metas por classe não pode passar de 100%.'
TARGETS_DUPLICATED = 'Cada classe de ativo pode ter apenas uma meta.'
TARGETS_INVALID = 'Não foi possível salvar as metas. Revise os valores.'


def _percentage(part, whole):
    """Percentage of ``part`` over ``whole``, zero when ``whole`` is zero."""
    if whole <= ZERO:
        return ZERO
    return to_money(part / whole * ONE_HUNDRED)


def _user_targets(user):
    """Queryset with the allocation targets of ``user``."""
    return AssetAllocationTarget.objects.filter(user=user)


def annotate_weights(assets):
    """Attach the weight inside the class to each asset instance.

    Templates read the values as plain attributes, and the returned map
    keeps the same rows available for the tests and for the context.
    """
    rows = asset_weights(assets)
    for asset in assets:
        row = rows[asset.pk]
        asset.class_weight = row['weight']
        asset.class_weight_target = row['target']
        asset.class_weight_action = row['action']
    return rows


class PortfolioDashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard of the user portfolio, with allocation by class."""

    template_name = 'investments/portfolio.html'

    def get_queryset(self):
        """Assets of the logged user, ordered by class and ticker."""
        return InvestmentAsset.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        assets = list(self.get_queryset())
        targets = AssetAllocationTarget.targets_by_class(self.request.user)
        weights = annotate_weights(assets)

        total_value = to_money(
            sum((asset.current_total_value for asset in assets), ZERO)
        )
        total_invested = to_money(
            sum((asset.total_invested for asset in assets), ZERO)
        )
        profit_loss = to_money(total_value - total_invested)
        profit_loss_percentage = _percentage(profit_loss, total_invested)

        assets_by_class = {}
        for asset in assets:
            assets_by_class.setdefault(asset.asset_class, []).append(asset)

        class_summary = self.build_class_summary(
            assets_by_class,
            targets,
            total_value,
        )
        allocation_total = AssetAllocationTarget.total_percentage(
            self.request.user
        )
        quotes = [
            asset.last_quote_update
            for asset in assets
            if asset.last_quote_update is not None
        ]

        context.update(
            {
                'assets': assets,
                'assets_by_class': assets_by_class,
                'class_summary': class_summary,
                'asset_weights': weights,
                'total_value': total_value,
                'total_invested': total_invested,
                'profit_loss_amount': profit_loss,
                'profit_loss_percentage': profit_loss_percentage,
                'chart_data': {
                    'labels': [row['label'] for row in class_summary],
                    'current': [
                        float(row['current_percentage'])
                        for row in class_summary
                    ],
                    'target': [
                        float(row['target_percentage'])
                        for row in class_summary
                    ],
                },
                'allocation_targets': _user_targets(self.request.user),
                'allocation_formset': AllocationTargetFormSet(
                    queryset=_user_targets(self.request.user),
                    prefix=FORMSET_PREFIX,
                    user=self.request.user,
                ),
                'allocation_total': allocation_total,
                'allocation_missing': max(
                    to_money(ONE_HUNDRED - allocation_total),
                    ZERO,
                ),
                'last_quote_update': max(quotes) if quotes else None,
                'title': 'Carteira de Investimentos',
            }
        )
        return context

    @staticmethod
    def build_class_summary(assets_by_class, targets, total_value):
        """Compare the current allocation of each class with its target."""
        summary = []
        for value, label in AssetClass.choices:
            class_assets = assets_by_class.get(value) or []
            target_percentage = to_money(targets.get(value, ZERO))
            if not class_assets and target_percentage <= ZERO:
                continue
            current_value = to_money(
                sum(
                    (asset.current_total_value for asset in class_assets),
                    ZERO,
                )
            )
            current_percentage = _percentage(current_value, total_value)
            summary.append(
                {
                    'asset_class': value,
                    'label': label,
                    'current_value': current_value,
                    'current_percentage': current_percentage,
                    'target_percentage': target_percentage,
                    'diff_percentage': to_money(
                        current_percentage - target_percentage
                    ),
                    'badge': (
                        BADGE_BUY
                        if current_percentage < target_percentage
                        else BADGE_WAIT
                    ),
                }
            )
        return summary


class AssetCreateView(LoginRequiredMixin, CreateView):
    """Create an asset for the logged user."""

    model = InvestmentAsset
    form_class = InvestmentAssetForm
    template_name = 'investments/asset_form.html'
    success_url = PORTFOLIO_URL

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Novo ativo'
        context['submit_label'] = 'Adicionar à carteira'
        return context

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, 'Ativo adicionado à carteira.')
        return super().form_valid(form)


class AssetUpdateView(LoginRequiredMixin, UpdateView):
    """Update an asset of the logged user."""

    model = InvestmentAsset
    form_class = InvestmentAssetForm
    template_name = 'investments/asset_form.html'
    success_url = PORTFOLIO_URL

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar ativo'
        context['submit_label'] = 'Salvar alterações'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Ativo atualizado com sucesso.')
        return super().form_valid(form)


class AssetDeleteView(LoginRequiredMixin, DeleteView):
    """Delete an asset of the logged user."""

    model = InvestmentAsset
    template_name = 'investments/asset_confirm_delete.html'
    success_url = PORTFOLIO_URL

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Excluir ativo'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Ativo removido da carteira.')
        return super().form_valid(form)


class RefreshQuotesView(LoginRequiredMixin, View):
    """Refresh the quotes of the user assets in one batch."""

    def post(self, request, *args, **kwargs):
        result = QuoteUpdaterService(request.user).update_user_assets()
        updated = len(result['updated'])
        failed = len(result['failed'])
        skipped = len(result['skipped'])
        if updated:
            message = f'{updated} cotação(ões) atualizada(s)'
        else:
            message = 'Nenhuma cotação foi atualizada'
        if skipped:
            message += f', {skipped} ativo(s) sem cotação automática'
        if failed:
            tickers = ', '.join(item['ticker'] for item in result['failed'])
            message += f', {failed} falha(s): {tickers}'
            messages.warning(request, message + '.')
        else:
            messages.success(request, message + '.')
        return redirect(PORTFOLIO_URL)

    def get(self, request, *args, **kwargs):
        """Keep the route friendly: a GET just returns to the portfolio."""
        return redirect(PORTFOLIO_URL)


class AllocationTargetUpdateView(LoginRequiredMixin, View):
    """Save the allocation targets posted by the portfolio formset."""

    success_url = PORTFOLIO_URL
    formset_class = AllocationTargetFormSet

    def post(self, request, *args, **kwargs):
        formset = self.formset_class(
            request.POST,
            queryset=_user_targets(request.user),
            prefix=FORMSET_PREFIX,
            user=request.user,
        )
        if not formset.is_valid():
            messages.error(request, TARGETS_INVALID)
            return redirect(self.success_url)

        rows = self.valid_rows(formset)
        classes = [
            row['asset_class']
            for row in rows
            if row['target_percentage'] is not None
        ]
        if len(classes) != len(set(classes)):
            messages.error(request, TARGETS_DUPLICATED)
            return redirect(self.success_url)

        total = to_money(
            sum(
                (
                    row['target_percentage']
                    for row in rows
                    if row['target_percentage'] is not None
                ),
                ZERO,
            )
        )
        if total > ONE_HUNDRED:
            messages.error(request, TARGETS_TOTAL_LIMIT)
            return redirect(self.success_url)

        self.save_formset(formset, request.user)
        messages.success(request, 'Metas por classe atualizadas.')
        return redirect(self.success_url)

    @staticmethod
    def valid_rows(formset):
        """Rows of the formset that were filled and not marked to delete."""
        rows = []
        for form in formset.forms:
            data = getattr(form, 'cleaned_data', None)
            if not data or data.get('DELETE'):
                continue
            if not data.get('asset_class'):
                continue
            rows.append(
                {
                    'asset_class': data['asset_class'],
                    'target_percentage': data.get('target_percentage'),
                }
            )
        return rows

    @staticmethod
    def save_formset(formset, user):
        """Persist the formset linking the logged user to each new row."""
        for instance in formset.save(commit=False):
            instance.user = user
            instance.save()
        for instance in formset.deleted_objects:
            instance.delete()
