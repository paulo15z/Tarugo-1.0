from django.db import models
from apps.core.models import BaseModel
from decimal import Decimal


class LotePCP(BaseModel):
    """Lote gerado a partir de um arquivo Dinabox"""
    pid = models.CharField(max_length=8, unique=True, editable=False)
    arquivo_original = models.CharField(max_length=255)
    data_processamento = models.DateTimeField(auto_now_add=True)

    # Dados do cliente/projeto (espelhados do schema)
    cliente_nome = models.CharField(max_length=255)
    cliente_id_projeto = models.CharField(max_length=50, blank=True, null=True)
    ordem_producao = models.CharField(max_length=50, blank=True, null=True)

    status = models.CharField(
        max_length=20,
        choices=[
            ('pendente', 'Pendente'),
            ('em_producao', 'Em Produção'),
            ('finalizado', 'Finalizado'),
        ],
        default='pendente',
    )

    class Meta:
        verbose_name = 'Lote PCP'
        verbose_name_plural = 'Lotes PCP'
        ordering = ['-data_processamento']

    def __str__(self):
        return f"Lote {self.pid} - {self.cliente_nome}"


class AmbientePCP(BaseModel):
    """Ambiente do projeto (ex: SOCIAL, COZINHA)"""
    lote = models.ForeignKey(LotePCP, on_delete=models.CASCADE, related_name='ambientes')

    nome = models.CharField(max_length=100)  # NOME DO PROJETO

    class Meta:
        verbose_name = 'Ambiente PCP'
        verbose_name_plural = 'Ambientes PCP'
        unique_together = ('lote', 'nome')

    def __str__(self):
        return f"{self.nome} ({self.lote.pid})"


class ModuloPCP(BaseModel):
    """Módulo dentro de um ambiente (ex: armário, prateleira)"""
    ambiente = models.ForeignKey(AmbientePCP, on_delete=models.CASCADE, related_name='modulos')

    nome = models.CharField(max_length=100)                    # DESCRIÇÃO MÓDULO
    codigo_modulo = models.CharField(max_length=50, blank=True, null=True)  # ex: M2052026

    class Meta:
        verbose_name = 'Módulo PCP'
        verbose_name_plural = 'Módulos PCP'
        unique_together = ('ambiente', 'codigo_modulo', 'nome')

    def __str__(self):
        return f"{self.nome} ({self.codigo_modulo or 'standalone'})"


class PecaPCP(BaseModel):
    """Peça individual (uma linha do Dinabox)"""
    modulo = models.ForeignKey(ModuloPCP, on_delete=models.CASCADE, related_name='pecas', null=True, blank=True)

    # Campos da REFERENCIA (parseados)
    referencia_bruta = models.CharField(max_length=100)
    codigo_modulo = models.CharField(max_length=50, blank=True, null=True)
    codigo_peca = models.CharField(max_length=50)

    descricao = models.TextField()
    local = models.CharField(max_length=100, blank=True, null=True)
    material = models.CharField(max_length=100, blank=True, null=True)
    codigo_material = models.CharField(max_length=50, blank=True, null=True)

    # Dimensões
    comprimento = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    largura = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    espessura = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    metro_quadrado = models.DecimalField(max_digits=12, decimal_places=5, null=True, blank=True)

    quantidade_planejada = models.PositiveIntegerField()

    # Atributos técnicos (JSONField para flexibilidade futura)
    atributos_tecnicos = models.JSONField(default=dict, blank=True)

    # Campos calculados pelo processamento
    roteiro = models.TextField(blank=True, null=True)
    plano = models.CharField(max_length=2, blank=True, null=True)

    observacoes = models.TextField(blank=True, null=True)
    lote_dinabox = models.CharField(max_length=50, blank=True, null=True)
    id_peca_dinabox = models.CharField(max_length=50, blank=True, null=True)

    # Para bipagem futura (sem tocar no estoque por enquanto)
    quantidade_produzida = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=[
            ('pendente', 'Pendente'),
            ('em_producao', 'Em Produção'),
            ('finalizado', 'Finalizado'),
        ],
        default='pendente',
    )

    class Meta:
        verbose_name = 'Peça PCP'
        verbose_name_plural = 'Peças PCP'
        ordering = ['codigo_peca']

    def __str__(self):
        return f"{self.codigo_peca} - {self.descricao[:60]}"

    @property
    def esta_finalizada(self):
        return self.quantidade_produzida >= self.quantidade_planejada