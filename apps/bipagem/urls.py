from django.urls import path

from . import views

app_name = 'bipagem'

urlpatterns = [
    path('', views.index, name='index'),
    path('lote/<str:numero_pedido>/', views.pedido_detalhe, name='pedido_detalhe'),
    path('lote/<str:numero_pedido>/estornar/', views.estornar_peca_view, name='estornar_peca'),
]
