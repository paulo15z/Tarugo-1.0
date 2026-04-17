from django.db import models
from django.utils import timezone

from .ordem_producao import OrdemProducao


class Modulo(models.Model):
    """Módulo / Móvel / Unidade (ex: Torre D Guarda Roupa, Gaveteiro, Itens Personalizados)"""
    
    ordem_producao = models.ForeignKey(OrdemProducao, on_delete=models.CASCADE, related_name='modulos')
    
    referencia_modulo = models.CharField(max_length=100, db_index=True)   # ex: M10175926 ou T5627157
    nome_modulo = models.CharField(max_length=255)                        # descrição do módulo
    
    data_criacao = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Módulo"
        verbose_name_plural = "Módulos"
        ordering = ['referencia_modulo']
        unique_together = ('ordem_producao', 'referencia_modulo')

    def __str__(self):
        return f"{self.referencia_modulo} - {self.nome_modulo}"

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