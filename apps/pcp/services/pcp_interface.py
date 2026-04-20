from datetime import timezone

from django.conf import settings
from apps.pcp.models.processamento import ProcessamentoPCP
from apps.pcp.services.processador_roteiro import ProcessadorRoteiroService


def liberar_lote_para_bipagem(pid: str, usuario=None):
    """Mantém compatibilidade com o ciclo de vida existente."""
    lote = ProcessamentoPCP.objects.get(id=pid)
    lote.liberado_para_bipagem = True
    lote.data_liberacao = timezone.now()
    lote.save(update_fields=['liberado_para_bipagem', 'data_liberacao'])
    return {"sucesso": True, "mensagem": "Lote liberado com sucesso (novo pipeline)"}


def bloquear_lote_bipagem(pid: str, motivo: str = ""):
    lote = ProcessamentoPCP.objects.get(id=pid)
    lote.liberado_para_bipagem = False
    lote.save(update_fields=['liberado_para_bipagem'])
    return {"sucesso": True, "mensagem": f"Lote bloqueado: {motivo}"}


def reabrir_lote_bipagem(pid: str):
    lote = ProcessamentoPCP.objects.get(id=pid)
    lote.liberado_para_bipagem = True
    lote.save(update_fields=['liberado_para_bipagem'])
    return {"sucesso": True, "mensagem": "Lote reaberto"}


# Funções de viagem permanecem iguais (modelo é o mesmo)