from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from apps.bipagem.services.importador_service import importar_csv

class ImportarCSVView(APIView):
    """
    POST /api/bipagem/importar-csv/
    Recebe um JSON com as linhas do CSV para importação.
    """
    def post(self, request):
        # O service já espera um dicionário e faz a validação com Pydantic
        resultado = importar_csv(request.data)
        
        if resultado.get('sucesso'):
            return Response(resultado, status=status.HTTP_201_CREATED)
        else:
            return Response(
                resultado, 
                status=status.HTTP_400_BAD_REQUEST
            )
