from django.urls import path

from .views import BipagemView, LotePecasView, LotePreviewView

app_name = 'bipagem-api'

urlpatterns = [
    path('bipagem/', BipagemView.as_view(), name='bipagem'),
    path('lotes/<str:pid>/preview/', LotePreviewView.as_view(), name='lote-preview'),
    path('lotes/<str:pid>/pecas/', LotePecasView.as_view(), name='lote-pecas'),
]
