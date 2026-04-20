"""
Views do app PCP.

O PCP gerencia o ciclo de vida completo dos lotes:
liberar -> bloquear -> reabrir -> liberar viagem -> remover historico
"""
import re
import unicodedata

from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.files.base import ContentFile
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from apps.pcp.models.processamento import ProcessamentoPCP
from apps.pcp.services.historico_service import HistoricoPCPService
from apps.pcp.services.pcp_interface import (
    bloquear_lote_bipagem,
    liberar_lote_para_bipagem,
    reabrir_lote_bipagem,
)
from apps.pcp.services.retorno_bipagem_service import RetornoBipagemService
from apps.pcp.services.processador_roteiro import ProcessadorRoteiroService


def _normalizar_chave(chave: str) -> str:
    chave = unicodedata.normalize('NFD', chave)
    chave = ''.join(c for c in chave if unicodedata.category(c) != 'Mn')
    return re.sub(r'\W+', '_', chave).strip('_').upper()


def _user_pode_gerenciar_pcp(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    return user.groups.filter(name__in=['PCP', 'TI']).exists()


def _json_forbidden():
    return JsonResponse({'erro': 'Somente PCP, TI ou admin podem executar esta acao.'}, status=403)


def _validar_risco_estoque_para_liberacao(pid: str):
    """
    Valida risco de ruptura antes da liberacao do lote para bipagem.
    Regra protegida por feature-flag para nao impactar operacao atual.
    """
    if not getattr(settings, "PCP_BLOQUEAR_LIBERACAO_COM_RISCO_ESTOQUE", False):
        return None

    processamento = ProcessamentoPCP.objects.filter(id=pid).only("id", "lote").first()
    if not processamento:
        return JsonResponse({'erro': 'Lote nao encontrado.'}, status=404)

    try:
        from apps.estoque.services.public_interface import EstoquePublicService

        chaves_lote = [str(processamento.id)]
        if processamento.lote:
            chaves_lote.append(str(processamento.lote))
            chaves_lote.append(f"LOTE-{processamento.lote}")

        janela_dias = int(getattr(settings, "PCP_ESTOQUE_RISCO_JANELA_DIAS", 30))
        for lote_ref in chaves_lote:
            analise = EstoquePublicService.consultar_risco_ruptura_lote(
                lote_pcp_id=lote_ref,
                dias=janela_dias,
            )
            if analise.get("itens"):
                if analise.get("risco_ruptura"):
                    return JsonResponse(
                        {
                            'erro': 'Liberacao bloqueada por risco de ruptura de estoque.',
                            'lote_referencia': lote_ref,
                            'analise_estoque': analise,
                        },
                        status=409,
                    )
                break
    except Exception as exc:
        return JsonResponse(
            {
                'erro': 'Falha ao validar risco de estoque para liberacao.',
                'detalhe': str(exc),
            },
            status=503,
        )

    return None


# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------

@login_required
def pcp_index(request):
    return render(request, 'pcp/index.html', {
        'pode_gerenciar_pcp': _user_pode_gerenciar_pcp(request.user),
    })


# ---------------------------------------------------------------------------
# Processamento
# ---------------------------------------------------------------------------

@login_required
@require_POST
def pcp_processar(request):
    """View principal do PCP - Pipeline v2."""
    project_id = request.POST.get("project_id", "").strip()
    lote_str = request.POST.get("lote", "").strip()
    
    if not project_id or not (lote_str and lote_str.isdigit()):
        return JsonResponse({"erro": "project_id e lote são obrigatórios"}, status=400)

    try:
        service = ProcessadorRoteiroService()
        resultado = service.processar_projeto_dinabox(
            project_id=project_id,
            numero_lote=int(lote_str),
            usuario=request.user
        )
        # Preparar prévia para o frontend (primeiras 50 peças)
        previa = []
        for p in resultado.pecas_finais[:50]:
            previa.append({
                "LOTE": p.get("lote_saida", ""),
                "DESCRICAO_DA_PECA": p.get("descricao", ""),
                "LOCAL": p.get("modulo_nome", ""),
                "OBSERVACAO": p.get("observacoes_original", ""),
                "PLANO": p.get("plano_corte", ""),
                "ROTEIRO": p.get("roteiro", ""),
            })

        # Resumo por roteiro
        roteiro_counts = {}
        for p in resultado.pecas_finais:
            rot = p.get("roteiro", "NENHUM")
            roteiro_counts[rot] = roteiro_counts.get(rot, 0) + 1
        
        resumo_roteiro = [{"roteiro": k, "qtd": v} for k, v in roteiro_counts.items()]

        return JsonResponse({
            "sucesso": True,
            "pid": resultado.processamento_id,
            "lote": int(lote_str),
            "total": len(resultado.pecas_finais),
            "resumo_processamento": resultado.resumo.model_dump(),
            "nome_saida": resultado.arquivo_xls,
            "auditoria_count": len(resultado.auditoria or []),
            "previa": previa,
            "resumo": resumo_roteiro,
        })
    except Exception as e:
        return JsonResponse({"erro": str(e)}, status=500)

# ---------------------------------------------------------------------------
# Ciclo de vida do lote (bipagem)
# ---------------------------------------------------------------------------

@require_POST
@login_required
def pcp_liberar(request, pid):
    if not _user_pode_gerenciar_pcp(request.user):
        return _json_forbidden()
    try:
        bloqueio = _validar_risco_estoque_para_liberacao(pid)
        if bloqueio is not None:
            return bloqueio
        resultado = liberar_lote_para_bipagem(pid, usuario=request.user)
        if not resultado.get('sucesso'):
            return JsonResponse({'erro': resultado.get('mensagem')}, status=400)
        return JsonResponse(resultado)
    except Exception as e:
        return JsonResponse({'erro': str(e)}, status=500)


@require_POST
@login_required
def pcp_bloquear(request, pid):
    if not _user_pode_gerenciar_pcp(request.user):
        return _json_forbidden()
    motivo = request.POST.get('motivo', '') or request.GET.get('motivo', '')
    resultado = bloquear_lote_bipagem(pid, motivo=motivo)
    status_code = 200 if resultado['sucesso'] else 404
    return JsonResponse(resultado, status=status_code)


@require_POST
@login_required
def pcp_reabrir(request, pid):
    if not _user_pode_gerenciar_pcp(request.user):
        return _json_forbidden()
    resultado = reabrir_lote_bipagem(pid)
    status_code = 200 if resultado['sucesso'] else 404
    return JsonResponse(resultado, status=status_code)


# ---------------------------------------------------------------------------
# Ciclo de vida do lote (viagem/expedicao)
# ---------------------------------------------------------------------------

@require_POST
@login_required
def pcp_liberar_viagem(request, pid):
    if not _user_pode_gerenciar_pcp(request.user):
        return _json_forbidden()
    try:
        from django.utils import timezone

        lote = ProcessamentoPCP.objects.get(id=pid)
        lote.liberado_para_viagem = True
        lote.data_liberacao_viagem = timezone.now()
        lote.save(update_fields=['liberado_para_viagem', 'data_liberacao_viagem'])

        return JsonResponse({
            'sucesso': True,
            'mensagem': 'Lote liberado para viagem.',
            'data_liberacao_viagem': lote.data_liberacao_viagem.isoformat(),
        })
    except ProcessamentoPCP.DoesNotExist:
        return JsonResponse({'erro': 'Lote nao encontrado.'}, status=404)
    except Exception as e:
        return JsonResponse({'erro': str(e)}, status=500)


@require_POST
@login_required
def pcp_remover(request, pid):
    if not _user_pode_gerenciar_pcp(request.user):
        return _json_forbidden()

    try:
        motivo = request.POST.get('motivo', '').strip() or request.GET.get('motivo', '').strip()
        resultado = HistoricoPCPService.remover_processamento(pid=pid, motivo=motivo, usuario=request.user)
        if resultado.get('sucesso'):
            return JsonResponse(resultado, status=200)
        return JsonResponse(
            {
                'erro': resultado.get('mensagem', 'Nao foi possivel remover o lote.'),
                **resultado,
            },
            status=400,
        )
    except Exception as e:
        return JsonResponse({'erro': str(e)}, status=500)


# ---------------------------------------------------------------------------
# Historico e download
# ---------------------------------------------------------------------------

@require_GET
@login_required
def pcp_historico(request):
    if not _user_pode_gerenciar_pcp(request.user):
        return _json_forbidden()
    registros = ProcessamentoPCP.objects.order_by('-criado_em')[:50]

    data = [
        {
            'id': r.id,
            'nome_arquivo': r.nome_arquivo,
            'lote': r.lote,
            'total_pecas': r.total_pecas,
            'data': r.criado_em.isoformat(),
            'liberado': r.liberado_para_bipagem,
            'data_liberacao': r.data_liberacao.isoformat() if r.data_liberacao else None,
            'liberado_viagem': r.liberado_para_viagem,
            'data_liberacao_viagem': (
                r.data_liberacao_viagem.isoformat() if r.data_liberacao_viagem else None
            ),
            'pode_remover': _user_pode_gerenciar_pcp(request.user),
        }
        for r in registros
    ]

    return JsonResponse(data, safe=False)


@require_GET
@login_required
def pcp_retorno_lote(request, pid):
    if not _user_pode_gerenciar_pcp(request.user):
        return _json_forbidden()
    retorno = RetornoBipagemService.obter_retorno_lote(pid=pid)
    if not retorno:
        return JsonResponse({'erro': 'Lote nao encontrado para retorno.'}, status=404)
    return JsonResponse(retorno)


@require_GET
@login_required
def pcp_retorno_relatorio(request, pid):
    if not _user_pode_gerenciar_pcp(request.user):
        return HttpResponse('Acesso negado.', status=403)
    csv_content = RetornoBipagemService.gerar_relatorio_csv(pid=pid)
    if csv_content is None:
        raise Http404('Lote nao encontrado para relatorio.')

    processamento = ProcessamentoPCP.objects.filter(id=pid).only('lote').first()
    lote_str = processamento.lote if processamento and processamento.lote else pid
    filename = f"retorno_bipagem_lote_{lote_str}.csv"

    response = HttpResponse(csv_content, content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@require_GET
@login_required
def pcp_download(request, pid):
    if not _user_pode_gerenciar_pcp(request.user):
        return HttpResponse('Acesso negado.', status=403)
    try:
        processamento = ProcessamentoPCP.objects.get(id=pid)
    except ProcessamentoPCP.DoesNotExist:
        raise Http404('Processamento nao encontrado.')

    if not processamento.arquivo_saida:
        raise Http404('Arquivo nao disponivel.')

    try:
        arquivo = processamento.arquivo_saida.open('rb')
    except FileNotFoundError:
        raise Http404('Arquivo nao encontrado no servidor.')

    nome = processamento.arquivo_saida.name.split('/')[-1]
    return FileResponse(arquivo, as_attachment=True, filename=nome)
