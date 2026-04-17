# apps/bipagem/models/peca.py
from django.db import models
from django.utils import timezone

from .modulo import Modulo
from .lote_producao import LoteProducao


class Peca(models.Model):
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('BIPADA', 'Bipada'),
        ('CONCLUIDA', 'Concluída'),
        ('CANCELADA', 'Cancelada'),
    ]

    modulo = models.ForeignKey(Modulo, on_delete=models.CASCADE, related_name='pecas')
    lote_producao = models.ForeignKey(
        LoteProducao, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='pecas',
        verbose_name="Lote de Produção"
    )
    
    id_peca = models.CharField(max_length=50, db_index=True)
    numero_lote_pcp = models.CharField(max_length=50, blank=True, db_index=True)
    
    descricao = models.CharField(max_length=255)
    local = models.CharField(max_length=100, db_index=True)
    material = models.CharField(max_length=255, blank=True)
    
    largura_mm = models.FloatField(null=True, blank=True)
    altura_mm = models.FloatField(null=True, blank=True)
    espessura_mm = models.FloatField(null=True, blank=True)
    quantidade = models.PositiveIntegerField(default=1)
    
    # Informações vindas do PCP
    roteiro = models.TextField(blank=True)
    plano_corte = models.CharField(max_length=10, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDENTE', db_index=True)
    destino = models.CharField(max_length=100, blank=True, null=True)
    data_bipagem = models.DateTimeField(null=True, blank=True)
    data_criacao = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Peça"
        verbose_name_plural = "Peças"
        ordering = ['id_peca']
        unique_together = ('modulo', 'id_peca')

    def __str__(self):
        return f"[{self.id_peca}] {self.descricao[:60]} — {self.local}"

    def bipa(self, usuario: str = 'SISTEMA', localizacao: str = ''):
        if self.status != 'BIPADA':
            self.status = 'BIPADA'
            self.data_bipagem = timezone.now()
            self.save(update_fields=['status', 'data_bipagem'])
        
        from .evento_bipagem import EventoBipagem
        EventoBipagem.objects.create(
            peca=self,
            usuario=usuario,
            localizacao=localizacao
        )