from django.urls import path

from apps.estoque.api.views import (
    ProdutoCreateView,
    ProdutoListView,
    DisponibilidadeView,
    ComprometimentoLoteView,
    RiscoRupturaLoteView,
    SinaisOperacionaisView,
    NecessidadesReposicaoView,
    MovimentacaoView,
    MovimentacaoListView,
    AjusteLoteView,
    BaixoEstoqueView,
    ReservaView,
    ReservaCancelarView,
    ReservaConsumirView,
)

urlpatterns = [
    path('produtos/listar/', ProdutoListView.as_view(), name='produto-list'),
    path('produtos/', ProdutoCreateView.as_view(), name='produto-create'),
    path('disponibilidade/', DisponibilidadeView.as_view(), name='disponibilidade'),
    path('comprometimento/lote/', ComprometimentoLoteView.as_view(), name='comprometimento-lote'),
    path('riscos/lote/', RiscoRupturaLoteView.as_view(), name='riscos-lote'),
    path('sinais-operacionais/', SinaisOperacionaisView.as_view(), name='sinais-operacionais'),
    path('necessidades/reposicao/', NecessidadesReposicaoView.as_view(), name='necessidades-reposicao'),
    path('movimentar/', MovimentacaoView.as_view(), name='movimentacao-create'),
    path('movimentacoes/', MovimentacaoListView.as_view(), name='movimentacao-list'),
    path('movimentar/lote/', AjusteLoteView.as_view(), name='movimentacao-lote'),
    path('reservas/', ReservaView.as_view(), name='reserva-create'),
    path('reservas/<int:reserva_id>/cancelar/', ReservaCancelarView.as_view(), name='reserva-cancelar'),
    path('reservas/<int:reserva_id>/consumir/', ReservaConsumirView.as_view(), name='reserva-consumir'),
    path('produtos/baixo-estoque/', BaixoEstoqueView.as_view(), name='produto-baixo-estoque'),
]
