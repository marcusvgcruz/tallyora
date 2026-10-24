from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, UpdateView

from .forms import PayrollDeductionForm, UserProfileForm
from .models import PayrollDeduction, UserProfile

PROFILE_URL = reverse_lazy('profiles:profile')


class ProfileConfigView(LoginRequiredMixin, UpdateView):
    """Show and update the financial profile of the logged user."""

    model = UserProfile
    form_class = UserProfileForm
    template_name = 'profiles/profile_detail.html'
    success_url = PROFILE_URL

    def get_object(self, queryset=None):
        profile, _ = UserProfile.objects.get_or_create(user=self.request.user)
        return profile

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = self.object
        context['deduction_form'] = PayrollDeductionForm()
        context['deductions'] = self.request.user.payroll_deductions.all()
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Perfil atualizado com sucesso.')
        return super().form_valid(form)


class PayrollDeductionCreateView(LoginRequiredMixin, CreateView):
    """Register a payroll deduction for the logged user.

    The deduction form lives on the profile page, so the view only
    processes the POST and returns to the profile.
    """

    model = PayrollDeduction
    form_class = PayrollDeductionForm
    success_url = PROFILE_URL

    def get(self, request, *args, **kwargs):
        return HttpResponseRedirect(self.success_url)

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, 'Desconto cadastrado com sucesso.')
        return super().form_valid(form)

    def form_invalid(self, form):
        errors = ' '.join(
            str(error)
            for error_list in form.errors.values()
            for error in error_list
        )
        messages.error(
            self.request,
            f'Não foi possível cadastrar o desconto. {errors}'.strip(),
        )
        return HttpResponseRedirect(self.success_url)


class PayrollDeductionDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a payroll deduction of the logged user.

    Deletion is POST-only and returns to the profile page.
    """

    model = PayrollDeduction
    success_url = PROFILE_URL

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def get(self, request, *args, **kwargs):
        return HttpResponseRedirect(self.success_url)

    def form_valid(self, form):
        messages.success(self.request, 'Desconto removido com sucesso.')
        return super().form_valid(form)
