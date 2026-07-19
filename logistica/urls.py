from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LoginClienteView, RegistroClienteView, MiPerfilView, MisEnviosViewSet, MisFacturasViewSet, RastreoPublicoView, catalogos_view, AnunciarPaqueteView

router = DefaultRouter()
router.register('envios', MisEnviosViewSet, basename='envios')
router.register('facturas', MisFacturasViewSet, basename='facturas')

urlpatterns = [
    path('login/', LoginClienteView.as_view(), name='login_cliente'),
    path('registro/', RegistroClienteView.as_view(), name='registro_cliente'),
    path('perfil/', MiPerfilView.as_view(), name='mi_perfil'),
    path('rastrear/<uuid:numero_tracking>/', RastreoPublicoView.as_view(), name='rastreo_publico'),
    path('catalogos/', catalogos_view, name='catalogos'),
    path('anunciar-paquete/', AnunciarPaqueteView.as_view(), name='anunciar_paquete'),
    path('', include(router.urls)),
]