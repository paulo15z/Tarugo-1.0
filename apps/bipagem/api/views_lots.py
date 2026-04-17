# apps/bipagem/api/views_lots.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Count, Q

from apps.bipagem.models import OrdemProducao, Modulo, Peca
from .serializers import (
    OrdemProducaoSerializer,
    ModuloSerializer,
    PecaListSerializer,
    PecaDetailSerializer
)


class LotesListView(APIView):
    """
    GET /api/bipagem/lotes/
    Lista todos os lotes (OrdemProducao) com status de progresso.
    """
    
    def get(self, request):
        # Filtrar apenas lotes com peças pendentes ou bipadas
        lotes = (
            OrdemProducao.objects
            .prefetch_related('modulos__pecas')
            .annotate(
                total_pecas=Count('modulos__pecas'),
                pecas_bipadas=Count('modulos__pecas', filter=Q(modulos__pecas__status='BIPADA'))
            )
            .order_by('-id')
        )
        
        data = []
        for lote in lotes:
            total = lote.total_pecas
            bipadas = lote.pecas_bipadas
            percentual = int((bipadas / total) * 100) if total > 0 else 0
            
            data.append({
                'id': lote.id,
                'nome_ambiente': lote.nome_ambiente,
                'referencia_principal': lote.referencia_principal,
                'total_pecas': total,
                'pecas_bipadas': bipadas,
                'percentual_concluido': percentual,
                'status': 'concluido' if percentual == 100 else 'em_progresso' if percentual > 0 else 'pendente'
            })
        
        return Response({
            'total_lotes': len(data),
            'lotes': data
        })


class LoteDetailView(APIView):
    """
    GET /api/bipagem/lotes/<int:lote_id>/
    Retorna detalhes de um lote específico com todas as suas peças.
    """
    
    def get(self, request, lote_id):
        try:
            lote = (
                OrdemProducao.objects
                .prefetch_related('modulos__pecas')
                .get(id=lote_id)
            )
            
            modulos_data = []
            for modulo in lote.modulos.all():
                pecas = modulo.pecas.all()
                modulos_data.append({
                    'id': modulo.id,
                    'referencia_modulo': modulo.referencia_modulo,
                    'nome_modulo': modulo.nome_modulo,
                    'total_pecas': pecas.count(),
                    'pecas_bipadas': pecas.filter(status='BIPADA').count(),
                    'pecas': PecaListSerializer(pecas, many=True).data
                })
            
            total_pecas = sum(m['total_pecas'] for m in modulos_data)
            total_bipadas = sum(m['pecas_bipadas'] for m in modulos_data)
            percentual = int((total_bipadas / total_pecas) * 100) if total_pecas > 0 else 0
            
            return Response({
                'lote': {
                    'id': lote.id,
                    'nome_ambiente': lote.nome_ambiente,
                    'referencia_principal': lote.referencia_principal,
                    'total_pecas': total_pecas,
                    'pecas_bipadas': total_bipadas,
                    'percentual_concluido': percentual,
                },
                'modulos': modulos_data
            })
        except OrdemProducao.DoesNotExist:
            return Response(
                {'erro': f'Lote {lote_id} não encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )


class PecasPorLoteView(APIView):
    """
    GET /api/bipagem/lotes/<int:lote_id>/pecas/?status=PENDENTE
    Retorna as peças de um lote com filtro opcional por status.
    """
    
    def get(self, request, lote_id):
        status_filter = request.query_params.get('status', None)
        
        try:
            lote = OrdemProducao.objects.get(id=lote_id)
        except OrdemProducao.DoesNotExist:
            return Response(
                {'erro': f'Lote {lote_id} não encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Coletar todas as peças do lote
        pecas_qs = Peca.objects.filter(modulo__ordem_producao=lote)
        
        if status_filter:
            pecas_qs = pecas_qs.filter(status=status_filter)
        
        pecas = pecas_qs.order_by('status', 'id_peca')
        
        return Response({
            'lote_id': lote_id,
            'total_pecas': pecas.count(),
            'pecas': PecaDetailSerializer(pecas, many=True).data
        })
