from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = "Cria usuarios iniciais (2 operadores, 1 PCP, 1 gestao) de forma idempotente."

    GROUP_OPERATOR = "Operador Maquina"
    GROUP_PCP = "PCP"
    GROUP_GESTAO = "Gestao"
    GROUP_TI = "TI"

    USER_SPECS = [
        {
            "username": "operador.maquina1",
            "first_name": "Operador",
            "last_name": "Maquina 1",
            "email": "operador1@tarugo.local",
            "group": GROUP_OPERATOR,
            "is_staff": False,
        },
        {
            "username": "operador.maquina2",
            "first_name": "Operador",
            "last_name": "Maquina 2",
            "email": "operador2@tarugo.local",
            "group": GROUP_OPERATOR,
            "is_staff": False,
        },
        {
            "username": "pcp",
            "first_name": "Usuario",
            "last_name": "PCP",
            "email": "pcp@tarugo.local",
            "group": GROUP_PCP,
            "is_staff": False,
        },
        {
            "username": "gestao",
            "first_name": "Usuario",
            "last_name": "Gestao",
            "email": "gestao@tarugo.local",
            "group": GROUP_GESTAO,
            "is_staff": True,
        },
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            "--default-password",
            default="Trocar123!",
            help="Senha padrao para usuarios novos (default: Trocar123!).",
        )
        parser.add_argument(
            "--reset-passwords",
            action="store_true",
            help="Se informado, redefine a senha de usuarios ja existentes.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        default_password = options["default_password"]
        reset_passwords = options["reset_passwords"]

        required_groups = {self.GROUP_OPERATOR, self.GROUP_PCP, self.GROUP_GESTAO, self.GROUP_TI}
        for group_name in required_groups:
            Group.objects.get_or_create(name=group_name)

        created = 0
        updated = 0
        passwords_reset = 0

        for spec in self.USER_SPECS:
            group = Group.objects.get(name=spec["group"])
            defaults = {
                "first_name": spec["first_name"],
                "last_name": spec["last_name"],
                "email": spec["email"],
                "is_staff": spec["is_staff"],
                "is_active": True,
            }

            user, was_created = User.objects.get_or_create(
                username=spec["username"],
                defaults=defaults,
            )

            if was_created:
                user.set_password(default_password)
                user.save(update_fields=["password"])
                created += 1
                self.stdout.write(self.style.SUCCESS(f"[CRIADO] Usuario: {user.username}"))
            else:
                dirty_fields = []
                for field, value in defaults.items():
                    if getattr(user, field) != value:
                        setattr(user, field, value)
                        dirty_fields.append(field)

                if dirty_fields:
                    user.save(update_fields=dirty_fields)
                    updated += 1
                    self.stdout.write(f"[ATUALIZADO] Usuario: {user.username} ({', '.join(dirty_fields)})")
                else:
                    self.stdout.write(f"[OK] Usuario ja existe: {user.username}")

                if reset_passwords:
                    user.set_password(default_password)
                    user.save(update_fields=["password"])
                    passwords_reset += 1
                    self.stdout.write(f"[SENHA] Senha redefinida para: {user.username}")

            user.groups.add(group)

        self.stdout.write(
            self.style.SUCCESS(
                "Seed de usuarios concluido. "
                f"Criados: {created}. Atualizados: {updated}. Senhas redefinidas: {passwords_reset}."
            )
        )
