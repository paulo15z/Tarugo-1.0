from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LotePCPViewSet

router = DefaultRouter()
router.register(r'lotes', LotePCPViewSet, basename='lote-pcp')

urlpatterns = [
    path('', include(router.urls)),
]