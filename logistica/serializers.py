from rest_framework import serializers
from .models import Clientes, Envios, Facturas, Paquetes, Seguimiento, EstadosEnvio, FacturaDetalle,Ciudades, TiposServicio, ViasEnvio, Tarifas, EstadosEnvio
from decimal import Decimal

class ClientePerfilSerializer(serializers.ModelSerializer):
    tipo_cliente = serializers.CharField(source='id_tipo_cliente.nombre', read_only=True)
    ciudad = serializers.CharField(source='id_ciudad.nombre', read_only=True)

    class Meta:
        model = Clientes
        fields = [
            'id_cliente', 'razon_social', 'primer_nombre', 'primer_apellido',
            'email', 'telefono', 'direccion', 'ciudad', 'tipo_cliente',
            'descuento_porcentaje',
        ]


class SeguimientoSerializer(serializers.ModelSerializer):
    estado = serializers.CharField(source='id_estado.nombre', read_only=True)

    class Meta:
        model = Seguimiento
        fields = ['id_seguimiento', 'estado', 'ubicacion_descripcion', 'observaciones', 'fecha_evento']


class PaqueteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Paquetes
        fields = [
            'id_paquete', 'numero_paquete', 'descripcion_contenido',
            'peso_real_kg', 'peso_volumetrico_kg', 'peso_cobrable_kg',
        ]


class EnvioListSerializer(serializers.ModelSerializer):
    estado = serializers.CharField(source='id_estado_actual.nombre', read_only=True)
    servicio = serializers.CharField(source='id_tipo_servicio.nombre', read_only=True)
    via = serializers.CharField(source='id_via.nombre', read_only=True)
    ciudad_origen = serializers.CharField(source='id_ciudad_origen.nombre', read_only=True)
    ciudad_destino = serializers.CharField(source='id_ciudad_destino.nombre', read_only=True)

    class Meta:
        model = Envios
        fields = [
            'id_envio', 'numero_tracking', 'estado', 'servicio', 'via',
            'ciudad_origen', 'ciudad_destino', 'costo_total_hnl',
            'fecha_recepcion', 'fecha_estimada', 'fecha_entrega_real',
        ]


class EnvioDetailSerializer(EnvioListSerializer):
    paquetes = PaqueteSerializer(source='paquetes_set', many=True, read_only=True)
    seguimiento = SeguimientoSerializer(source='seguimiento_set', many=True, read_only=True)

    class Meta(EnvioListSerializer.Meta):
        fields = EnvioListSerializer.Meta.fields + [
            'nombre_remitente', 'nombre_destinatario', 'direccion_destino',
            'valor_declarado_hnl', 'observaciones', 'paquetes', 'seguimiento',
        ]
        

class FacturaDetalleSerializer(serializers.ModelSerializer):
    class Meta:
        model = FacturaDetalle
        fields = ['id_detalle', 'descripcion', 'cantidad', 'precio_unitario_hnl', 'descuento_linea_hnl', 'subtotal_linea_hnl']


class FacturaListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Facturas
        fields = ['id_factura', 'numero_factura', 'fecha_emision', 'subtotal_hnl', 'descuento_hnl', 'total_hnl', 'moneda', 'anulada']


class FacturaDetailSerializer(FacturaListSerializer):
    detalle = FacturaDetalleSerializer(source='facturadetalle_set', many=True, read_only=True)

    class Meta(FacturaListSerializer.Meta):
        fields = FacturaListSerializer.Meta.fields + ['rtn_cliente', 'nombre_cliente', 'base_gravable_hnl', 'isv_hnl', 'motivo_anulacion', 'detalle']
        
class RastreoPublicoSerializer(serializers.ModelSerializer):
    estado = serializers.CharField(source='id_estado_actual.nombre', read_only=True)
    servicio = serializers.CharField(source='id_tipo_servicio.nombre', read_only=True)
    via = serializers.CharField(source='id_via.nombre', read_only=True)
    ciudad_origen = serializers.CharField(source='id_ciudad_origen.nombre', read_only=True)
    ciudad_destino = serializers.CharField(source='id_ciudad_destino.nombre', read_only=True)
    seguimiento = SeguimientoSerializer(source='seguimiento_set', many=True, read_only=True)

    class Meta:
        model = Envios
        # ojo: a propósito NO exponemos costo, remitente, ni dirección exacta —
        # es público, cualquiera con el tracking lo puede consultar
        fields = [
            'numero_tracking', 'estado', 'servicio', 'via',
            'ciudad_origen', 'ciudad_destino', 'nombre_destinatario',
            'fecha_recepcion', 'fecha_estimada', 'fecha_entrega_real', 'seguimiento',
        ]
        
class CiudadSerializer(serializers.ModelSerializer):
    pais = serializers.CharField(source='id_pais.nombre', read_only=True)

    class Meta:
        model = Ciudades
        fields = ['id_ciudad', 'nombre', 'pais']


class TipoServicioSerializer(serializers.ModelSerializer):
    class Meta:
        model = TiposServicio
        fields = ['id_tipo_servicio', 'nombre', 'factor_precio', 'descripcion']


class ViaEnvioSerializer(serializers.ModelSerializer):
    class Meta:
        model = ViasEnvio
        fields = ['id_via', 'nombre', 'descripcion']


class AnunciarPaqueteSerializer(serializers.Serializer):
    """No es un ModelSerializer: valida el input del cliente para armar un envío nuevo."""
    id_ciudad_origen = serializers.IntegerField()
    id_ciudad_destino = serializers.IntegerField()
    id_tipo_servicio = serializers.IntegerField()
    id_via = serializers.IntegerField()
    nombre_destinatario = serializers.CharField(max_length=200)
    telefono_destinatario = serializers.CharField(max_length=20, required=False, allow_blank=True)
    direccion_destino = serializers.CharField()
    descripcion_contenido = serializers.CharField(required=False, allow_blank=True)
    peso_real_kg = serializers.DecimalField(max_digits=8, decimal_places=3)
    largo_cm = serializers.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0'))
    ancho_cm = serializers.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0'))
    alto_cm = serializers.DecimalField(max_digits=8, decimal_places=2, default=Decimal('0'))
    valor_declarado_hnl = serializers.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))