from django.contrib import admin
from .models import (
    Clientes, Envios, ViasEnvio, TiposCliente, TiposServicio, EstadosEnvio,
    Paquetes, Seguimiento, Facturas, FacturaDetalle, Rutas, RutaZonas,
    AsignacionesRuta, Repartidores, Sucursales, Usuarios, Roles,
    ConfiguracionesSar, Tarifas, Ciudades, Paises, Zonas,
)


# ==================================================================
# CLIENTES
# ==================================================================
@admin.register(Clientes)
class ClientesAdmin(admin.ModelAdmin):
    list_display = ('id_cliente', 'razon_social', 'primer_nombre', 'primer_apellido', 'email', 'id_tipo_cliente', 'activo')
    list_filter = ('id_tipo_cliente', 'activo')
    search_fields = ('razon_social', 'primer_nombre', 'primer_apellido', 'email', 'rtn')


@admin.register(TiposCliente)
class TiposClienteAdmin(admin.ModelAdmin):
    list_display = ('id_tipo_cliente', 'nombre')


# ==================================================================
# ENVÍOS Y PAQUETES
# ==================================================================
@admin.register(Envios)
class EnviosAdmin(admin.ModelAdmin):
    list_display = ('id_envio', 'numero_tracking', 'id_cliente', 'id_estado_actual', 'id_ciudad_origen', 'id_ciudad_destino', 'costo_total_hnl', 'fecha_recepcion')
    list_filter = ('id_estado_actual', 'id_via', 'id_tipo_servicio')
    search_fields = ('numero_tracking', 'nombre_remitente', 'nombre_destinatario')
    date_hierarchy = 'fecha_recepcion'


@admin.register(Paquetes)
class PaquetesAdmin(admin.ModelAdmin):
    list_display = ('id_paquete', 'id_envio', 'numero_paquete', 'peso_real_kg', 'peso_volumetrico_kg', 'peso_cobrable_kg')
    search_fields = ('id_envio__numero_tracking',)


@admin.register(Seguimiento)
class SeguimientoAdmin(admin.ModelAdmin):
    list_display = ('id_seguimiento', 'id_envio', 'id_estado', 'id_repartidor', 'fecha_evento')
    list_filter = ('id_estado',)
    date_hierarchy = 'fecha_evento'


@admin.register(EstadosEnvio)
class EstadosEnvioAdmin(admin.ModelAdmin):
    list_display = ('id_estado', 'nombre', 'es_estado_final')


# ==================================================================
# FACTURACIÓN
# ==================================================================
class FacturaDetalleInline(admin.TabularInline):
    model = FacturaDetalle
    extra = 1


@admin.register(Facturas)
class FacturasAdmin(admin.ModelAdmin):
    list_display = ('id_factura', 'numero_factura', 'id_cliente', 'nombre_cliente', 'total_hnl', 'anulada', 'fecha_emision')
    list_filter = ('anulada', 'moneda', 'id_sucursal')
    search_fields = ('numero_factura', 'nombre_cliente', 'rtn_cliente')
    date_hierarchy = 'fecha_emision'
    inlines = [FacturaDetalleInline]


@admin.register(ConfiguracionesSar)
class ConfiguracionesSarAdmin(admin.ModelAdmin):
    list_display = ('id_conf_sar', 'id_sucursal', 'cai', 'rango_inicial', 'rango_final', 'secuencia_actual', 'fecha_limite_emision', 'activo')


# ==================================================================
# RUTAS, ZONAS Y REPARTO
# ==================================================================
class RutaZonasInline(admin.TabularInline):
    model = RutaZonas
    extra = 1


@admin.register(Rutas)
class RutasAdmin(admin.ModelAdmin):
    list_display = ('id_ruta', 'nombre', 'id_sucursal', 'activa')
    list_filter = ('activa', 'id_sucursal')
    inlines = [RutaZonasInline]


@admin.register(AsignacionesRuta)
class AsignacionesRutaAdmin(admin.ModelAdmin):
    list_display = ('id_asignacion', 'id_ruta', 'id_repartidor', 'fecha_inicio', 'fecha_fin', 'activo')
    list_filter = ('activo',)


@admin.register(Repartidores)
class RepartidoresAdmin(admin.ModelAdmin):
    list_display = ('id_repartidor', 'id_usuario', 'numero_licencia', 'tipo_vehiculo', 'placa_vehiculo', 'activo')
    list_filter = ('activo',)


@admin.register(Zonas)
class ZonasAdmin(admin.ModelAdmin):
    list_display = ('id_zona', 'nombre', 'id_ciudad')


# ==================================================================
# INFRAESTRUCTURA (sucursales, usuarios/staff, roles)
# ==================================================================
@admin.register(Sucursales)
class SucursalesAdmin(admin.ModelAdmin):
    list_display = ('id_sucursal', 'codigosar', 'nombre', 'id_ciudad', 'activa')
    list_filter = ('activa',)


@admin.register(Usuarios)
class UsuariosAdmin(admin.ModelAdmin):
    list_display = ('id_usuario', 'primer_nombre', 'primer_apellido', 'email', 'id_sucursal', 'id_rol', 'activo')
    list_filter = ('id_rol', 'id_sucursal', 'activo')
    search_fields = ('primer_nombre', 'primer_apellido', 'email', 'dni')


@admin.register(Roles)
class RolesAdmin(admin.ModelAdmin):
    list_display = ('id_rol', 'nombre')


# ==================================================================
# CATÁLOGOS Y TARIFAS
# ==================================================================
@admin.register(ViasEnvio)
class ViasEnvioAdmin(admin.ModelAdmin):
    list_display = ('id_via', 'nombre')


@admin.register(TiposServicio)
class TiposServicioAdmin(admin.ModelAdmin):
    list_display = ('id_tipo_servicio', 'nombre', 'factor_precio')


@admin.register(Tarifas)
class TarifasAdmin(admin.ModelAdmin):
    list_display = ('id_tarifa', 'id_via', 'id_tipo_servicio', 'id_ciudad_origen', 'id_ciudad_destino', 'peso_min_kg', 'peso_max_kg', 'precio_base_hnl', 'precio_por_kg_hnl', 'precio_por_m3_hnl', 'activa')
    list_filter = ('id_via', 'id_tipo_servicio', 'activa')


@admin.register(Ciudades)
class CiudadesAdmin(admin.ModelAdmin):
    list_display = ('id_ciudad', 'nombre', 'id_pais')
    list_filter = ('id_pais',)
    search_fields = ('nombre',)


@admin.register(Paises)
class PaisesAdmin(admin.ModelAdmin):
    list_display = ('id_pais', 'nombre', 'codigo_pais')