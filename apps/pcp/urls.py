"""
Rotas do app PCP.

O PCP é o dono do ciclo de vida dos lotes:
  - Processar arquivo
  - Liberar para bipagem
  - Bloquear/reabrir lote
  - Liberar para viagem/expedição
  - Download do XLS gerado
  - Histórico
"""
from django.urls import path
from . import views

app_name = 'pcp'

urlpatterns = [
    # Interface principal
    path('', views.pcp_index, name='index'),

    # Processamento de arquivo
    path('processar/', views.pcp_processar, name='processar'),

    # Histórico de processamentos
    path('historico/', views.pcp_historico, name='historico'),
    path('lote/<str:pid>/retorno/', views.pcp_retorno_lote, name='retorno'),
    path('lote/<str:pid>/retorno/relatorio/', views.pcp_retorno_relatorio, name='retorno-relatorio'),

    # Ciclo de vida do lote para bipagem (PCP é dono)
    path('lote/<str:pid>/liberar/', views.pcp_liberar, name='liberar'),
    path('lote/<str:pid>/bloquear/', views.pcp_bloquear, name='bloquear'),
    path('lote/<str:pid>/reabrir/', views.pcp_reabrir, name='reabrir'),
    path('lote/<str:pid>/remover/', views.pcp_remover, name='remover'),

    # Ciclo de vida para expedição/viagem
    path('lote/<str:pid>/liberar-viagem/', views.pcp_liberar_viagem, name='liberar-viagem'),

    # Download do roteiro gerado
    path('download/<str:pid>/', views.pcp_download, name='download'),
]
