from django.db import models
from apps.estoque.models.produto import Produto

class SaldoMDF(models.Model):
    """Saldo por espessura para produtos da família MDF"""
    produto = models.ForeignKey(
        Produto, 
        on_delete=models.CASCADE, 
        related_name='saldos_mdf',
        verbose_name="Produto (MDF)"
    )
    espessura = models.IntegerField(verbose_name="Espessura (mm)")
    quantidade = models.PositiveIntegerField(default=0, verbose_name="Quantidade em estoque")
    preco_custo = models.DecimalField(
        max_digits=12, 
        decimal_places=4, 
        null=True, 
        blank=True, 
        verbose_name="Preço de custo (Chapa)"
    )
    
    class Meta:
        verbose_name = "Saldo MDF"
        verbose_name_plural = "Saldos MDF"
        unique_together = [['produto', 'espessura']]
        ordering = ['produto', 'espessura']

    def __str__(self):
        return f"{self.produto.nome} - {self.espessura}mm: {self.quantidade}"
