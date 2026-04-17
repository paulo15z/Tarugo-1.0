from django.db import models
from django.utils import timezone


class Pedido(models.Model):
    """Pedido que vem do comercial (ex: número 573 - sergio possenti)"""
    
    numero_pedido = models.CharField(max_length=50, unique=True, db_index=True)  # 573
    cliente_nome = models.CharField(max_length=255, db_index=True)
    data_criacao = models.DateTimeField(default=timezone.now)
    data_importacao = models.DateTimeField(auto_now_add=True)
    
    # Acompanhamento por Projeto (Gêmeo Digital)
    STATUS_PROJETO = [
        ('ORCAMENTO', 'Orçamento'),
        ('APROVADO', 'Aprovado'),
        ('PCP', 'Em PCP'),
        ('PRODUCAO', 'Em Produção'),
        ('EXPEDICAO', 'Em Expedição'),
        ('ENTREGUE', 'Entregue'),
        ('CANCELADO', 'Cancelado'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_PROJETO, default='APROVADO', db_index=True)
    bloqueado = models.BooleanField(default=False, verbose_name="Bipagem Bloqueada")
    data_entrega_prevista = models.DateField(null=True, blank=True)
    data_conclusao = models.DateTimeField(null=True, blank=True)
    observacoes = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"
        ordering = ['-data_criacao']

    def __str__(self):
        return f"Pedido {self.numero_pedido} - {self.cliente_nome}"

    @property
    def total_pecas(self):
        return self.ordens_producao.aggregate(total=models.Sum('total_pecas'))['total'] or 0

    @property
    def pecas_bipadas(self):
        return self.ordens_producao.aggregate(bipadas=models.Sum('pecas_bipadas'))['bipadas'] or 0