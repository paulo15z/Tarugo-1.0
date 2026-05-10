from django.core.management.base import BaseCommand

from apps.integracoes.service_accounts import get_integration_service_user


class Command(BaseCommand):
    help = "Cria ou valida o usuario tecnico interno usado por integracoes externas."

    def handle(self, *args, **options):
        user = get_integration_service_user()
        if user is None:
            self.stdout.write(self.style.WARNING("INTEGRACOES_SERVICE_USERNAME vazio; nenhum usuario criado."))
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Usuario tecnico de integracoes pronto: {user.username} (id={user.pk})"
            )
        )
