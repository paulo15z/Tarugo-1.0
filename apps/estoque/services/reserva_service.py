from django.core.exceptions import ValidationError
from django.db import transaction
from pydantic import ValidationError as PydanticValidationError

from apps.estoque.domain.tipos import FamiliaProduto
from apps.estoque.models import Reserva
from apps.estoque.schemas.movimentacao import ReservaCreateSchema
from apps.estoque.selectors.disponibilidade_selector import (
    get_espessuras_operacionais,
    get_saldo_disponivel,
)
from apps.estoque.selectors.produto_selector import ProdutoSelector
from apps.estoque.services.movimentacao_service import MovimentacaoService


class ReservaService:
    """Service de reservas industriais com impacto em saldo disponivel."""

    @staticmethod
    @transaction.atomic
    def criar_reserva(data: dict, usuario=None) -> Reserva:
        try:
            schema = ReservaCreateSchema(**data)
        except PydanticValidationError as exc:
            raise ValidationError(f"Erro de validacao: {exc.errors()}") from exc

        produto = ProdutoSelector.get_produto_para_movimentacao(schema.produto_id)
        familia = produto.categoria.familia

        if familia == FamiliaProduto.MDF and schema.espessura is None:
            raise ValidationError("Espessura e obrigatoria para reservar produtos da familia MDF.")
        if familia == FamiliaProduto.MDF:
            espessuras_operacionais = get_espessuras_operacionais(produto)
            if espessuras_operacionais and schema.espessura not in espessuras_operacionais:
                raise ValidationError(
                    f"Espessura {schema.espessura}mm invalida para este item. "
                    f"Permitidas: {', '.join(str(e) for e in espessuras_operacionais)}mm."
                )

        saldo_disponivel = get_saldo_disponivel(produto, espessura=schema.espessura)
        if saldo_disponivel < schema.quantidade:
            raise ValidationError(
                f"Saldo disponivel insuficiente. Disponivel: {saldo_disponivel}, solicitado: {schema.quantidade}."
            )

        return Reserva.objects.create(
            produto=produto,
            espessura=schema.espessura,
            quantidade=int(schema.quantidade),
            usuario=usuario,
            observacao=schema.observacao,
            status="ativa",
            referencia_externa=schema.referencia_externa,
            origem_externa=schema.origem_externa,
            lote_pcp_id=schema.lote_pcp_id,
            modulo_id=schema.modulo_id,
            ambiente=schema.ambiente,
        )

    @staticmethod
    @transaction.atomic
    def consumir_reserva(reserva_id: int, usuario=None) -> Reserva:
        reserva = Reserva.objects.select_for_update().select_related("produto", "produto__categoria").get(id=reserva_id)
        if reserva.status != "ativa":
            raise ValidationError(f"Reserva nao pode ser consumida. Status atual: {reserva.status}")

        reserva.status = "consumida"
        reserva.save(update_fields=["status", "atualizado_em"])

        observacao = (
            f"Consumo de reserva #{reserva.id}"
            + (f" ({reserva.referencia_externa})" if reserva.referencia_externa else "")
        )

        MovimentacaoService.processar_movimentacao(
            {
                "produto_id": reserva.produto_id,
                "tipo": "saida",
                "quantidade": int(reserva.quantidade),
                "espessura": reserva.espessura,
                "observacao": observacao,
            },
            usuario=usuario,
        )

        return reserva

    @staticmethod
    @transaction.atomic
    def cancelar_reserva(reserva_id: int, usuario=None) -> Reserva:
        reserva = Reserva.objects.select_for_update().get(id=reserva_id)
        if reserva.status != "ativa":
            raise ValidationError(f"Reserva nao pode ser cancelada. Status atual: {reserva.status}")

        reserva.status = "cancelada"
        reserva.save(update_fields=["status", "atualizado_em"])
        return reserva
