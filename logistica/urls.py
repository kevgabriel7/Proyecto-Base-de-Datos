from django.urls import path
from . import views

urlpatterns = [
    path('portal/', views.portal_cliente, name='portal_cliente'),
    path('mis-paquetes/', views.mis_paquetes, name='mis_paquetes'),
    path('rastreo/', views.rastreo, name='rastreo'),
    path('facturas/', views.facturas, name='facturas'),
    path('mis-datos/', views.mis_datos, name='mis_datos'),
    path('calculadora/', views.calculadora, name='calculadora'),
]