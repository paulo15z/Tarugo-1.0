from rest_framework import serializers

from apps.estoque.domain.tipos import TipoMovimentacao
from apps.estoque.models.movimentacao import Movimentacao
from apps.estoque.models.produto import Produto
from apps.estoque.models.reserva import Reserva


class ProdutoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Produto
        fields = ["id", "nome", "sku", "quantidade", "estoque_minimo", "criado_em"]
        read_only_fields = ["id", "criado_em"]


class ProdutoListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Produto
        fields = [
            "id",
            "nome",
            "sku",
            "unidade_medida",
            "estoque_minimo",
            "localizacao",
            "lote",
            "categoria",
        ]
        read_only_fields = fields


class MovimentacaoSerializer(serializers.Serializer):
    produto_id = serializers.IntegerField()
    quantidade = serializers.IntegerField(min_value=1)
    tipo = serializers.ChoiceField(choices=[tipo.value for tipo in TipoMovimentacao])
    espessura = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    observacao = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class MovimentacaoListSerializer(serializers.ModelSerializer):
    produto_nome = serializers.CharField(source="produto.nome", read_only=True)
    produto_sku = serializers.CharField(source="produto.sku", read_only=True)
    usuario_username = serializers.CharField(source="usuario.username", read_only=True, default=None)
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)

    class Meta:
        model = Movimentacao
        fields = [
            "id",
            "produto",
            "produto_nome",
            "produto_sku",
            "tipo",
            "tipo_display",
            "espessura",
            "quantidade",
            "usuario",
            "usuario_username",
            "observacao",
            "criado_em",
        ]
        read_only_fields = fields


class AjusteLoteSerializer(serializers.Serializer):
    movimentacoes = MovimentacaoSerializer(many=True)


class ReservaCreateSerializer(serializers.Serializer):
    produto_id = serializers.IntegerField()
    quantidade = serializers.IntegerField(min_value=1)
    espessura = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    referencia_externa = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    origem_externa = serializers.ChoiceField(choices=["pcp", "manual", "integracao"], default="pcp")
    observacao = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    lote_pcp_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    modulo_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    ambiente = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class ReservaSerializer(serializers.ModelSerializer):
    produto_nome = serializers.CharField(source="produto.nome", read_only=True)
    produto_sku = serializers.CharField(source="produto.sku", read_only=True)

    class Meta:
        model = Reserva
        fields = [
            "id",
            "produto",
            "produto_nome",
            "produto_sku",
            "quantidade",
            "espessura",
            "lote_pcp_id",
            "modulo_id",
            "ambiente",
            "status",
            "referencia_externa",
            "origem_externa",
            "observacao",
            "criado_em",
        ]
        read_only_fields = fields
