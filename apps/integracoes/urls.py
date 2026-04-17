from django.urls import path

from . import views

app_name = "integracoes"

urlpatterns = [
    path("dinabox/conectar/", views.dinabox_conectar, name="dinabox-conectar"),
    path("dinabox/capacidades/", views.dinabox_capacidades, name="dinabox-capacidades"),
    path("dinabox/desconectar/", views.dinabox_desconectar, name="dinabox-desconectar"),
    path("dinabox/test-auth/", views.dinabox_test_auth, name="dinabox-test-auth"),
    path("dinabox/clientes/", views.dinabox_clientes_list, name="dinabox-clientes-list"),
    path("dinabox/clientes/criar/", views.dinabox_cliente_criar, name="dinabox-cliente-criar"),
    path("dinabox/clientes/<str:customer_id>/", views.dinabox_cliente_detail, name="dinabox-cliente-detail"),
    path("dinabox/clientes/<str:customer_id>/atualizar/", views.dinabox_cliente_atualizar, name="dinabox-cliente-atualizar"),
    path("dinabox/clientes/<str:customer_id>/excluir/", views.dinabox_cliente_excluir, name="dinabox-cliente-excluir"),
    path("dinabox/materiais/", views.dinabox_materiais_list, name="dinabox-materiais-list"),
    path("dinabox/etiquetas/", views.dinabox_etiquetas_list, name="dinabox-etiquetas-list"),
    path("dinabox/etiquetas/criar/", views.dinabox_etiqueta_criar, name="dinabox-etiqueta-criar"),
    path("dinabox/etiquetas/excluir/", views.dinabox_etiqueta_excluir, name="dinabox-etiqueta-excluir"),
    path("dinabox/projetos/", views.dinabox_projetos_list, name="dinabox-projetos-list"),
    path("dinabox/projetos/<str:project_id>/", views.dinabox_projeto_detail, name="dinabox-projeto-detail"),
    path("dinabox/lotes/", views.dinabox_lotes_list, name="dinabox-lotes-list"),
    path("dinabox/lotes/<str:group_id>/", views.dinabox_lote_detail, name="dinabox-lote-detail"),
]
