from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_redirect, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('portal/', views.portal_cliente, name='portal_cliente'),
    path('mis-paquetes/', views.mis_paquetes, name='mis_paquetes'),
    path('rastreo/', views.rastreo, name='rastreo'),
    path('facturas/', views.facturas, name='facturas'),
    path('mis-datos/', views.mis_datos, name='mis_datos'),
    path('calculadora/', views.calculadora, name='calculadora'),
    path('admin-portal/', views.portal_empleado, name='portal_empleado'),
    path('admin-portal/recepcion/', views.recepcion_paquetes, name='recepcion_paquetes'),
    path('admin-portal/tracking/', views.actualizar_rastreo, name='actualizar_rastreo'),
    path('admin-portal/caja/', views.facturacion_sar, name='facturacion_sar'),
]