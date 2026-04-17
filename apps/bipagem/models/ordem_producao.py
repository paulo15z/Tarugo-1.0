from django.db import models
from django.utils import timezone

from .pedido import Pedido


class OrdemProducao(models.Model):
    """Ambiente ou projeto dentro do pedido (SUÍTE HÓSPEDES, CLOSET MASTER...)"""
    
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='ordens_producao')
    
    nome_ambiente = models.CharField(max_length=255)
    referencia_principal = models.CharField(max_length=100, blank=True)

    data_criacao = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Ordem de Produção"
        verbose_name_plural = "Ordens de Produção"
        ordering = ['nome_ambiente']
        unique_together = ('pedido', 'nome_ambiente')

    def __str__(self):
        return f"{self.nome_ambiente} (Pedido {self.pedido.numero_pedido})"

    @property
    def total_pecas(self):
        return self.pecas.count()

    @property
    def pecas_bipadas(self):
        return self.pecas.filter(status='BIPADA').count()

    @property
    def percentual_concluido(self):
        total = self.total_pecas
        if total == 0:
            return 0
        return int((self.pecas_bipadas / total) * 100)