from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import BankAccountForm
from .models import BankAccount

LIST_URL = reverse_lazy('accounts:list')


class AccountListView(LoginRequiredMixin, ListView):
    """List the bank accounts of the logged user."""

    model = BankAccount
    template_name = 'accounts/account_list.html'
    context_object_name = 'accounts'
    paginate_by = 10

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)


class AccountCreateView(LoginRequiredMixin, CreateView):
    """Create a bank account for the logged user."""

    model = BankAccount
    form_class = BankAccountForm
    template_name = 'accounts/account_form.html'
    success_url = LIST_URL

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, 'Conta cadastrada com sucesso.')
        return super().form_valid(form)


class AccountUpdateView(LoginRequiredMixin, UpdateView):
    """Update a bank account of the logged user."""

    model = BankAccount
    form_class = BankAccountForm
    template_name = 'accounts/account_form.html'
    success_url = LIST_URL

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, 'Conta atualizada com sucesso.')
        return super().form_valid(form)


class AccountDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a bank account of the logged user."""

    model = BankAccount
    template_name = 'accounts/account_confirm_delete.html'
    success_url = LIST_URL

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, 'Conta removida com sucesso.')
        return super().form_valid(form)
