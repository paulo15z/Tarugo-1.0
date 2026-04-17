# apps/bipagem/api/serializers.py
from rest_framework import serializers
from apps.bipagem.models import Pedido, OrdemProducao, Modulo, Peca, EventoBipagem, LoteProducao


class LoteProducaoSerializer(serializers.ModelSerializer):
    total_pecas = serializers.IntegerField(read_only=True)
    pecas_bipadas = serializers.IntegerField(read_only=True)
    percentual = serializers.FloatField(read_only=True)

    class Meta:
        model = LoteProducao
        fields = [
            'id', 'numero_lote', 'processamento_pcp', 'data_criacao',
            'liberado_para_bipagem', 'bloqueado_motivo', 'observacoes',
            'total_pecas', 'pecas_bipadas', 'percentual'
        ]


class EventoBipagemSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventoBipagem
        fields = ['id', 'momento', 'usuario', 'localizacao']


class PecaListSerializer(serializers.ModelSerializer):
    """Serializer para listagem (mais leve)"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Peca
        fields = [
            'id', 'id_peca', 'descricao', 'local', 'material',
            'status', 'status_display', 'data_bipagem',
            'quantidade', 'plano_corte'
        ]


class PecaDetailSerializer(serializers.ModelSerializer):
    """Serializer completo com histórico"""
    bipagens = EventoBipagemSerializer(many=True, read_only=True)
    modulo_nome = serializers.CharField(source='modulo.nome_modulo', read_only=True)
    ordem_ambiente = serializers.CharField(source='modulo.ordem_producao.nome_ambiente', read_only=True)
    pedido_numero = serializers.CharField(source='modulo.ordem_producao.pedido.numero_pedido', read_only=True)
    
    class Meta:
        model = Peca
        fields = [
            'id', 'id_peca', 'descricao', 'local', 'material',
            'largura_mm', 'altura_mm', 'espessura_mm', 'quantidade',
            'roteiro', 'plano_corte', 'status', 'data_bipagem',
            'modulo_nome', 'ordem_ambiente', 'pedido_numero',
            'bipagens'
        ]


class ModuloSerializer(serializers.ModelSerializer):
    total_pecas = serializers.SerializerMethodField()
    pecas_bipadas = serializers.SerializerMethodField()
    percentual_concluido = serializers.SerializerMethodField()
    
    class Meta:
        model = Modulo
        fields = ['id', 'referencia_modulo', 'nome_modulo',
                  'total_pecas', 'pecas_bipadas', 'percentual_concluido']
    
    def get_total_pecas(self, obj):
        return obj.total_pecas
    
    def get_pecas_bipadas(self, obj):
        return obj.pecas_bipadas
    
    def get_percentual_concluido(self, obj):
        return obj.percentual_concluido


class OrdemProducaoSerializer(serializers.ModelSerializer):
    total_pecas = serializers.SerializerMethodField()
    pecas_bipadas = serializers.SerializerMethodField()
    percentual_concluido = serializers.SerializerMethodField()
    
    class Meta:
        model = OrdemProducao
        fields = ['id', 'nome_ambiente', 'referencia_principal',
                  'total_pecas', 'pecas_bipadas', 'percentual_concluido']
    
    def get_total_pecas(self, obj):
        return obj.total_pecas  # vai usar property do model
    
    def get_pecas_bipadas(self, obj):
        return obj.pecas_bipadas
    
    def get_percentual_concluido(self, obj):
        return obj.percentual_concluido


class PedidoSerializer(serializers.ModelSerializer):
    total_pecas = serializers.SerializerMethodField()
    pecas_bipadas = serializers.SerializerMethodField()
    percentual_concluido = serializers.SerializerMethodField()
    
    class Meta:
        model = Pedido
        fields = ['id', 'numero_pedido', 'cliente_nome',
                  'total_pecas', 'pecas_bipadas', 'percentual_concluido']
    
    def get_total_pecas(self, obj):
        return obj.total_pecas
    
    def get_pecas_bipadas(self, obj):
        return obj.pecas_bipadas
    
    def get_percentual_concluido(self, obj):
        total = obj.total_pecas
        if total == 0:
            return 0
        return int((obj.pecas_bipadas / total) * 100)