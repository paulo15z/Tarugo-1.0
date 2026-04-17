"""
Interface publica do modulo PCP.

Regra: outros apps (bipagem, estoque, etc.) so podem importar do PCP atraves
este modulo. Nunca importar models ou services internos diretamente de fora do
app pcp.
"""
from __future__ import annotations

from typing import TypedDict

from django.db.models import Count


def _processamento_liberado_para_bipagem(pid: str):
    from apps.pcp.models.processamento import ProcessamentoPCP

    return ProcessamentoPCP.objects.filter(id=pid, liberado_para_bipagem=True).first()


def _resolver_peca_por_codigo(pid: str, codigo_peca: str):
    """
    Resolve a peca operacional pelo codigo dentro do lote.

    Regra:
    - Se houver uma unica ocorrencia, retorna ela.
    - Se houver multiplas ocorrencias, prioriza as que ainda faltam bipagem.
    - Se continuar ambiguo, nao escolhe "a primeira": retorna erro explicito.
    """
    from apps.pcp.models.lote import PecaPCP

    candidatas = list(
        PecaPCP.objects
        .filter(modulo__ambiente__lote__pid=pid, codigo_peca=codigo_peca)
        .select_related('modulo__ambiente__lote')
        .order_by('id')
    )
    if not candidatas:
        return None, 'Peca nao encontrada neste lote.'

    if len(candidatas) == 1:
        return candidatas[0], None

    pendentes = [
        p for p in candidatas
        if p.quantidade_produzida < p.quantidade_planejada
    ]
    if len(pendentes) == 1:
        return pendentes[0], None

    if len(pendentes) > 1:
        planos = sorted({p.plano for p in pendentes if p.plano})
        return None, (
            'Codigo de peca duplicado no lote. '
            f'Nao foi possivel identificar unicamente (planos: {", ".join(planos) or "--"}).'
        )

    # Todas finalizadas; retorna uma para mensagem de repetido.
    return candidatas[0], None


def _proxima_etapa_operacional(roteiro: str | None) -> str | None:
    if not roteiro:
        return None

    etapas = [etapa.strip() for etapa in roteiro.split('>') if etapa.strip()]
    if not etapas:
        return None

    ignorar = {'COR', 'CQL', 'EXP'}
    for etapa in etapas:
        if etapa not in ignorar:
            return etapa
    return None


class LoteInfo(TypedDict):
    id: str
    lote: int | None
    nome_arquivo: str
    criado_em: str
    liberado_para_bipagem: bool
    liberado_para_viagem: bool
    data_liberacao: str | None
    total_pecas: int


class LoteOperacionalInfo(TypedDict):
    pid: str
    lote: int | None
    nome_arquivo: str
    cliente_nome: str
    ordem_producao: str | None
    criado_em: str
    total_pecas: int
    pecas_bipadas: int
    pecas_pendentes: int
    percentual_bipado: float
    total_ambientes: int
    total_modulos: int
    total_ripas: int
    ambientes: list[str]


class PecaOperacionalInfo(TypedDict):
    id: str
    codigo_peca: str
    descricao: str
    ambiente: str
    modulo: str
    local: str | None
    material: str | None
    quantidade_planejada: int
    quantidade_produzida: int
    faltam: int
    status: str
    roteiro: str | None
    plano: str | None
    lote: str | None
    observacoes: str | None
    destino: str
    proxima_etapa: str | None


class LotePreviewInfo(TypedDict):
    lote: LoteOperacionalInfo
    clientes: list[str]
    ambientes: list[str]
    planos: list[str]
    total_modulos: int
    total_ripas: int
    total_pecas: int
    total_pecas_bipadas: int


def get_lotes_liberados_para_bipagem() -> list[LoteInfo]:
    from apps.pcp.models.processamento import ProcessamentoPCP

    qs = ProcessamentoPCP.objects.filter(liberado_para_bipagem=True).order_by('-criado_em')
    return [_to_lote_info(p) for p in qs]


def get_numeros_lotes_liberados() -> list[str]:
    from apps.pcp.models.processamento import ProcessamentoPCP

    return list(
        ProcessamentoPCP.objects
        .filter(liberado_para_bipagem=True)
        .values_list('lote', flat=True)
    )


def list_lotes_operacionais(cliente: str = '', ambiente: str = '') -> list[LoteOperacionalInfo]:
    from apps.pcp.models.lote import LotePCP, PecaPCP
    from apps.pcp.models.processamento import ProcessamentoPCP

    processamentos = list(
        ProcessamentoPCP.objects
        .filter(liberado_para_bipagem=True)
        .order_by('-criado_em')
    )
    if not processamentos:
        return []

    pids = [p.id for p in processamentos]
    lotes_qs = (
        LotePCP.objects
        .filter(pid__in=pids)
        .prefetch_related('ambientes__modulos__pecas')
    )
    if cliente:
        lotes_qs = lotes_qs.filter(cliente_nome__icontains=cliente)
    if ambiente:
        lotes_qs = lotes_qs.filter(ambientes__nome__icontains=ambiente)
    lotes_qs = lotes_qs.distinct()

    proc_map = {p.id: p for p in processamentos}
    lotes_map = {l.pid: l for l in lotes_qs}

    resultado: list[LoteOperacionalInfo] = []
    for pid in pids:
        proc = proc_map.get(pid)
        lote_pcp = lotes_map.get(pid)
        if not proc or not lote_pcp:
            continue

        pecas = list(
            PecaPCP.objects
            .filter(modulo__ambiente__lote=lote_pcp)
            .select_related('modulo__ambiente')
        )
        total_pecas = len(pecas)
        pecas_bipadas = sum(1 for p in pecas if p.quantidade_produzida > 0)
        pecas_pendentes = sum(1 for p in pecas if p.quantidade_produzida < p.quantidade_planejada)
        total_modulos = lote_pcp.ambientes.aggregate(total=Count('modulos', distinct=True))['total'] or 0
        ambientes = list(lote_pcp.ambientes.order_by('nome').values_list('nome', flat=True))
        total_ripas = sum(1 for p in pecas if (p.plano or '') == '03')

        resultado.append({
            'pid': proc.id,
            'lote': proc.lote,
            'nome_arquivo': proc.nome_arquivo,
            'cliente_nome': lote_pcp.cliente_nome,
            'ordem_producao': lote_pcp.ordem_producao,
            'criado_em': proc.criado_em.isoformat(),
            'total_pecas': total_pecas,
            'pecas_bipadas': pecas_bipadas,
            'pecas_pendentes': pecas_pendentes,
            'percentual_bipado': round((pecas_bipadas / total_pecas * 100), 1) if total_pecas else 0.0,
            'total_ambientes': len(ambientes),
            'total_modulos': total_modulos,
            'total_ripas': total_ripas,
            'ambientes': ambientes,
        })

    return resultado


def get_lote_operacional(pid: str) -> LoteOperacionalInfo | None:
    for lote in list_lotes_operacionais():
        if lote['pid'] == pid:
            return lote
    return None


def get_preview_lote_operacional(pid: str) -> LotePreviewInfo | None:
    from apps.pcp.models.lote import LotePCP, PecaPCP

    lote = get_lote_operacional(pid)
    if not lote or not _processamento_liberado_para_bipagem(pid):
        return None

    lote_pcp = LotePCP.objects.filter(pid=pid).prefetch_related('ambientes__modulos__pecas').first()
    if not lote_pcp:
        return None

    pecas = list(PecaPCP.objects.filter(modulo__ambiente__lote=lote_pcp).select_related('modulo__ambiente'))
    planos = sorted({p.plano for p in pecas if p.plano})

    return {
        'lote': lote,
        'clientes': [lote_pcp.cliente_nome] if lote_pcp.cliente_nome else [],
        'ambientes': lote['ambientes'],
        'planos': planos,
        'total_modulos': lote['total_modulos'],
        'total_ripas': lote['total_ripas'],
        'total_pecas': lote['total_pecas'],
        'total_pecas_bipadas': lote['pecas_bipadas'],
    }


def list_pecas_lote_operacional(
    pid: str,
    termo: str = '',
    ambiente: str = '',
    plano: str = '',
    status: str = '',
) -> list[PecaOperacionalInfo]:
    from django.db.models import Q
    from apps.pcp.models.lote import PecaPCP

    if not _processamento_liberado_para_bipagem(pid):
        return []

    qs = (
        PecaPCP.objects
        .filter(modulo__ambiente__lote__pid=pid)
        .select_related('modulo__ambiente')
        .order_by('modulo__ambiente__nome', 'modulo__nome', 'codigo_peca')
    )

    if termo:
        qs = qs.filter(
            Q(codigo_peca__icontains=termo) |
            Q(descricao__icontains=termo) |
            Q(local__icontains=termo) |
            Q(modulo__nome__icontains=termo) |
            Q(modulo__ambiente__nome__icontains=termo)
        )
    if ambiente:
        qs = qs.filter(modulo__ambiente__nome__icontains=ambiente)
    if plano:
        qs = qs.filter(plano=plano)
    if status == 'pendente':
        qs = qs.filter(status='pendente')
    elif status == 'em_producao':
        qs = qs.filter(status='em_producao')
    elif status == 'finalizado':
        qs = qs.filter(status='finalizado')

    return [_to_peca_operacional_info(peca) for peca in qs]


def registrar_bipagem_peca(
    pid: str,
    codigo_peca: str,
    quantidade: int = 1,
    usuario: str = 'OPERADOR',
    localizacao: str = '',
) -> dict:
    from apps.bipagem.models import EventoBipagem
    from apps.pcp.services.lote_service import LotePCPService

    if not _processamento_liberado_para_bipagem(pid):
        return {'sucesso': False, 'mensagem': 'Lote bloqueado ou nao liberado para bipagem.'}

    peca, erro_resolucao = _resolver_peca_por_codigo(pid, codigo_peca)
    if erro_resolucao:
        return {'sucesso': False, 'mensagem': erro_resolucao}

    faltam = max(peca.quantidade_planejada - peca.quantidade_produzida, 0)
    if faltam <= 0:
        return {
            'sucesso': True,
            'mensagem': 'Peca ja finalizada anteriormente.',
            'repetido': True,
            'peca': _to_peca_operacional_info(peca),
        }

    quantidade_aplicada = min(quantidade, faltam)
    peca = LotePCPService.bipar_peca(peca_id=peca.id, quantidade=quantidade_aplicada, usuario=usuario)
    EventoBipagem.objects.create(
        peca=peca,
        tipo='BIPAGEM',
        quantidade=quantidade_aplicada,
        usuario=usuario,
        localizacao=localizacao,
    )
    return {
        'sucesso': True,
        'mensagem': 'Bipagem registrada com sucesso.',
        'repetido': False,
        'peca': _to_peca_operacional_info(peca),
    }


def estornar_bipagem_peca(
    pid: str,
    codigo_peca: str,
    usuario: str,
    motivo: str,
) -> dict:
    from apps.bipagem.models import EventoBipagem

    if not _processamento_liberado_para_bipagem(pid):
        return {'sucesso': False, 'mensagem': 'Lote bloqueado ou nao liberado para bipagem.'}

    peca, erro_resolucao = _resolver_peca_por_codigo(pid, codigo_peca)
    if erro_resolucao:
        return {'sucesso': False, 'mensagem': erro_resolucao}

    if peca.quantidade_produzida <= 0:
        return {'sucesso': False, 'mensagem': 'Peca ainda nao possui bipagem para estornar.'}

    # Estorno operacional e unitario: cada peca e tratada individualmente.
    quantidade_estornada = 1
    peca.quantidade_produzida -= quantidade_estornada
    if peca.quantidade_produzida <= 0:
        peca.quantidade_produzida = 0
        peca.status = 'pendente'
    elif peca.quantidade_produzida < peca.quantidade_planejada:
        peca.status = 'em_producao'
    else:
        peca.status = 'finalizado'
    peca.save(update_fields=['quantidade_produzida', 'status'])

    EventoBipagem.objects.create(
        peca=peca,
        tipo='ESTORNO',
        quantidade=quantidade_estornada,
        usuario=usuario,
        motivo=motivo,
    )
    return {
        'sucesso': True,
        'mensagem': 'Estorno registrado com sucesso.',
        'peca': _to_peca_operacional_info(peca),
    }


def get_lote_info(pid: str) -> LoteInfo | None:
    from apps.pcp.models.processamento import ProcessamentoPCP

    try:
        p = ProcessamentoPCP.objects.get(id=pid)
        return _to_lote_info(p)
    except ProcessamentoPCP.DoesNotExist:
        return None


def liberar_lote_para_bipagem(pid: str, usuario=None) -> dict:
    from apps.pcp.services.processamento_service import ProcessamentoPCPService

    return ProcessamentoPCPService.liberar_lote(pid, usuario=usuario)


def bloquear_lote_bipagem(pid: str, motivo: str = '') -> dict:
    from apps.pcp.models.processamento import ProcessamentoPCP
    from apps.bipagem.models import LoteProducao

    try:
        proc = ProcessamentoPCP.objects.get(id=pid)
        proc.liberado_para_bipagem = False
        proc.data_liberacao = None
        proc.save(update_fields=['liberado_para_bipagem', 'data_liberacao'])

        LoteProducao.objects.filter(processamento_pcp=proc).update(
            liberado_para_bipagem=False,
            bloqueado_motivo=motivo or 'Bloqueado pelo PCP'
        )

        return {'sucesso': True, 'mensagem': f'Lote {proc.lote} bloqueado para bipagem.'}
    except ProcessamentoPCP.DoesNotExist:
        return {'sucesso': False, 'mensagem': 'Processamento nao encontrado.'}


def reabrir_lote_bipagem(pid: str) -> dict:
    from django.utils import timezone
    from apps.pcp.models.processamento import ProcessamentoPCP
    from apps.bipagem.models import LoteProducao

    try:
        proc = ProcessamentoPCP.objects.get(id=pid)

        if not proc.liberado_para_bipagem:
            proc.liberado_para_bipagem = True
            proc.data_liberacao = timezone.now()
            proc.save(update_fields=['liberado_para_bipagem', 'data_liberacao'])

        LoteProducao.objects.filter(processamento_pcp=proc).update(
            liberado_para_bipagem=True,
            bloqueado_motivo=None,
        )

        return {'sucesso': True, 'mensagem': f'Lote {proc.lote} reaberto para bipagem.'}
    except ProcessamentoPCP.DoesNotExist:
        return {'sucesso': False, 'mensagem': 'Processamento nao encontrado.'}


def _to_lote_info(p) -> LoteInfo:
    return LoteInfo(
        id=p.id,
        lote=p.lote,
        nome_arquivo=p.nome_arquivo,
        criado_em=p.criado_em.isoformat(),
        liberado_para_bipagem=p.liberado_para_bipagem,
        liberado_para_viagem=p.liberado_para_viagem,
        data_liberacao=p.data_liberacao.isoformat() if p.data_liberacao else None,
        total_pecas=p.total_pecas,
    )


def _to_peca_operacional_info(peca) -> PecaOperacionalInfo:
    from apps.bipagem.domain.tipos import get_nome_etapa, get_nome_setor

    return {
        'id': str(peca.id),
        'codigo_peca': peca.codigo_peca,
        'descricao': peca.descricao,
        'ambiente': peca.modulo.ambiente.nome if peca.modulo and peca.modulo.ambiente else '',
        'modulo': peca.modulo.nome if peca.modulo else '',
        'local': peca.local,
        'material': peca.material,
        'quantidade_planejada': peca.quantidade_planejada,
        'quantidade_produzida': peca.quantidade_produzida,
        'faltam': max(peca.quantidade_planejada - peca.quantidade_produzida, 0),
        'status': peca.status,
        'roteiro': peca.roteiro,
        'plano': peca.plano,
        'lote': peca.lote_dinabox,
        'observacoes': peca.observacoes,
        'destino': get_nome_setor(peca.plano),
        'proxima_etapa': get_nome_etapa(_proxima_etapa_operacional(peca.roteiro)),
    }
