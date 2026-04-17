from django.http import Http404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.pcp.models.lote import LotePCP
from apps.pcp.services.lote_service import LotePCPService
from apps.pcp.selectors.lote_selector import (
    list_lotes_pendentes,
    get_lote_by_pid,
    get_peca_by_id,
)
from .serializers import (
    LotePCPListSerializer,
    LotePCPDetailSerializer,
    BipagemRequestSerializer,
    PecaPCPSerializer,
)


class LotePCPViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API PCP - Lotes e Bipagem
    GET /api/pcp/lotes/          → lista de lotes pendentes
    GET /api/pcp/lotes/{pid}/    → detalhe completo (hierarquia)
    POST /api/pcp/lotes/{pid}/bipar/ → bipagem simples
    """
    queryset = LotePCP.objects.all()
    lookup_field = 'pid'

    def get_serializer_class(self):
        if self.action == 'list':
            return LotePCPListSerializer
        return LotePCPDetailSerializer

    def get_queryset(self):
        if self.action == 'list':
            return list_lotes_pendentes()
        return super().get_queryset()

    def get_object(self):
        if self.action == 'retrieve':
            pid = self.kwargs.get(self.lookup_field)
            lote = get_lote_by_pid(pid)
            if not lote:
                raise Http404
            return lote
        return super().get_object()

    @action(detail=True, methods=['post'], url_path='bipar')
    def bipar(self, request, pid=None):
        """Bipagem real da empresa - simples e rápida"""
        serializer = BipagemRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        peca = get_peca_by_id(serializer.validated_data['peca_id'])
        if not peca or peca.modulo.ambiente.lote.pid != pid:
            return Response(
                {"detail": "Peça não encontrada ou não pertence a este lote"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Toda regra de negócio está no Service
        peca_atualizada = LotePCPService.bipar_peca(
            peca_id=peca.id,
            quantidade=serializer.validated_data['quantidade'],
            # usuario=request.user.username se quiser logar quem bipou
        )

        return Response(
            {
                "message": f"Bipado {serializer.validated_data['quantidade']} unidade(s) com sucesso!",
                "peca": PecaPCPSerializer(peca_atualizada).data
            },
            status=status.HTTP_200_OK
        )
