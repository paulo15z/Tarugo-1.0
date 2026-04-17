from django.db import models
from apps.pcp.models.processamento import ProcessamentoPCP

class LoteProducao(models.Model):
    """
    Representa um lote físico de produção gerado a partir de um processamento do PCP.
    Um lote pode conter peças de múltiplos pedidos (lote misto).
    """
    numero_lote = models.CharField(max_length=50, unique=True, verbose_name="Número do Lote")
    processamento_pcp = models.ForeignKey(
        ProcessamentoPCP,
        on_delete=models.CASCADE,
        related_name="lotes_producao",
        verbose_name="Processamento PCP"
    )
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name="Data de Criação")
    liberado_para_bipagem = models.BooleanField(default=False, verbose_name="Liberado para Bipagem")
    bloqueado_motivo = models.TextField(null=True, blank=True, verbose_name="Motivo do Bloqueio")
    observacoes = models.TextField(null=True, blank=True, verbose_name="Observações")

    class Meta:
        verbose_name = "Lote de Produção"
        verbose_name_plural = "Lotes de Produção"
        ordering = ['-data_criacao']

    def __str__(self):
        return f"Lote {self.numero_lote} ({self.processamento_pcp_id})"
