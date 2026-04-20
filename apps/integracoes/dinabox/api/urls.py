from django.urls import path
from . import views

app_name = "dinabox_api"

urlpatterns = [
    # Processamento de projetos
    path('projetos/processar/', views.processar_projeto_json, name='processar-projeto'),
    
    # Mapeamentos de materiais
    path('mapeamentos/', views.mapeamento_material_list, name='mapeamento-list'),
    path('mapeamentos/<int:mapeamento_id>/', views.mapeamento_material_detail, name='mapeamento-detail'),
    
    # Clientes Dinabox
    path('clientes/', views.cliente_dinabox_list, name='cliente-list'),
    path('clientes/stats/', views.cliente_dinabox_stats, name='cliente-stats'),
    path('clientes/<str:customer_id>/', views.cliente_dinabox_detail, name='cliente-detail'),
]
