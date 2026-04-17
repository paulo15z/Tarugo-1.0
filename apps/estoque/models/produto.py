# apps/estoque/models/produto.py
from django.db import models

from apps.estoque.models.categoria import CategoriaProduto


class Produto(models.Model):
    """Produto com suporte a categorias e atributos específicos (Tarugo MVP)"""

    nome = models.CharField(max_length=255, verbose_name="Nome")
    sku = models.CharField(max_length=100, unique=True, verbose_name="SKU")

    categoria = models.ForeignKey(
        CategoriaProduto,
        on_delete=models.PROTECT,
        related_name="produtos",
        verbose_name="Categoria",
    )

    unidade_medida = models.CharField(
        max_length=20,
        choices=[
            ("un", "Unidade"),
            ("pc", "Peça"),
            ("m", "Metro linear"),
            ("m2", "Metro quadrado"),
            ("kg", "Quilograma"),
            ("cx", "Caixa"),
            ("l", "Litro"),
        ],
        default="un",
        verbose_name="Unidade de medida",
    )

    quantidade = models.PositiveIntegerField(default=0, verbose_name="Quantidade em estoque")
    estoque_minimo = models.PositiveIntegerField(default=0, verbose_name="Estoque mínimo")

    preco_custo = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        verbose_name="Preço de custo",
    )

    lote = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Lote / Referência",
        help_text="Importante para rastreabilidade (NF, lote do fornecedor...)",
    )

    localizacao = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Localização no almoxarifado",
        help_text="Ex: Prateleira A-03, Gaveta Dobradiças",
    )

    # Campos flexíveis por categoria (ex: espessura no MDF, ângulo na dobradiça)
    atributos_especificos = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Atributos específicos",
    )

    ativo = models.BooleanField(default=True, verbose_name="Ativo")

    criado_em = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    atualizado_em = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    class Meta:
        ordering = ["categoria__nome", "nome"]
        verbose_name = "Produto"
        verbose_name_plural = "Produtos"

    def __str__(self):
        return f"{self.nome} ({self.sku}) — {self.categoria}"