from datetime import timezone
from apps.pcp.models.processamento import ProcessamentoPCP
from apps.pcp.models.lote import LotePCP, PecaPCP
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


# --- Funções de Interface Operacional (usadas pela Bipagem) ---

def list_lotes_operacionais(cliente: str = '', ambiente: str = '') -> list[dict]:
    """Lista lotes disponíveis para bipagem."""
    qs = LotePCP.objects.all()
    if cliente:
        qs = qs.filter(cliente_nome__icontains=cliente)
    
    lotes = []
    for lote in qs:
        lotes.append({
            "pid": lote.pid,
            "cliente": lote.cliente_nome,
            "data": lote.data_processamento,
            "status": lote.status
        })
    return lotes


def get_preview_lote_operacional(pid: str) -> dict | None:
    """Retorna resumo de um lote para o dashboard."""
    try:
        lote = LotePCP.objects.get(pid=pid)
        return {
            "pid": lote.pid,
            "cliente": lote.cliente_nome,
            "total_pecas": PecaPCP.objects.filter(modulo__ambiente__lote=lote).count(),
            "status": lote.status
        }
    except LotePCP.DoesNotExist:
        return None


def list_pecas_lote_operacional(pid: str, **filters) -> list[dict]:
    """Lista peças de um lote com filtros."""
    qs = PecaPCP.objects.filter(modulo__ambiente__lote__pid=pid)
    
    if filters.get('termo'):
        qs = qs.filter(descricao__icontains=filters['termo'])
    if filters.get('status'):
        qs = qs.filter(status=filters['status'])
        
    pecas = []
    for p in qs:
        pecas.append({
            "id": p.id,
            "descricao": p.descricao,
            "quantidade": p.quantidade_planejada,
            "bipada": p.quantidade_bipada,
            "status": p.status
        })
    return pecas


def registrar_bipagem_peca(pid: str, codigo_peca: str, quantidade: int, usuario: str = '', localizacao: str = '') -> dict:
    """Registra a bipagem de uma peça no lote."""
    try:
        peca = PecaPCP.objects.get(modulo__ambiente__lote__pid=pid, codigo_peca=codigo_peca)
        peca.quantidade_bipada += quantidade
        if peca.quantidade_bipada >= peca.quantidade_planejada:
            peca.status = 'concluido'
            peca.data_bipagem = timezone.now()
        else:
            peca.status = 'processando'
        peca.save()
        return {"sucesso": True, "mensagem": "Bipagem registrada"}
    except PecaPCP.DoesNotExist:
        return {"sucesso": False, "mensagem": "Peça não encontrada"}


def estornar_bipagem_peca(pid: str, codigo_peca: str, usuario: str = '', motivo: str = '') -> dict:
    """Estorna a bipagem de uma peça."""
    try:
        peca = PecaPCP.objects.get(modulo__ambiente__lote__pid=pid, codigo_peca=codigo_peca)
        peca.quantidade_bipada = 0
        peca.status = 'pendente'
        peca.data_bipagem = None
        peca.save()
        return {"sucesso": True, "mensagem": "Bipagem estornada"}
    except PecaPCP.DoesNotExist:
        return {"sucesso": False, "mensagem": "Peça não encontrada"}
