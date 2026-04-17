from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bipagem.services.bipagem_service import registrar_bipagem
from apps.pcp.services.pcp_interface import get_preview_lote_operacional, list_pecas_lote_operacional


class LotePreviewView(APIView):
    def get(self, request, pid):
        preview = get_preview_lote_operacional(pid)
        if not preview:
            return Response({'erro': 'Lote nao encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(preview)


class LotePecasView(APIView):
    def get(self, request, pid):
        data = list_pecas_lote_operacional(
            pid=pid,
            termo=request.query_params.get('q', '').strip(),
            ambiente=request.query_params.get('ambiente', '').strip(),
            plano=request.query_params.get('plano', '').strip(),
            status=request.query_params.get('status', '').strip(),
        )
        return Response(data)


class BipagemView(APIView):
    def post(self, request):
        resultado = registrar_bipagem({
            'pid': request.data.get('pid', ''),
            'codigo_peca': request.data.get('codigo', ''),
            'quantidade': request.data.get('quantidade', 1),
            'usuario': request.data.get('usuario', 'OPERADOR'),
            'localizacao': request.data.get('localizacao', ''),
        })

        if resultado.get('sucesso'):
            return Response(resultado, status=status.HTTP_200_OK)
        return Response(resultado, status=status.HTTP_400_BAD_REQUEST)
