from django.core.exceptions import ValidationError
from django.db import transaction
from pydantic import ValidationError as PydanticValidationError

from apps.estoque.domain.tipos import FamiliaProduto
from apps.estoque.models import Movimentacao, Produto, SaldoMDF
from apps.estoque.schemas.movimentacao import MovimentacaoCreateSchema
from apps.estoque.selectors.disponibilidade_selector import (
    get_espessuras_operacionais,
    get_saldo_reservado,
)
from apps.estoque.selectors.produto_selector import ProdutoSelector


class MovimentacaoService:
    """Service central do estoque industrial."""

    @staticmethod
    @transaction.atomic
    def processar_movimentacao(data: dict, usuario=None) -> Movimentacao:
        try:
            schema = MovimentacaoCreateSchema(**data)
        except PydanticValidationError as exc:
            raise ValidationError(f"Erro de validacao: {exc.errors()}") from exc

        produto = ProdutoSelector.get_produto_para_movimentacao(schema.produto_id)
        tipo = schema.tipo.value
        quantidade = int(schema.quantidade)
        espessura = schema.espessura
        observacao = schema.observacao

        familia = produto.categoria.familia
        if familia == FamiliaProduto.MDF:
            if espessura is None:
                raise ValidationError("Espessura e obrigatoria para produtos da familia MDF.")
            espessuras_operacionais = get_espessuras_operacionais(produto)
            if espessuras_operacionais and espessura not in espessuras_operacionais:
                raise ValidationError(
                    f"Espessura {espessura}mm invalida para este item. "
                    f"Permitidas: {', '.join(str(e) for e in espessuras_operacionais)}mm."
                )

            saldo_mdf, _ = SaldoMDF.objects.get_or_create(produto=produto, espessura=espessura)
            reservado = get_saldo_reservado(produto, espessura=espessura)
            disponivel = max(0, saldo_mdf.quantidade - reservado)

            if tipo == "saida" and disponivel < quantidade:
                raise ValidationError(
                    f"Saldo disponivel insuficiente para {espessura}mm. Disponivel: {disponivel}, solicitado: {quantidade}."
                )
            if tipo == "ajuste" and quantidade < reservado:
                raise ValidationError(
                    f"Ajuste invalido. Reservado para {espessura}mm: {reservado}. Novo saldo fisico nao pode ser menor que o reservado."
                )

            if tipo == "entrada":
                saldo_mdf.quantidade += quantidade
            elif tipo == "saida":
                saldo_mdf.quantidade -= quantidade
            elif tipo == "ajuste":
                saldo_mdf.quantidade = quantidade

            saldo_mdf.save(update_fields=["quantidade"])
        else:
            reservado = get_saldo_reservado(produto)
            disponivel = max(0, int(produto.quantidade) - reservado)

            if tipo == "saida" and disponivel < quantidade:
                raise ValidationError(
                    f"Saldo disponivel insuficiente. Disponivel: {disponivel}, solicitado: {quantidade}."
                )
            if tipo == "ajuste" and quantidade < reservado:
                raise ValidationError(
                    f"Ajuste invalido. Reservado: {reservado}. Novo saldo fisico nao pode ser menor que o reservado."
                )

            if tipo == "entrada":
                produto.quantidade += quantidade
            elif tipo == "saida":
                produto.quantidade -= quantidade
            elif tipo == "ajuste":
                produto.quantidade = quantidade

            produto.save(update_fields=["quantidade", "atualizado_em"])

        return Movimentacao.objects.create(
            produto=produto,
            tipo=tipo,
            espessura=espessura,
            quantidade=quantidade,
            usuario=usuario,
            observacao=observacao,
        )

    @staticmethod
    @transaction.atomic
    def processar_ajuste_em_lote(data: dict, usuario=None) -> list[Produto]:
        movimentacoes_data = data["movimentacoes"]
        if not movimentacoes_data:
            raise ValidationError("A lista de movimentacoes nao pode estar vazia.")

        produtos_atualizados = []
        for mov_data in movimentacoes_data:
            movimentacao = MovimentacaoService.processar_movimentacao(mov_data, usuario=usuario)
            produtos_atualizados.append(movimentacao.produto)

        return produtos_atualizados
