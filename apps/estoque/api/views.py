from datetime import datetime

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.estoque.api.serializers import (
    AjusteLoteSerializer,
    MovimentacaoListSerializer,
    MovimentacaoSerializer,
    ProdutoListSerializer,
    ProdutoSerializer,
    ReservaCreateSerializer,
    ReservaSerializer,
)
from apps.estoque.selectors import listar_movimentacoes
from apps.estoque.services.movimentacao_service import MovimentacaoService
from apps.estoque.services.produto_service import ProdutoService
from apps.estoque.services.public_interface import EstoquePublicService
from apps.estoque.services.reserva_service import ReservaService


def _parse_date(value: str, field_name: str):
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} invalida. Use o formato ISO: YYYY-MM-DD.") from exc


def _parse_bool_param(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "sim"}


class ProdutoCreateView(APIView):
    def post(self, request):
        serializer = ProdutoSerializer(data=request.data)
        if serializer.is_valid():
            produto = ProdutoService.criar_produto(serializer.validated_data)
            return Response(ProdutoSerializer(produto).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProdutoListView(APIView):
    def get(self, request):
        produtos = ProdutoService.listar_produtos()
        data = []
        for produto in produtos:
            item = ProdutoListSerializer(produto).data
            item["disponibilidade"] = EstoquePublicService.consultar_disponibilidade(produto_id=produto.id)
            data.append(item)
        return Response(data, status=status.HTTP_200_OK)


class DisponibilidadeView(APIView):
    def get(self, request):
        params = request.query_params

        produto_id = params.get("produto_id")
        espessura = params.get("espessura")

        try:
            disponibilidade = EstoquePublicService.consultar_disponibilidade(
                produto_id=int(produto_id) if produto_id else None,
                sku=params.get("sku"),
                familia=params.get("familia"),
                espessura=int(espessura) if espessura else None,
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(disponibilidade, status=status.HTTP_200_OK)


class BaixoEstoqueView(APIView):
    def get(self, request):
        return Response(EstoquePublicService.get_alertas_baixo_estoque(), status=status.HTTP_200_OK)


class ComprometimentoLoteView(APIView):
    def get(self, request):
        lote_pcp_id = request.query_params.get("lote_pcp_id")
        if not lote_pcp_id:
            return Response({"error": "lote_pcp_id e obrigatorio."}, status=status.HTTP_400_BAD_REQUEST)
        status_reserva = request.query_params.get("status", "ativa")
        data = EstoquePublicService.consultar_comprometimento_lote(
            lote_pcp_id=lote_pcp_id,
            status=status_reserva,
        )
        return Response(data, status=status.HTTP_200_OK)


class RiscoRupturaLoteView(APIView):
    def get(self, request):
        lote_pcp_id = request.query_params.get("lote_pcp_id")
        if not lote_pcp_id:
            return Response({"error": "lote_pcp_id e obrigatorio."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            dias = int(request.query_params.get("dias", 30))
        except (TypeError, ValueError):
            return Response({"error": "dias deve ser inteiro."}, status=status.HTTP_400_BAD_REQUEST)

        data = EstoquePublicService.consultar_risco_ruptura_lote(lote_pcp_id=lote_pcp_id, dias=dias)
        return Response(data, status=status.HTTP_200_OK)


class SinaisOperacionaisView(APIView):
    def get(self, request):
        try:
            dias = int(request.query_params.get("dias", 30))
        except (TypeError, ValueError):
            return Response({"error": "dias deve ser inteiro."}, status=status.HTTP_400_BAD_REQUEST)

        familia = request.query_params.get("familia")
        apenas_risco = _parse_bool_param(request.query_params.get("apenas_risco"), default=False)

        data = EstoquePublicService.listar_sinais_operacionais(dias=dias)
        if familia:
            data = [item for item in data if item.get("familia") == familia]
        if apenas_risco:
            data = [item for item in data if item.get("risco_ruptura")]

        return Response(data, status=status.HTTP_200_OK)


class NecessidadesReposicaoView(APIView):
    def get(self, request):
        try:
            dias = int(request.query_params.get("dias", 30))
        except (TypeError, ValueError):
            return Response({"error": "dias deve ser inteiro."}, status=status.HTTP_400_BAD_REQUEST)

        familia = request.query_params.get("familia")
        data = EstoquePublicService.listar_necessidades_reposicao(dias=dias)
        if familia:
            data = [item for item in data if item.get("familia") == familia]

        return Response(data, status=status.HTTP_200_OK)


class MovimentacaoView(APIView):
    def post(self, request):
        serializer = MovimentacaoSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        usuario = request.user if request.user.is_authenticated else None

        try:
            movimentacao = MovimentacaoService.processar_movimentacao(serializer.validated_data, usuario=usuario)
            disponibilidade = EstoquePublicService.consultar_disponibilidade(
                produto_id=movimentacao.produto_id,
                espessura=movimentacao.espessura,
            )
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "message": "Movimentacao realizada com sucesso.",
                "movimentacao_id": movimentacao.id,
                "produto_id": movimentacao.produto_id,
                "disponibilidade": disponibilidade,
            },
            status=status.HTTP_200_OK,
        )


class MovimentacaoListView(APIView):
    def get(self, request):
        params = request.query_params

        try:
            limit = int(params.get("limit", 10))
            offset = int(params.get("offset", 0))
        except (ValueError, TypeError):
            return Response({"error": "limit e offset devem ser inteiros."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            produto_id = int(params["produto_id"]) if params.get("produto_id") else None
            usuario_id = int(params["usuario_id"]) if params.get("usuario_id") else None
            data_inicio = _parse_date(params["data_inicio"], "data_inicio") if params.get("data_inicio") else None
            data_fim = _parse_date(params["data_fim"], "data_fim") if params.get("data_fim") else None
        except (ValueError, TypeError) as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        movimentacoes = listar_movimentacoes(
            produto_id=produto_id,
            tipo=params.get("tipo"),
            usuario_id=usuario_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )

        total = movimentacoes.count()
        paginated = movimentacoes[offset : offset + limit]

        return Response(
            {
                "meta": {
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                    "tem_proxima": (offset + limit) < total,
                },
                "data": MovimentacaoListSerializer(paginated, many=True).data,
            }
        )


class AjusteLoteView(APIView):
    def post(self, request):
        serializer = AjusteLoteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        usuario = request.user if request.user.is_authenticated else None

        try:
            produtos = MovimentacaoService.processar_ajuste_em_lote(serializer.validated_data, usuario=usuario)
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "message": f"{len(produtos)} movimentacao(oes) processada(s) com sucesso.",
                "produtos": [{"id": p.id} for p in produtos],
            },
            status=status.HTTP_200_OK,
        )


class ReservaView(APIView):
    def post(self, request):
        serializer = ReservaCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        usuario = request.user if request.user.is_authenticated else None

        try:
            reserva = ReservaService.criar_reserva(serializer.validated_data, usuario=usuario)
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(ReservaSerializer(reserva).data, status=status.HTTP_201_CREATED)


class ReservaCancelarView(APIView):
    def post(self, request, reserva_id: int):
        usuario = request.user if request.user.is_authenticated else None
        try:
            reserva = ReservaService.cancelar_reserva(reserva_id, usuario=usuario)
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ReservaSerializer(reserva).data, status=status.HTTP_200_OK)


class ReservaConsumirView(APIView):
    def post(self, request, reserva_id: int):
        usuario = request.user if request.user.is_authenticated else None
        try:
            reserva = ReservaService.consumir_reserva(reserva_id, usuario=usuario)
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ReservaSerializer(reserva).data, status=status.HTTP_200_OK)
