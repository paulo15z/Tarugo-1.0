from __future__ import annotations

from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LogoutView
from django.shortcuts import redirect, render
from django.urls import reverse


def _group_names(user) -> set[str]:
    if not user or not user.is_authenticated:
        return set()
    return {name.lower() for name in user.groups.values_list("name", flat=True)}


def _has_any_group(user, expected_groups: set[str]) -> bool:
    groups = _group_names(user)
    return bool(groups.intersection(expected_groups))


def _apps_disponiveis(user) -> list[dict[str, str]]:
    if not user or not user.is_authenticated:
        return []

    is_admin = bool(user.is_superuser or user.is_staff)

    apps: list[dict[str, str]] = []
    if is_admin or _has_any_group(user, {"gestao", "pcp", "estoque", "ti"}):
        apps.append(
            {
                "nome": "Estoque",
                "descricao": "Produtos, reservas e movimentacoes.",
                "url": reverse("estoque:lista_produtos"),
                "setor": "Almoxarifado",
            }
        )

    if is_admin or _has_any_group(user, {"gestao", "pcp", "ti"}):
        apps.append(
            {
                "nome": "PCP",
                "descricao": "Planejamento e controle da producao.",
                "url": reverse("pcp:index"),
                "setor": "PCP",
            }
        )

    if is_admin or _has_any_group(user, {"gestao", "pcp", "operador", "ti"}):
        apps.append(
            {
                "nome": "Bipagem",
                "descricao": "Operacao de leitura e andamento de pecas.",
                "url": reverse("bipagem:index"),
                "setor": "Producao",
            }
        )

    if is_admin or _has_any_group(user, {"gestao", "pcp", "ti"}):
        apps.append(
            {
                "nome": "Dinabox",
                "descricao": "Conexao com API Dinabox para consulta.",
                "url": reverse("integracoes:dinabox-conectar"),
                "setor": "Integracoes",
            }
        )

    return apps


def entrada(request):
    if request.user.is_authenticated:
        apps = _apps_disponiveis(request.user)
        if len(apps) == 1:
            return redirect(apps[0]["url"])
        return render(
            request,
            "core/entrada.html",
            {
                "apps_disponiveis": apps,
                "modo": "apps",
            },
        )

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            next_url = request.POST.get("next", "").strip()
            if next_url:
                return redirect(next_url)
            apps = _apps_disponiveis(request.user)
            if len(apps) == 1:
                return redirect(apps[0]["url"])
            return redirect("entrada")
    else:
        form = AuthenticationForm(request)

    return render(
        request,
        "core/entrada.html",
        {
            "form": form,
            "modo": "login",
            "default_redirect": settings.LOGIN_REDIRECT_URL,
        },
    )


class EntradaLogoutView(LogoutView):
    next_page = "/"

