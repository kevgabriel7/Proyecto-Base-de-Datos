"""
] servicios para el cálculo de tarifas de envío, peso volumétrico
y generación automática de facturación SAR.
"""
# @author hnramireza@unah.hn
# @version 0.1.0
# @date 2026/08/01

from decimal import Decimal
from django.utils import timezone
from .models import Facturas, FacturaDetalle, ConfiguracionesSar

def calcular_peso_volumetrico(largo_cm, ancho_cm, alto_cm):
    volumen_cm3 = largo_cm * ancho_cm * alto_cm
    return volumen_cm3 / Decimal('5000')

def calcular_tarifa_envio(peso_real, largo_cm, ancho_cm, alto_cm, envio):
    from .models import Tarifas
    peso_volumetrico = calcular_peso_volumetrico(largo_cm, ancho_cm, alto_cm)
    peso_cobrable = max(peso_real, peso_volumetrico)
    
    # 1. Intentar buscar tarifa exacta en la BD
    tarifa_db = Tarifas.objects.filter(
        id_via=envio.id_via,
        id_tipo_servicio=envio.id_tipo_servicio,
        id_ciudad_origen=envio.id_ciudad_origen,
        id_ciudad_destino=envio.id_ciudad_destino,
        activa=True
    ).filter(
        peso_min_kg__lte=peso_cobrable,
        peso_max_kg__gte=peso_cobrable
    ).first()

    # 2. Si no hay exacta, buscar una genérica para esa Vía (Salvavidas MVP)
    if not tarifa_db:
        tarifa_db = Tarifas.objects.filter(id_via=envio.id_via, activa=True).first()

    # 3. Calcular usando los valores reales de la Base de Datos
    if tarifa_db:
        if envio.id_via.pk == 1: # Aereo (cobra por peso)
            costo = tarifa_db.precio_base_hnl + (peso_cobrable * tarifa_db.precio_por_kg_hnl)
        else: # Maritimo (cobra por volumen m3)
            volumen_m3 = (largo_cm * ancho_cm * alto_cm) / Decimal('1000000')
            costo = tarifa_db.precio_base_hnl + (volumen_m3 * tarifa_db.precio_por_m3_hnl)
            if costo < Decimal('500'): # Costo mínimo
                costo = Decimal('500')
    else:
        # Fallback ultra extremo si la tabla esta completamente vacia
        if envio.id_via.pk == 1:
            costo = peso_cobrable * Decimal('125')
        else:
            volumen_m3 = (largo_cm * ancho_cm * alto_cm) / Decimal('1000000')
            costo = max(Decimal('500'), volumen_m3 * Decimal('5000'))

    return {
        "peso_volumetrico": peso_volumetrico,
        "peso_cobrable": peso_cobrable,
        "costo": costo
    }

def generar_factura_automatica(envio):
    cliente = envio.id_cliente
    subtotal = envio.costo_flete_hnl or Decimal('0')
    descuento_porcentaje = cliente.descuento_porcentaje or Decimal('0')
    descuento = subtotal * descuento_porcentaje / Decimal('100')
    base_gravable = subtotal - descuento
    isv = base_gravable * Decimal('0.15')
    total = base_gravable + isv
    config_sar = ConfiguracionesSar.objects.filter(activo=True).first()
    if not config_sar:
        return None
    numero = config_sar.secuencia_actual
    config_sar.secuencia_actual += 1
    config_sar.save()
    numero_factura = f"{config_sar.rango_inicial[:3]}-{config_sar.rango_inicial[4:7]}-{config_sar.rango_inicial[8:10]}-{numero:08d}"
    factura = Facturas.objects.create(
        id_cliente=cliente,
        id_sucursal=envio.id_sucursal_destino,
        id_usuario_emisor=envio.creado_por,
        numero_factura=numero_factura,
        rtn_cliente=cliente.rtn or "",
        nombre_cliente=f"{cliente.primer_nombre} {cliente.primer_apellido}".strip(),
        fecha_emision=timezone.now(),
        subtotal_hnl=subtotal,
        descuento_hnl=descuento,
        base_gravable_hnl=base_gravable,
        isv_hnl=isv,
        total_hnl=total,
        anulada=False
    )
    FacturaDetalle.objects.create(
        id_factura=factura,
        id_envio=envio,
        descripcion=f"Servicio de envío - Tracking {envio.numero_tracking}",
        cantidad=1,
        precio_unitario_hnl=subtotal,
        descuento_linea_hnl=descuento,
        subtotal_linea_hnl=base_gravable
    )
    return factura