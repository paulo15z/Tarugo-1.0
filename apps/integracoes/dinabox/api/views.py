"""
API Views para o app integracoes.

Padrão: Apenas serialização e chamada de Service.
Regra: Toda lógica de negócio está em services.py.
"""

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.integracoes.services import (
    DinaboxIntegrationService,
    MaterialMappingService,
    DinaboxClienteService
)
from apps.integracoes.selectors import (
    MapeamentoMaterialSelector,
    DinaboxClienteSelector
)
from .serializers import MapeamentoMaterialSerializer, DinaboxClienteIndexSerializer


@api_view(['POST'])
def processar_projeto_json(request):
    """
    API para processar um projeto JSON bruto do Dinabox.
    Retorna as três visões: operacional, logístico e administrativo.
    
    POST /api/integracoes/dinabox/projetos/processar/
    Body: JSON bruto do Dinabox
    """
    try:
        raw_data = request.data
        if not raw_data:
            return Response(
                {"error": "JSON vazio fornecido."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        result = DinaboxIntegrationService.process_raw_json(raw_data)
        
        return Response({
            "operacional": result["operacional"].model_dump(),
            "logistico": result["logistico"].model_dump(),
            "administrativo": result["administrativo"].model_dump(),
        }, status=status.HTTP_200_OK)
    
    except ValueError as e:
        return Response(
            {"error": f"Erro de validação: {str(e)}"},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {"error": f"Erro ao processar projeto: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET', 'POST'])
def mapeamento_material_list(request):
    """
    Lista todos os mapeamentos de materiais ou cria um novo.
    
    GET /api/integracoes/mapeamentos/
    POST /api/integracoes/mapeamentos/
    """
    if request.method == 'GET':
        mapeamentos = MapeamentoMaterialSelector.list_ativos()
        serializer = MapeamentoMaterialSerializer(mapeamentos, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        serializer = MapeamentoMaterialSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PATCH', 'DELETE'])
def mapeamento_material_detail(request, mapeamento_id):
    """
    Detalhes, atualização e exclusão de um mapeamento.
    
    GET /api/integracoes/mapeamentos/{id}/
    PATCH /api/integracoes/mapeamentos/{id}/
    DELETE /api/integracoes/mapeamentos/{id}/
    """
    from apps.integracoes.models import MapeamentoMaterial
    
    try:
        mapeamento = MapeamentoMaterial.objects.get(id=mapeamento_id)
    except MapeamentoMaterial.DoesNotExist:
        return Response(
            {"error": "Mapeamento não encontrado."},
            status=status.HTTP_404_NOT_FOUND
        )
    
    if request.method == 'GET':
        serializer = MapeamentoMaterialSerializer(mapeamento)
        return Response(serializer.data)
    
    elif request.method == 'PATCH':
        serializer = MapeamentoMaterialSerializer(mapeamento, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        MaterialMappingService.desativar_mapeamento(mapeamento_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
def cliente_dinabox_list(request):
    """
    Lista clientes indexados do Dinabox com filtros opcionais.
    
    GET /api/integracoes/clientes/
    GET /api/integracoes/clientes/?search=termo
    GET /api/integracoes/clientes/?type=pf
    GET /api/integracoes/clientes/?status=on
    """
    search = request.query_params.get('search', '').strip()
    customer_type = request.query_params.get('type', '').strip()
    customer_status = request.query_params.get('status', '').strip()
    
    if search:
        clientes = DinaboxClienteSelector.search_por_nome(search)
    elif customer_type:
        clientes = DinaboxClienteSelector.list_por_tipo(customer_type)
    elif customer_status:
        clientes = DinaboxClienteSelector.list_por_status(customer_status)
    else:
        clientes = DinaboxClienteSelector.list_todos()
    
    serializer = DinaboxClienteIndexSerializer(clientes, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def cliente_dinabox_detail(request, customer_id):
    """
    Detalhes de um cliente específico.
    
    GET /api/integracoes/clientes/{customer_id}/
    """
    cliente = DinaboxClienteSelector.get_by_customer_id(customer_id)
    if not cliente:
        return Response(
            {"error": "Cliente não encontrado."},
            status=status.HTTP_404_NOT_FOUND
        )
    
    serializer = DinaboxClienteIndexSerializer(cliente)
    return Response(serializer.data)


@api_view(['GET'])
def cliente_dinabox_stats(request):
    """
    Estatísticas dos clientes Dinabox.
    
    GET /api/integracoes/clientes/stats/
    """
    return Response({
        "total": DinaboxClienteSelector.count_total(),
        "por_tipo": DinaboxClienteSelector.count_por_tipo(),
        "por_status": DinaboxClienteSelector.count_por_status(),
    })
