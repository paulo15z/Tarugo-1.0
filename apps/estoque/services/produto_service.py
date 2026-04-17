from decimal import Decimal
from typing import Optional

from django.db import transaction
from django.utils.text import slugify
from pydantic import ValidationError

from apps.estoque.domain.tipos import FamiliaProduto
from apps.estoque.models.categoria import CategoriaProduto
from apps.estoque.models.produto import Produto
from apps.estoque.models.saldo_mdf import SaldoMDF
from apps.estoque.schemas.produto_schema import ProdutoCreateSchema, ProdutoUpdateSchema


class ProdutoService:
    """Service central para regras de negocio de produtos (padrao Tarugo)."""

    FITAS_BORDA_PADRAO_MM = [22, 25, 40, 64]

    @staticmethod
    def listar_produtos():
        return Produto.objects.select_related("categoria").prefetch_related("saldos_mdf").order_by("nome")

    @staticmethod
    def _garantir_categoria_fita_borda() -> CategoriaProduto:
        categoria_raiz, _ = CategoriaProduto.objects.get_or_create(
            nome="Fitas de Borda",
            parent=None,
            defaults={"familia": FamiliaProduto.FITAS_BORDA, "ordem": 2},
        )
        if categoria_raiz.familia != FamiliaProduto.FITAS_BORDA:
            categoria_raiz.familia = FamiliaProduto.FITAS_BORDA
            categoria_raiz.save(update_fields=["familia"])

        categoria_fita, _ = CategoriaProduto.objects.get_or_create(
            nome="ABS",
            parent=categoria_raiz,
            defaults={"familia": FamiliaProduto.FITAS_BORDA, "ordem": 1},
        )
        if categoria_fita.familia != FamiliaProduto.FITAS_BORDA:
            categoria_fita.familia = FamiliaProduto.FITAS_BORDA
            categoria_fita.save(update_fields=["familia"])
        return categoria_fita

    @staticmethod
    def sincronizar_fitas_borda_para_mdf(produto_mdf: Produto) -> int:
        """
        Gera/atualiza fitas de borda (22/25/40/64mm) para o acabamento do MDF.
        Retorna quantas fitas foram criadas.
        """
        if produto_mdf.categoria.familia != FamiliaProduto.MDF:
            return 0

        atributos = produto_mdf.atributos_especificos or {}
        marca = str(atributos.get("marca") or atributos.get("fabricante") or "").strip()
        acabamento = str(atributos.get("padrao") or atributos.get("acabamento") or "").strip()
        linha = str(atributos.get("linha") or "").strip()

        if not acabamento:
            return 0

        categoria_fita = ProdutoService._garantir_categoria_fita_borda()
        criadas = 0

        for largura_mm in ProdutoService.FITAS_BORDA_PADRAO_MM:
            sku_base = f"FITA-{marca}-{acabamento}-{largura_mm}MM" if marca else f"FITA-{acabamento}-{largura_mm}MM"
            sku = slugify(sku_base).upper()[:100]
            nome = f"Fita de Borda ABS {largura_mm}mm {marca} {acabamento}".replace("  ", " ").strip()

            _, created = Produto.objects.update_or_create(
                sku=sku,
                defaults={
                    "nome": nome,
                    "categoria": categoria_fita,
                    "unidade_medida": "m",
                    "quantidade": 0,
                    "estoque_minimo": 0,
                    "atributos_especificos": {
                        "tipo": "ABS",
                        "largura_mm": largura_mm,
                        "marca": marca,
                        "acabamento": acabamento,
                        "linha": linha,
                        "mdf_sku_referencia": produto_mdf.sku,
                    },
                },
            )
            criadas += int(created)

        return criadas

    @staticmethod
    @transaction.atomic
    def criar_produto(data: dict) -> Produto:
        """Cria um novo produto com validacao Pydantic."""
        try:
            schema = ProdutoCreateSchema(**data)
        except ValidationError as e:
            raise ValueError(f"Erro de validacao dos dados: {e.errors()}")

        try:
            categoria = CategoriaProduto.objects.get(id=schema.categoria_id)
        except CategoriaProduto.DoesNotExist:
            raise ValueError(f"Categoria ID {schema.categoria_id} nao encontrada.")

        familia = schema.familia or categoria.familia

        produto = Produto.objects.create(
            nome=schema.nome,
            sku=schema.sku,
            categoria=categoria,
            unidade_medida=schema.unidade_medida,
            estoque_minimo=schema.estoque_minimo,
            preco_custo=schema.preco_custo,
            lote=schema.lote,
            localizacao=schema.localizacao,
            atributos_especificos=schema.atributos_especificos or {},
        )

        if familia == FamiliaProduto.MDF:
            espessuras_padrao = [6, 15, 18, 25]
            for esp in espessuras_padrao:
                SaldoMDF.objects.get_or_create(
                    produto=produto,
                    espessura=esp,
                    defaults={"quantidade": 0},
                )
            ProdutoService.sincronizar_fitas_borda_para_mdf(produto)

        return produto

    @staticmethod
    @transaction.atomic
    def atualizar_produto(produto_id: int, data: dict) -> Produto:
        """Atualiza um produto existente."""
        try:
            produto = Produto.objects.select_for_update().get(id=produto_id)
        except Produto.DoesNotExist:
            raise ValueError(f"Produto ID {produto_id} nao encontrado.")

        schema = ProdutoUpdateSchema(**data)

        for field, value in schema.model_dump(exclude_unset=True).items():
            if field == "atributos_especificos" and value is not None:
                current = getattr(produto, field) or {}
                current.update(value)
                setattr(produto, field, current)
            else:
                setattr(produto, field, value)

        produto.save()
        return produto

    @staticmethod
    @transaction.atomic
    def atualizar_configuracoes_mdf(
        produto_id: int,
        espessura: int,
        estoque_minimo: int = None,
        preco_custo: Decimal = None,
    ) -> SaldoMDF:
        """Atualiza estoque minimo e preco de custo por espessura."""
        try:
            produto = Produto.objects.get(id=produto_id)
            saldo = SaldoMDF.objects.get(produto=produto, espessura=espessura)
        except (Produto.DoesNotExist, SaldoMDF.DoesNotExist):
            raise ValueError(f"Configuracao para {espessura}mm nao encontrada.")

        if estoque_minimo is not None:
            produto.estoque_minimo = estoque_minimo
            produto.save(update_fields=["estoque_minimo"])

        if preco_custo is not None:
            saldo.preco_custo = preco_custo
            saldo.save(update_fields=["preco_custo"])

        return saldo