"""
 servicios para el cálculo de tarifas de envío, peso volumétrico
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

def calcular_tarifa_envio(peso_real, largo_cm, ancho_cm, alto_cm, id_via):
    peso_volumetrico = calcular_peso_volumetrico(largo_cm, ancho_cm, alto_cm)
    peso_cobrable = max(peso_real, peso_volumetrico)
    if id_via == 1:
        costo = peso_cobrable * Decimal('125')
    elif id_via == 2:
        volumen_m3 = (largo_cm * ancho_cm * alto_cm) / Decimal('1000000')
        costo = volumen_m3 * Decimal('5000')
        if costo < Decimal('500'):
            costo = Decimal('500')
    else:
        costo = Decimal('0')
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