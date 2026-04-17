from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = "Cria grupos iniciais de acesso (idempotente)."

    DEFAULT_GROUPS = [
        "Operador Maquina",
        "PCP",
        "Gestao",
        "TI",
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            "--groups",
            nargs="+",
            default=self.DEFAULT_GROUPS,
            help="Lista de grupos a criar/garantir.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        groups = options["groups"] or self.DEFAULT_GROUPS
        created = 0

        for group_name in groups:
            _, was_created = Group.objects.get_or_create(name=group_name)
            created += int(was_created)
            if was_created:
                self.stdout.write(self.style.SUCCESS(f"[CRIADO] Grupo: {group_name}"))
            else:
                self.stdout.write(f"[OK] Grupo ja existe: {group_name}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed de grupos concluido. Criados: {created}. Existentes: {len(groups) - created}."
            )
        )
