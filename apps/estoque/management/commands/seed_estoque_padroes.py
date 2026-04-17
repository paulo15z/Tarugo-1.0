from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from apps.estoque.models.categoria import CategoriaProduto
from apps.estoque.models.produto import Produto
from apps.estoque.services.produto_service import ProdutoService


class Command(BaseCommand):
    help = "Injeta padrões de mercado (Duratex, Arauco, Leo) nas espessuras 6, 15, 18 e 25mm"

    MARCAS_PADROES = {
        "Duratex": ["Branco Diamante", "Carvalho Malva", "Gianduia", "Preto Silk"],
        "Arauco": ["Branco Supremo", "Noce Oro", "Grafite", "Louro Freijó"],
        "Leo Madeiras": ["Branco TX", "Nogueira Sevilha", "Cinza Sagrado"],
    }
    ESPESSURAS_MM = [6, 15, 18, 25]

    @staticmethod
    def _build_sku(marca, padrao, espessura):
        return slugify(f"{marca}-{padrao}-{espessura}mm").upper()

    @staticmethod
    def _produto_defaults(marca, padrao, espessura, categoria):
        return {
            "nome": f"MDF {espessura}mm {marca} {padrao}",
            "categoria": categoria,
            "unidade_medida": "m2",
            "quantidade": 50,
            "estoque_minimo": 10,
            "atributos_especificos": {
                "marca": marca,
                "padrao": padrao,
                "espessura": espessura,
            },
        }

    def handle(self, *args, **options):
        self.stdout.write("Garantindo categorias base...")
        call_command("seed_categorias", stdout=self.stdout)

        categoria_mdf = CategoriaProduto.objects.get(
            nome="MDF",
            parent__nome="Matéria-Prima",
        )

        criados = 0
        atualizados = 0
        fitas_criadas = 0

        with transaction.atomic():
            for marca, padroes in self.MARCAS_PADROES.items():
                for padrao in padroes:
                    produto_ref = None
                    for espessura in self.ESPESSURAS_MM:
                        sku = self._build_sku(marca, padrao, espessura)
                        defaults = self._produto_defaults(marca, padrao, espessura, categoria_mdf)

                        produto, created = Produto.objects.update_or_create(
                            sku=sku,
                            defaults=defaults,
                        )
                        if espessura == 15:
                            produto_ref = produto

                        criados += int(created)
                        atualizados += int(not created)
                    if produto_ref:
                        fitas_criadas += ProdutoService.sincronizar_fitas_borda_para_mdf(produto_ref)

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed de produtos finalizado. MDF criados: {criados}. MDF atualizados: {atualizados}. Fitas criadas: {fitas_criadas}."
            )
        )
