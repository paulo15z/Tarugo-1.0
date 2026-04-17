# apps/pcp/selectors/pcp_selectors.py
from apps.pcp.models.processamento import ProcessamentoPCP
from django.db.models import QuerySet


def get_historico_pcp() -> QuerySet:
    """
    Selector padrão para histórico completo.
    Centraliza a consulta e facilita futuras filtros (empresa, usuário, período, etc). q umaa hora ou outra vai vir
    """
    return ProcessamentoPCP.objects.all().order_by('-data')


def get_processamento_by_pid(pid: str) -> ProcessamentoPCP | None:
    """Busca um processamento específico por PID"""
    try:
        return ProcessamentoPCP.objects.get(id=pid)
    except ProcessamentoPCP.DoesNotExist:
        return None


def get_historico_pcp_filtrado(
    usuario_id: int | None = None,
    data_inicio: str | None = None,
    data_fim: str | None = None,
    limit: int = 50
) -> QuerySet:
    """
    Selector com filtros básicos (pronto para evolução futura).
    """
    qs = ProcessamentoPCP.objects.all().order_by('-data')

    #if usuario_id:
    #    qs = qs.filter(usuario_id=usuario_id)   # descomentar quando FK estiver ativo

    if data_inicio:
        qs = qs.filter(data__gte=data_inicio)

    if data_fim:
        qs = qs.filter(data__lte=data_fim)

    return qs[:limit]