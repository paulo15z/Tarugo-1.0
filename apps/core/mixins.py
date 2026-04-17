from __future__ import annotations

from typing import Iterable

from django.contrib import messages
from django.contrib.auth.mixins import AccessMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from rest_framework.permissions import BasePermission


class EstoquePermissionMixin(AccessMixin):
    login_url = 'login'
    redirect_field_name = 'next'
    allowed_groups: Iterable[str] | None = ('Almoxarife', 'Gerente', 'PCP')
    permission_denied_message = 'Acesso restrito ao módulo de estoque.'
    denied_redirect_url = 'estoque-dashboard'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if self.allowed_groups:
            if not request.user.groups.filter(name__in=self.allowed_groups).exists():
                messages.warning(request, self.permission_denied_message)
                return redirect(self.get_denied_redirect_url())

        return super().dispatch(request, *args, **kwargs)

    def get_denied_redirect_url(self):
        return reverse_lazy(self.denied_redirect_url)


class EstoqueGroupPermission(BasePermission):
    required_groups: Iterable[str] | None = None

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        required = getattr(view, 'required_groups', self.required_groups)
        if not required:
            return True

        return request.user.groups.filter(name__in=required).exists()
