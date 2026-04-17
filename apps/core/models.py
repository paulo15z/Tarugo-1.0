import uuid
from django.db import models
from django.utils import timezone


class BaseModel(models.Model):
    """BaseModel padrão do Tarugo - usado em TODOS os apps"""
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    ativo = models.BooleanField(default=True)          # soft-delete futuro
    criado_por = models.CharField(max_length=100, blank=True, null=True)
    atualizado_por = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        abstract = True
        ordering = ['-criado_em']

    def __str__(self):
        return f"{self.__class__.__name__} - {self.id}"