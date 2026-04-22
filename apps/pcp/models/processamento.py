# apps/pcp/models/processamento.py
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.db import models
from django.contrib.auth import get_user_model

class ProcessamentoPCP(models.Model):
    """Historico de processamentos do PCP"""

    id = models.CharField(max_length=8, primary_key=True, editable=False)
    nome_arquivo = models.CharField(max_length=255, verbose_name="Arquivo Original")
    lote = models.PositiveIntegerField(null=True, blank=True, verbose_name="Numero do Lote")
    total_pecas = models.PositiveIntegerField(default=0, verbose_name="Total de Pecas")

    liberado_para_bipagem = models.BooleanField(default=False, verbose_name="Liberado para Bipagem")
    data_liberacao = models.DateTimeField(null=True, blank=True, verbose_name="Data de Liberacao")

    liberado_para_viagem = models.BooleanField(default=False, verbose_name="Liberado para Viagem")
    data_liberacao_viagem = models.DateTimeField(null=True, blank=True, verbose_name="Data de Liberacao Viagem")

    arquivo_saida = models.FileField(
        upload_to='pcp/outputs/%Y/%m/%d/',
        null=True,
        blank=True,
        verbose_name="Roteiro Gerado",
    )

    criado_em = models.DateTimeField(default=timezone.now, editable=False)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Processamento PCP"
        verbose_name_plural = "Processamentos PCP"
        ordering = ['-criado_em']

    def __str__(self):
        lote_str = f"Lote {self.lote}" if self.lote else "Sem lote"
        return f"{self.id} - {lote_str} ({self.total_pecas} pecas)"


class AuditoriaProcessamentoPCP(models.Model):
    """Trilha de auditoria para exclusoes e outras acoes sensiveis do PCP."""

    ACAO_CHOICES = [
        ('EXCLUSAO', 'Exclusao'),
    ]

    processamento_id = models.CharField(max_length=8, db_index=True)
    lote = models.PositiveIntegerField(null=True, blank=True)
    nome_arquivo = models.CharField(max_length=255)
    acao = models.CharField(max_length=20, choices=ACAO_CHOICES)
    motivo = models.TextField()
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    criado_em = models.DateTimeField(default=timezone.now, editable=False)
    snapshot = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = 'Auditoria de Processamento PCP'
        verbose_name_plural = 'Auditorias de Processamentos PCP'
        ordering = ['-criado_em']

    def __str__(self):
        return f"{self.acao} {self.processamento_id}"


# ---------------------------------------------------------------#

User = get_user_model()

class AuditoriaRoteamento(models.Model):
    """
    Rastreia todas as transformações aplicadas em cada peça.
    Essencial para debug e auditoria operacional.
    """

    processamento = models.ForeignKey(
        'ProcessamentoPCP',
        on_delete=models.CASCADE,
        related_name='auditorias'
    )

    id_peca = models.CharField(max_length=100, db_index=True)
    tipo_transformacao = models.CharField(
        max_length=50,
        choices=[
            ('consolidacao', 'Consolidação de Ripas'),
            ('roteiro', 'Cálculo de Roteiro'),
            ('plano', 'Determinação de Plano'),
            ('validacao', 'Validação'),
        ]
    )

    valor_antes = models.TextField(blank=True)
    valor_depois = models.TextField(blank=True)
    regra_aplicada = models.CharField(max_length=200)
    confianca = models.CharField(max_length=20, default='high')

    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Auditoria de Roteamento"
        verbose_name_plural = "Auditorias de Roteamento"
        ordering = ['-criado_em']

    def __str__(self):
        return f"{self.tipo_transformacao} - {self.id_peca} ({self.regra_aplicada})"