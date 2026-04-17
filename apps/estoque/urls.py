from django.urls import path
from . import views

app_name = "estoque"

urlpatterns = [
    path("", views.lista_produtos, name="lista_produtos"),
    path("dashboard/", views.dashboard_operacional, name="dashboard_operacional"),
    path("movimentacao/", views.movimentacao_create, name="movimentacao_create"),
    path("produtos/novo/", views.produto_create, name="produto_create"),
    path("reservas/", views.lista_reservas, name="lista_reservas"),
    path("reservas/nova/", views.reserva_create, name="reserva_create"),
    path("reservas/<int:reserva_id>/consumir/", views.reserva_consumir, name="reserva_consumir"),
    path("reservas/<int:reserva_id>/cancelar/", views.reserva_cancelar, name="reserva_cancelar"),
    path("produtos/<int:produto_id>/config/", views.produto_config_update, name="produto_config_update"),
]
