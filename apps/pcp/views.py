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
from apps.pcp.services.pcp_service import processar_arquivo_dinabox


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

@require_POST
@login_required
def pcp_processar(request):
    if not _user_pode_gerenciar_pcp(request.user):
        return _json_forbidden()
    arquivo = request.FILES.get('arquivo')

    if not arquivo:
        return JsonResponse({'erro': 'Nenhum arquivo enviado.'}, status=400)

    lote_str = request.POST.get('lote', '').strip()
    if not lote_str or not lote_str.isdigit() or int(lote_str) <= 0:
        return JsonResponse({'erro': 'Informe um numero de lote valido.'}, status=400)

    try:
        df, xls_bytes, nome_saida, pid, resumo_processamento = processar_arquivo_dinabox(
            arquivo,
            int(lote_str),
        )

        processamento = ProcessamentoPCP.objects.create(
            id=pid,
            nome_arquivo=arquivo.name,
            lote=int(lote_str),
            total_pecas=len(df),
            usuario=request.user if request.user.is_authenticated else None,
        )

        arquivo_content = ContentFile(xls_bytes, name=nome_saida)
        processamento.arquivo_saida.save(nome_saida, arquivo_content, save=True)

        cols_previa = ['DESCRICAO DA PECA', 'DESCRIÇÃO DA PEÇA', 'LOCAL', 'PLANO', 'ROTEIRO']
        if 'LOTE' in df.columns:
            cols_previa.insert(0, 'LOTE')
        if 'OBSERVACAO' in df.columns or 'OBSERVA??O' in df.columns:
            cols_previa.insert(3, 'OBSERVACAO')

        cols_existentes = []
        variantes = {
            'DESCRICAO DA PECA': 'DESCRI??O DA PE?A',
            'DESCRIÇÃO DA PEÇA': 'DESCRI??O DA PE?A',
            'OBSERVACAO': 'OBSERVA??O',
        }
        for col in cols_previa:
            if col in df.columns:
                cols_existentes.append(col)
                continue
            coluna_real = variantes.get(col)
            if coluna_real and coluna_real in df.columns:
                cols_existentes.append(coluna_real)

        previa_raw = df[cols_existentes].head(50).fillna('').to_dict(orient='records')
        previa = [{_normalizar_chave(k): v for k, v in row.items()} for row in previa_raw]

        resumo_df = df['ROTEIRO'].fillna('SEM ROTEIRO').astype(str).value_counts().reset_index()
        resumo_df.columns = ['roteiro', 'qtd']
        resumo = resumo_df.to_dict(orient='records')

        return JsonResponse({
            'pid': pid,
            'lote': int(lote_str),
            'total': len(df),
            'resumo_processamento': resumo_processamento,
            'previa': previa,
            'resumo': resumo,
            'nome_saida': nome_saida,
        })
    except Exception as e:
        return JsonResponse({'erro': str(e)}, status=500)


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
