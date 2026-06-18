from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.core import views as core_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', core_views.entrada, name='entrada'),

    # Autenticacao
    path('login/', core_views.entrada, name='login'),
    path('logout/', core_views.EntradaLogoutView.as_view(), name='logout'),

    # Apps
    path('pcp/', include('apps.pcp.urls')),
    path('api/pcp/', include('apps.pcp.api.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
