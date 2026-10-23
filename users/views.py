from django.contrib.auth import authenticate, login
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.views.generic import CreateView

from .forms import EmailAuthenticationForm, UserRegistrationForm


class UserRegisterView(CreateView):
    """Create a new account and log the user in right after it."""

    form_class = UserRegistrationForm
    template_name = 'users/register.html'
    success_url = reverse_lazy('core:dashboard')

    def form_valid(self, form):
        response = super().form_valid(form)
        user = authenticate(
            self.request,
            username=form.cleaned_data['email'],
            password=form.cleaned_data['password1'],
        )
        if user is not None:
            login(self.request, user)
        return response


class UserLoginView(LoginView):
    """Authenticate the user with e-mail and password."""

    form_class = EmailAuthenticationForm
    template_name = 'users/login.html'
    redirect_authenticated_user = True


class UserLogoutView(LogoutView):
    """End the current session and return to the public landing page."""

    next_page = reverse_lazy('core:landing')
