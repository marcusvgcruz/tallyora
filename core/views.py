from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views.generic import TemplateView


class LandingPageView(TemplateView):
    """Public landing page; authenticated users go to the dashboard."""

    template_name = 'core/landing.html'

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('core:dashboard')
        return super().get(request, *args, **kwargs)


class DashboardView(LoginRequiredMixin, TemplateView):
    """Temporary dashboard placeholder (data arrives in Sprint 5)."""

    template_name = 'core/dashboard.html'
