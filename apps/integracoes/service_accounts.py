from __future__ import annotations

from django.conf import settings
from django.contrib.auth import get_user_model


def get_integration_service_user():
    """
    Retorna o usuario tecnico interno usado para acoes automatizadas.

    Ele nao substitui credenciais do provedor externo. Serve para auditoria
    local quando um conector executa rotinas sem operador humano.
    """

    username = str(getattr(settings, "INTEGRACOES_SERVICE_USERNAME", "integracoes-api") or "").strip()
    if not username:
        return None

    User = get_user_model()
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            "is_active": True,
            "is_staff": False,
        },
    )
    if created:
        user.set_unusable_password()
        user.save(update_fields=["password"])
    return user
