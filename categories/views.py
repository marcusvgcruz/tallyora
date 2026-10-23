from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import CategoryForm
from .models import Category

LIST_URL = reverse_lazy('categories:list')


class CategoryListView(LoginRequiredMixin, ListView):
    """List the categories of the logged user."""

    model = Category
    template_name = 'categories/category_list.html'
    context_object_name = 'categories'

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)


class CategoryCreateView(LoginRequiredMixin, CreateView):
    """Create a category for the logged user."""

    model = Category
    form_class = CategoryForm
    template_name = 'categories/category_form.html'
    success_url = LIST_URL

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, 'Categoria criada com sucesso.')
        return super().form_valid(form)


class CategoryUpdateView(LoginRequiredMixin, UpdateView):
    """Update a category of the logged user."""

    model = Category
    form_class = CategoryForm
    template_name = 'categories/category_form.html'
    success_url = LIST_URL

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Categoria atualizada com sucesso.')
        return super().form_valid(form)


class CategoryDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a category of the logged user."""

    model = Category
    template_name = 'categories/category_confirm_delete.html'
    success_url = LIST_URL

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, 'Categoria removida com sucesso.')
        return super().form_valid(form)
