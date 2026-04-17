from django.contrib.auth import get_user_model
from django.db import models

from apps.estoque.models.produto import Produto

User = get_user_model()

STATUS_CHOICES = [
    ("ativa", "Ativa"),
    ("consumida", "Consumida"),
    ("cancelada", "Cancelada"),
]

ORIGEM_CHOICES = [
    ("pcp", "PCP"),
    ("manual", "Manual"),
    ("integracao", "Integracao"),
]


class Reserva(models.Model):
    produto = models.ForeignKey(
        Produto,
        on_delete=models.CASCADE,
        related_name="reservas",
        verbose_name="Produto",
    )
    lote_pcp_id = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="Lote PCP",
        help_text="Identificador do lote no PCP.",
    )
    modulo_id = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="Modulo PCP",
        help_text="Quando aplicavel.",
    )
    ambiente = models.CharField(
        max_length=80,
        null=True,
        blank=True,
        verbose_name="Ambiente / Setor",
    )
    referencia_externa = models.CharField(
        max_length=120,
        null=True,
        blank=True,
        verbose_name="Referencia Externa",
        help_text="Codigo externo (pedido, lote, modulo ou projeto).",
    )
    origem_externa = models.CharField(
        max_length=20,
        choices=ORIGEM_CHOICES,
        default="pcp",
        verbose_name="Origem",
    )
    projeto_legado = models.CharField(
        max_length=255,
        verbose_name="Projeto (Legado)",
        null=True,
        blank=True,
    )
    espessura = models.IntegerField(
        verbose_name="Espessura (MDF)",
        null=True,
        blank=True,
        help_text="Apenas para produtos da familia MDF",
    )
    quantidade = models.PositiveIntegerField(verbose_name="Quantidade")
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="ativa",
        verbose_name="Status",
    )
    usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reservas",
        verbose_name="Usuario",
    )
    observacao = models.TextField(blank=True, null=True, verbose_name="Observacao")
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    atualizado_em = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    class Meta:
        verbose_name = "Reserva"
        verbose_name_plural = "Reservas"
        ordering = ["-criado_em"]
        indexes = [
            models.Index(fields=["status", "produto"]),
            models.Index(fields=["lote_pcp_id"]),
        ]

    @property
    def projeto(self):
        if self.referencia_externa:
            return self.referencia_externa
        if self.lote_pcp_id:
            return f"Lote {self.lote_pcp_id}"
        return self.projeto_legado or "Sem Referencia"

    def __str__(self):
        return f"Reserva {self.projeto} - {self.produto.nome} ({self.quantidade})"
