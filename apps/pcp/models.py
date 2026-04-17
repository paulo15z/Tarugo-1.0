from django.db import models
from django.utils.timezone import now

class ProcessamentoPCP(models.Model):
    id = models.CharField(max_length=8, primary_key=True)
    nome_arquivo = models.CharField(max_length=255)
    data = models.DateTimeField(default=now)
    total_pecas = models.PositiveIntegerField()
    arquivo_saida = models.CharField(max_length=255)  # nome do XLS gerado

    class Meta:
        ordering = ['-data']
        verbose_name = 'Processamento PCP'