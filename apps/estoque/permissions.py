# apps/estoque/permissions.py
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


GRUPOS_MOVIMENTACAO = {
    "Operador Maquina",
    "PCP",
    "TI",
    "estoque.02",
    "estoque.03",
}

GRUPOS_CADASTRO = {
    "PCP",
    "TI",
    "estoque.03",
}


def _usuario_tem_grupo(user, grupos: set[str]) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=grupos).exists()


def pode_movimentar_estoque(user) -> bool:
    return _usuario_tem_grupo(user, GRUPOS_MOVIMENTACAO)


def pode_cadastrar_estoque(user) -> bool:
    return _usuario_tem_grupo(user, GRUPOS_CADASTRO)


def _expandir_grupos(*grupos) -> set[str]:
    expandido: set[str] = set()
    for grupo in grupos:
        if grupo == "estoque.movimentar":
            expandido.update(GRUPOS_MOVIMENTACAO)
        elif grupo == "estoque.cadastrar":
            expandido.update(GRUPOS_CADASTRO)
        else:
            expandido.add(grupo)
    return expandido


def grupo_requerido(*grupos):
    """
    Decorator que verifica se o usuário pertence a pelo menos um dos grupos.
    Uso: @grupo_requerido('estoque.02', 'estoque.03')
    """
    grupos_permitidos = _expandir_grupos(*grupos)

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')

            # Superusuário passa sempre
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            grupos_do_usuario = request.user.groups.values_list('name', flat=True)
            if any(g in grupos_do_usuario for g in grupos_permitidos):
                return view_func(request, *args, **kwargs)

            messages.error(request, 'Você não tem permissão para acessar esta página.')
            return redirect('estoque:lista_produtos')

        return wrapper
    return decorator
