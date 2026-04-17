from django.db import models
from django.contrib.auth import get_user_model

from apps.estoque.domain.tipos import TipoMovimentacao
from apps.estoque.models.produto import Produto

User = get_user_model()


class Movimentacao(models.Model):
    produto = models.ForeignKey(
        Produto,
        on_delete=models.CASCADE,
        related_name="movimentacoes",
        verbose_name="Produto",
    )
    tipo = models.CharField(
        max_length=10,
        choices=TipoMovimentacao.choices(),
        verbose_name="Tipo",
    )
    espessura = models.IntegerField(
        verbose_name="Espessura (MDF)",
        null=True,
        blank=True
    )
    quantidade = models.PositiveIntegerField(verbose_name="Quantidade")
    usuario = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimentacoes",
        verbose_name="Usuário",
    )
    observacao = models.TextField(blank=True, null=True, verbose_name="Observação")

    criado_em = models.DateTimeField(auto_now_add=True, verbose_name="Data/Hora")

    class Meta:
        ordering = ["-criado_em"]
        verbose_name = "Movimentação"
        verbose_name_plural = "Movimentações"

    def __str__(self):
        usuario_str = self.usuario.username if self.usuario else "sistema"
        return f"{self.get_tipo_display()} • {self.produto.nome} ({self.quantidade}) por {usuario_str}"