from django.db import models

from apps.pcp.models.lote import PecaPCP


class EventoBipagem(models.Model):
    """Historico imutavel de movimentacoes operacionais da bipagem."""

    TIPO_CHOICES = [
        ("BIPAGEM", "Bipagem"),
        ("ESTORNO", "Estorno"),
    ]

    peca = models.ForeignKey(PecaPCP, on_delete=models.CASCADE, related_name="eventos_bipagem")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default="BIPAGEM")
    quantidade = models.PositiveIntegerField(default=1)
    momento = models.DateTimeField(auto_now_add=True, db_index=True)
    usuario = models.CharField(max_length=100, default="SISTEMA")
    localizacao = models.CharField(max_length=100, blank=True)
    motivo = models.TextField(blank=True)

    class Meta:
        verbose_name = "Evento de Bipagem"
        verbose_name_plural = "Eventos de Bipagem"
        ordering = ["-momento"]
        indexes = [models.Index(fields=["peca", "momento"])]

    def __str__(self):
        return f"{self.tipo} {self.peca.codigo_peca} - {self.momento.strftime('%d/%m %H:%M')}"
