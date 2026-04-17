from django.core.management.base import BaseCommand
from django.db import transaction

from apps.estoque.domain.tipos import FamiliaProduto
from apps.estoque.models.categoria import CategoriaProduto


class Command(BaseCommand):
    help = "Popula categorias otimizadas para industria moveleira (Tarugo)"

    CATEGORIAS_RAIZ = [
        ("Matéria-Prima", 0, FamiliaProduto.OUTROS),
        ("Ferragens", 1, FamiliaProduto.FERRAGENS),
        ("Fitas de Borda", 2, FamiliaProduto.FITAS_BORDA),
        ("Elétrica", 3, FamiliaProduto.OUTROS),
        ("Suprimentos", 4, FamiliaProduto.OUTROS),
        ("Vidros e Espelhos", 5, FamiliaProduto.VIDROS_ESPELHOS),
    ]

    SUBCATEGORIAS = {
        "Matéria-Prima": [
            ("MDF", FamiliaProduto.MDF),
            ("Compensado", FamiliaProduto.MDF),
            ("Outras Chapas", FamiliaProduto.MDF),
        ],
        "Ferragens": [
            ("Dobradiças", FamiliaProduto.FERRAGENS),
            ("Corrediças", FamiliaProduto.FERRAGENS),
            ("Trilhos", FamiliaProduto.FERRAGENS),
            ("Kits Deslizantes", FamiliaProduto.FERRAGENS),
            ("Sistemas de Abertura", FamiliaProduto.FERRAGENS),
            ("Puxadores e Botões", FamiliaProduto.FERRAGENS),
            ("Parafusos e Fixadores", FamiliaProduto.FERRAGENS),
            ("Dispositivos de Montagem", FamiliaProduto.FERRAGENS),
            ("Outras Ferragens", FamiliaProduto.FERRAGENS),
        ],
        "Fitas de Borda": [
            ("PVC", FamiliaProduto.FITAS_BORDA),
            ("ABS", FamiliaProduto.FITAS_BORDA),
            ("Madeira Natural", FamiliaProduto.FITAS_BORDA),
        ],
        "Suprimentos": [
            ("Embalagens e Proteção", FamiliaProduto.EMBALAGENS),
            ("Químicos e Insumos", FamiliaProduto.QUIMICOS_INSUMOS),
            ("EPIs e Ferramentas", FamiliaProduto.EPIS_FERRAMENTAS),
            ("Outros Suprimentos", FamiliaProduto.OUTROS),
        ],
        "Vidros e Espelhos": [
            ("Vidros", FamiliaProduto.VIDROS_ESPELHOS),
            ("Espelhos", FamiliaProduto.VIDROS_ESPELHOS),
        ],
    }

    @staticmethod
    def _upsert_categoria(*, nome, parent, ordem, familia):
        categoria, created = CategoriaProduto.objects.get_or_create(
            nome=nome,
            parent=parent,
            defaults={"ordem": ordem, "familia": familia},
        )

        updated = False
        if categoria.ordem != ordem:
            categoria.ordem = ordem
            updated = True
        if categoria.familia != familia:
            categoria.familia = familia
            updated = True

        if updated:
            categoria.save(update_fields=["ordem", "familia"])

        return categoria, created, updated

    def handle(self, *args, **options):
        self.stdout.write("Iniciando seed de categorias...")

        criadas = 0
        atualizadas = 0
        categorias_raiz = {}

        with transaction.atomic():
            for nome, ordem, familia in self.CATEGORIAS_RAIZ:
                categoria, created, updated = self._upsert_categoria(
                    nome=nome,
                    parent=None,
                    ordem=ordem,
                    familia=familia,
                )
                categorias_raiz[nome] = categoria
                criadas += int(created)
                atualizadas += int(updated)

            for parent_nome, subcategorias in self.SUBCATEGORIAS.items():
                parent = categorias_raiz[parent_nome]
                for ordem, (sub_nome, familia) in enumerate(subcategorias):
                    _, created, updated = self._upsert_categoria(
                        nome=sub_nome,
                        parent=parent,
                        ordem=ordem,
                        familia=familia,
                    )
                    criadas += int(created)
                    atualizadas += int(updated)

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed finalizado com sucesso. Criadas: {criadas}. Atualizadas: {atualizadas}."
            )
        )
