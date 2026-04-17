from rest_framework import serializers
from apps.pcp.models.lote import LotePCP, AmbientePCP, ModuloPCP, PecaPCP


class PecaPCPSerializer(serializers.ModelSerializer):
    esta_finalizada = serializers.BooleanField(read_only=True)

    class Meta:
        model = PecaPCP
        fields = [
            'id', 'codigo_peca', 'descricao', 'local', 'material',
            'quantidade_planejada', 'quantidade_produzida',
            'status', 'esta_finalizada', 'roteiro', 'plano',
            'observacoes', 'atributos_tecnicos'
        ]
        read_only_fields = ['codigo_peca', 'descricao', 'roteiro', 'plano']


class ModuloPCPSerializer(serializers.ModelSerializer):
    pecas = PecaPCPSerializer(many=True, read_only=True)

    class Meta:
        model = ModuloPCP
        fields = ['id', 'nome', 'codigo_modulo', 'pecas']


class AmbientePCPSerializer(serializers.ModelSerializer):
    modulos = ModuloPCPSerializer(many=True, read_only=True)

    class Meta:
        model = AmbientePCP
        fields = ['id', 'nome', 'modulos']


class LotePCPListSerializer(serializers.ModelSerializer):
    """Lista resumida (tela de lotes pendentes)"""
    class Meta:
        model = LotePCP
        fields = ['id', 'pid', 'arquivo_original', 'cliente_nome',
                  'ordem_producao', 'status', 'data_processamento']


class LotePCPDetailSerializer(serializers.ModelSerializer):
    """Detalhe completo com hierarquia (tela de bipagem)"""
    ambientes = AmbientePCPSerializer(many=True, read_only=True)

    class Meta:
        model = LotePCP
        fields = ['id', 'pid', 'arquivo_original', 'cliente_nome',
                  'ordem_producao', 'status', 'data_processamento', 'ambientes']


class BipagemRequestSerializer(serializers.Serializer):
    """Payload simples para bipagem"""
    peca_id = serializers.IntegerField()
    quantidade = serializers.IntegerField(min_value=1)
    observacao = serializers.CharField(required=False, allow_blank=True)