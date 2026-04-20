from rest_framework import serializers
from apps.integracoes.models import MapeamentoMaterial, DinaboxClienteIndex


class MapeamentoMaterialSerializer(serializers.ModelSerializer):
    """Serializer para mapeamentos de materiais Dinabox."""
    
    class Meta:
        model = MapeamentoMaterial
        fields = ['id', 'nome_dinabox', 'produto', 'fator_conversao', 'ativo']
        read_only_fields = ['id']


class DinaboxClienteIndexSerializer(serializers.ModelSerializer):
    """Serializer para índice de clientes Dinabox."""
    
    class Meta:
        model = DinaboxClienteIndex
        fields = ['customer_id', 'customer_name', 'customer_type', 'customer_status', 'synced_at']
        read_only_fields = ['synced_at']
