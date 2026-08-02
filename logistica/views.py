import uuid
from decimal import Decimal
from django.db import transaction
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login as django_login, logout as django_logout
from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone
from django.core.exceptions import ValidationError

from .models import (
    Clientes, Sucursales, Envios, Facturas, Seguimiento,
    Usuarios, Paquetes, Tarifas, ViasEnvio, TiposServicio,
    EstadosEnvio, Rutas, Ciudades, ConfiguracionesSar, FacturaDetalle, TiposCliente
)
from .services import calcular_tarifa_envio, generar_factura_automatica

def get_cliente_actual(request):
    id_cliente = request.session.get('id_cliente')
    if not id_cliente:
        return None
    try:
        return Clientes.objects.get(id_cliente=id_cliente, activo=True)
    except Clientes.DoesNotExist:
        return None

def home_redirect(request):
    if request.session.get('id_cliente'):
        return redirect('portal_cliente')
    return redirect('login')

def login_view(request):
    error = None
    if request.method == 'POST':
        identificador = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=identificador, password=password)
        if user is None:
            try:
                u = User.objects.get(email=identificador)
                user = authenticate(request, username=u.username, password=password)
            except User.DoesNotExist:
                user = None
        if user is not None and user.is_staff:
            django_login(request, user)
            return redirect('/admin/')
        try:
            cliente = Clientes.objects.get(email=identificador, activo=True)
        except Clientes.DoesNotExist:
            cliente = None
        if cliente and cliente.password_hash and check_password(password, cliente.password_hash):
            request.session['id_cliente'] = cliente.id_cliente
            return redirect('portal_cliente')
        error = 'Correo o contraseña incorrectos.'
    return render(request, 'logistica/login.html', {'error': error})

def logout_view(request):
    request.session.flush()
    django_logout(request)
    return redirect('login')

def portal_cliente(request):
    cliente = get_cliente_actual(request)
    if not cliente:
        return redirect('login')
    sucursal_miami = Sucursales.objects.filter(nombre__icontains='Miami').first()
    nombre_completo = ""
    direccion_local = ""
    telefono_local = ""
    email_local = ""
    ciudad_local = ""
    tipo_cliente = ""
    descuento = 0
    if cliente:
        nombre_completo = f"{cliente.primer_nombre or ''} {cliente.primer_apellido or ''}".strip().upper()
        direccion_local = cliente.direccion or "Sin dirección"
        telefono_local = cliente.telefono or "N/D"
        email_local = cliente.email or "N/D"
        ciudad_local = cliente.id_ciudad.nombre if cliente.id_ciudad else "N/D"
        tipo_cliente = cliente.id_tipo_cliente.nombre if cliente.id_tipo_cliente else ""
        if tipo_cliente.lower() == "normal":
            tipo_cliente = ""
        descuento = cliente.descuento_porcentaje
    context = {
        'nombre_completo': nombre_completo,
        'direccion_local': direccion_local,
        'telefono_local': telefono_local,
        'email_local': email_local,
        'ciudad_local': ciudad_local,
        'tipo_cliente': tipo_cliente,
        'descuento': descuento,
        'sucursal_miami': sucursal_miami,
    }
    return render(request, 'logistica/portal_cliente.html', context)

def registro_cliente(request):
    if request.method == "POST":
        nombre = request.POST.get("primer_nombre")
        apellido = request.POST.get("primer_apellido")
        email = request.POST.get("email")
        password = request.POST.get("password")
        tipo_cliente = TiposCliente.objects.first()
        ciudad = Ciudades.objects.first()
        cliente = Clientes.objects.create(
            id_tipo_cliente=tipo_cliente,
            id_ciudad=ciudad,
            razon_social="",
            primer_nombre=nombre,
            primer_apellido=apellido,
            email=email,
            password_hash=make_password(password),
            activo=True,
            descuento_porcentaje=Decimal("0")
        )
        messages.success(request, "Cuenta creada correctamente")
        return redirect("login")
    return render(request, "logistica/registro_cliente.html")

def mis_paquetes(request):
    cliente = get_cliente_actual(request)
    if not cliente:
        return redirect('login')
    envios = Envios.objects.filter(id_cliente=cliente)
    return render(request, 'logistica/mis_paquetes.html', {'paquetes': envios})


def programar_envio(request):
    cliente = get_cliente_actual(request)
    if not cliente:
        return redirect("login")

    if request.method == "POST":
        id_via = request.POST.get("id_via")
        id_tipo_servicio = request.POST.get("id_tipo_servicio")
        descripcion = request.POST.get("descripcion")


        largo = Decimal(request.POST.get("largo", "0"))
        ancho = Decimal(request.POST.get("ancho", "0"))
        alto = Decimal(request.POST.get("alto", "0"))
        peso = Decimal(request.POST.get("peso_real", "0"))


        valor_declarado_raw = request.POST.get("valor_declarado")
        valor_declarado = Decimal(valor_declarado_raw) if valor_declarado_raw else Decimal("0")

        via = ViasEnvio.objects.get(pk=id_via)
        servicio = TiposServicio.objects.get(pk=id_tipo_servicio)

        estado = EstadosEnvio.objects.filter(nombre__icontains="pendiente").first() or EstadosEnvio.objects.first()
        sucursal_miami = Sucursales.objects.filter(nombre__icontains="Miami").first()
        sucursal_destino = Sucursales.objects.exclude(nombre__icontains="Miami").first()

        if not sucursal_miami or not sucursal_destino:
            messages.error(request, "No existen sucursales configuradas.")
            return redirect("programar_envio")

        ruta = Rutas.objects.first()
        tarifa = Tarifas.objects.filter(id_via=via, id_tipo_servicio=servicio, activa=True).first()

        if not tarifa:
            messages.error(request, "No existe tarifa configurada.")
            return redirect("programar_envio")


        resultado_calculo = calcular_tarifa_envio(
            peso_real=peso,
            largo_cm=largo,
            ancho_cm=ancho,
            alto_cm=alto,
            id_via=int(via.pk)
        )


        costo_flete = resultado_calculo["costo"]


        costo_total = costo_flete

        ciudad_destino = cliente.id_ciudad if cliente.id_ciudad else sucursal_destino.id_ciudad


        envio = Envios.objects.create(
            numero_tracking=uuid.uuid4(),
            id_cliente=cliente,
            id_via=via,
            id_tipo_servicio=servicio,
            id_estado_actual=estado,
            id_ciudad_origen=sucursal_miami.id_ciudad,
            id_ciudad_destino=ciudad_destino,
            id_sucursal_origen=sucursal_miami,
            id_sucursal_destino=sucursal_destino,
            id_ruta=ruta,
            id_tarifa=tarifa,
            nombre_remitente="CLIENTE",
            nombre_destinatario=f"{cliente.primer_nombre or ''} {cliente.primer_apellido or ''}".strip(),
            telefono_destinatario=cliente.telefono or "00000000",
            direccion_destino=cliente.direccion or "Pendiente de completar",


            valor_declarado_hnl=valor_declarado,
            costo_flete_hnl=costo_flete,
            descuento_hnl=Decimal("0"),
            costo_total_hnl=costo_total,

            fecha_recepcion=timezone.now(),
            creado_por=Usuarios.objects.first()
        )

        Paquetes.objects.create(
            id_envio=envio,
            numero_paquete=1,
            descripcion_contenido=descripcion,
            largo_cm=largo,
            ancho_cm=ancho,
            alto_cm=alto,
            peso_real_kg=peso
        )

        generar_factura_automatica(envio)

        messages.success(request, f"Solicitud creada correctamente. Tracking: {envio.numero_tracking}")
        return redirect("portal_cliente")

    context = {
        "vias": ViasEnvio.objects.all(),
        "servicios": TiposServicio.objects.all(),
    }
    return render(request, "logistica/programar_envio.html", context)
def rastreo(request):
    numero_guia = request.GET.get('guia', '').strip()
    envio = None
    eventos = []
    error = None
    if numero_guia:
        try:
            envio = Envios.objects.get(numero_tracking=numero_guia)
            eventos = Seguimiento.objects.filter(id_envio=envio).order_by('-fecha_evento')
        except Envios.DoesNotExist:
            error = "No se encontró ningún paquete con ese número de guía."
        except ValueError:
            error = "El formato del número de guía no es válido."
    context = {
        'numero_guia': numero_guia,
        'envio': envio,
        'eventos': eventos,
        'error': error,
    }
    return render(request, 'logistica/rastreo.html', context)

def facturas(request):
    cliente = get_cliente_actual(request)
    if not cliente:
        return redirect('login')
    facturas_lista = Facturas.objects.filter(id_cliente=cliente).order_by('-fecha_emision')
    return render(request, 'logistica/facturas.html', {'facturas': facturas_lista})

def mis_datos(request):
    cliente = get_cliente_actual(request)
    if not cliente:
        return redirect('login')
    ciudades = Ciudades.objects.all()
    mensaje_exito = False
    if request.method == 'POST':
        if cliente:
            cliente.primer_nombre = request.POST.get('primer_nombre', '').strip()
            cliente.segundo_nombre = request.POST.get('segundo_nombre', '').strip()
            cliente.primer_apellido = request.POST.get('primer_apellido', '').strip()
            cliente.segundo_apellido = request.POST.get('segundo_apellido', '').strip()
            cliente.rtn = request.POST.get('rtn', '').strip()
            cliente.direccion = request.POST.get('direccion', '').strip()
            cliente.telefono = request.POST.get('telefono', '').strip()
            cliente.email = request.POST.get('email', '').strip()
            ciudad_id = request.POST.get('ciudad')
            if ciudad_id:
                cliente.id_ciudad = Ciudades.objects.get(id_ciudad=ciudad_id)
            cliente.save()
            mensaje_exito = True
    context = {
        'cliente': cliente,
        'ciudades': ciudades,
        'mensaje_exito': mensaje_exito,
    }
    return render(request, 'logistica/mis_datos.html', context)

def calculadora(request):
    vias = ViasEnvio.objects.all()
    servicios = TiposServicio.objects.all()
    resultado_hnl = None
    peso_volumetrico = None
    if request.method == 'POST':
        try:
            peso_kg = Decimal(request.POST.get('peso', 0))
            largo_cm = Decimal(request.POST.get('largo', 0))
            ancho_cm = Decimal(request.POST.get('ancho', 0))
            alto_cm = Decimal(request.POST.get('alto', 0))
            id_via = int(request.POST.get('via', 1))
            resultado = calcular_tarifa_envio(peso_kg, largo_cm, ancho_cm, alto_cm, id_via)
            resultado_hnl = resultado["costo"]
            peso_volumetrico = resultado["peso_volumetrico"]
        except ValueError:
            pass
    context = {
        'vias': vias,
        'servicios': servicios,
        'resultado_hnl': resultado_hnl,
        'peso_volumetrico': peso_volumetrico,
        'datos_post': request.POST if request.method == 'POST' else None
    }
    return render(request, 'logistica/calculadora.html', context)

def portal_empleado(request):
    empleado = Usuarios.objects.filter(id_rol__nombre__icontains='empleado').first() or Usuarios.objects.first()
    hoy = timezone.now().date()
    total_envios_hoy = Envios.objects.filter(fecha_recepcion__date=hoy).count()
    ingresos_hoy = sum(f.total_hnl for f in Facturas.objects.filter(fecha_emision__date=hoy, anulada=False))
    paquetes_transito = Envios.objects.exclude(id_estado_actual__es_estado_final=True).count()
    entregados_hoy = Seguimiento.objects.filter(fecha_evento__date=hoy, id_estado__es_estado_final=True).count()
    context = {
        'nombre_empleado': f"{empleado.primer_nombre} {empleado.primer_apellido}" if empleado else "Admin",
        'rol': empleado.id_rol.nombre if empleado and empleado.id_rol else "Administrador",
        'sucursal': empleado.id_sucursal.nombre if empleado and empleado.id_sucursal else "Bodega Central",
        'total_envios_hoy': total_envios_hoy,
        'ingresos_hoy': ingresos_hoy,
        'paquetes_transito': paquetes_transito,
        'entregados_hoy': entregados_hoy,
    }
    return render(request, 'logistica/portal_empleado.html', context)

def recepcion_paquetes(request):
    if request.method == 'POST':
        with transaction.atomic():
            id_cliente = request.POST.get('id_cliente')
            id_via = request.POST.get('id_via')
            id_tipo_servicio = request.POST.get('id_tipo_servicio')
            descripcion = request.POST.get('descripcion')
            valor_declarado = Decimal(request.POST.get('valor_declarado', '0'))
            largo = Decimal(request.POST.get('largo', '0'))
            ancho = Decimal(request.POST.get('ancho', '0'))
            alto = Decimal(request.POST.get('alto', '0'))
            peso_real = Decimal(request.POST.get('peso_real', '0'))
            if not id_cliente or not id_via or not id_tipo_servicio:
                messages.error(request, "Debe seleccionar cliente, vía y servicio.")
                return redirect("recepcion_paquetes")
            if peso_real <= 0 or largo <= 0 or ancho <= 0 or alto <= 0:
                messages.error(request, "El peso y las dimensiones deben ser mayores a cero.")
                return redirect("recepcion_paquetes")
            cliente = Clientes.objects.get(pk=id_cliente)
            via = ViasEnvio.objects.get(pk=id_via)
            servicio = TiposServicio.objects.get(pk=id_tipo_servicio)
            tarifa = Tarifas.objects.filter(id_via=via, id_tipo_servicio=servicio, activa=True).first()
            if not tarifa:
                messages.error(request, "No existe una tarifa configurada para este servicio.")
                return redirect("recepcion_paquetes")
            resultado = calcular_tarifa_envio(peso_real, largo, ancho, alto, via.id_via)
            costo_envio = resultado["costo"] * servicio.factor_precio
            peso_volumetrico = resultado["peso_volumetrico"]
            peso_cobrable = resultado["peso_cobrable"]
            estado_inicial = EstadosEnvio.objects.first()
            sucursal_origen = Sucursales.objects.filter(nombre__icontains="Miami").first()
            sucursal_destino = Sucursales.objects.exclude(nombre__icontains="Miami").first()
            if not sucursal_origen or not sucursal_destino:
                messages.error(request, "No existen sucursales configuradas.")
                return redirect("recepcion_paquetes")
            ruta = Rutas.objects.first()
            creado_por = Usuarios.objects.first()
            codigo_tracking = uuid.uuid4()
            nuevo_envio = Envios.objects.create(
                numero_tracking=codigo_tracking,
                id_cliente=cliente,
                id_via=via,
                id_tipo_servicio=servicio,
                id_estado_actual=estado_inicial,
                id_ciudad_origen=sucursal_origen.id_ciudad,
                id_ciudad_destino=sucursal_destino.id_ciudad,
                id_sucursal_origen=sucursal_origen,
                id_sucursal_destino=sucursal_destino,
                id_ruta=ruta,
                id_tarifa=tarifa,
                nombre_remitente="BODEGA MIAMI",
                nombre_destinatario=f"{cliente.primer_nombre} {cliente.primer_apellido}"[:100],
                telefono_destinatario=(cliente.telefono or "")[:20],
                direccion_destino=(cliente.direccion or "Conocido")[:200],
                valor_declarado_hnl=valor_declarado,
                costo_flete_hnl=costo_envio,
                costo_total_hnl=costo_envio,
                descuento_hnl=Decimal('0'),
                fecha_recepcion=timezone.now(),
                creado_por=creado_por
            )
            Paquetes.objects.create(
                id_envio=nuevo_envio,
                numero_paquete=1,
                descripcion_contenido=descripcion,
                largo_cm=largo,
                ancho_cm=ancho,
                alto_cm=alto,
                peso_real_kg=peso_real,
                peso_volumetrico_kg=peso_volumetrico,
                peso_cobrable_kg=peso_cobrable
            )
            generar_factura_automatica(nuevo_envio)
            messages.success(request, f"Paquete registrado correctamente. Tracking: {nuevo_envio.numero_tracking}")
            return redirect("recepcion_paquetes")
    context = {
        'clientes': Clientes.objects.all(),
        'vias': ViasEnvio.objects.all(),
        'servicios': TiposServicio.objects.all(),
    }
    return render(request, "logistica/recepcion.html", context)

def actualizar_rastreo(request):
    if request.method == 'POST':
        tracking_str = request.POST.get('tracking')
        id_estado = request.POST.get('id_estado')
        ubicacion = request.POST.get('ubicacion')
        try:
            envio = Envios.objects.get(numero_tracking=tracking_str)
            estado = EstadosEnvio.objects.get(pk=id_estado)
            creado_por = Usuarios.objects.first()
            envio.id_estado_actual = estado
            envio.save()
            Seguimiento.objects.create(
                id_envio=envio,
                id_estado=estado,
                ubicacion_descripcion=ubicacion,
                fecha_evento=timezone.now(),
                id_usuario=creado_por
            )
            messages.success(request, f'Estado del paquete actualizado a: {estado.nombre}')
        except Envios.DoesNotExist:
            messages.error(request, 'Error: No se encontró ningún paquete con ese número de tracking.')
        except ValidationError:
            messages.error(request, 'Error: El formato del número de tracking no es válido.')
        return redirect("actualizar_rastreo")
    return render(request, "logistica/tracking.html", {'estados': EstadosEnvio.objects.all().order_by('id_estado')})

def facturacion_sar(request):
    context = {}
    if request.method == 'GET' and 'q' in request.GET:
        query = request.GET.get('q')
        try:
            envio = Envios.objects.get(numero_tracking=query)
            if FacturaDetalle.objects.filter(id_envio=envio, id_factura__anulada=False).exists():
                messages.warning(request, 'Este envío ya ha sido facturado.')
            else:
                context['envio'] = envio
                flete = Decimal(500)
                seguro = envio.valor_declarado_hnl * Decimal('0.05') if envio.valor_declarado_hnl else Decimal(0)
                subtotal = flete + seguro
                isv = subtotal * Decimal('0.15')
                total = subtotal + isv
                context['subtotal'] = subtotal
                context['isv'] = isv
                context['total'] = total
        except Envios.DoesNotExist:
            pass
    elif request.method == 'POST':
        id_envio = request.POST.get('id_envio')
        subtotal = Decimal(request.POST.get('subtotal'))
        isv = Decimal(request.POST.get('isv'))
        total = Decimal(request.POST.get('total'))
        envio = Envios.objects.get(pk=id_envio)
        cajero = Usuarios.objects.first()
        config_sar = ConfiguracionesSar.objects.filter(activo=True).first()
        if not config_sar:
            messages.error(request, 'Error crítico: No hay una configuración SAR activa.')
            return redirect('facturacion_sar')
        numero_secuencia = config_sar.secuencia_actual
        config_sar.secuencia_actual += 1
        rango_final_int = int(config_sar.rango_final.split('-')[-1])
        if config_sar.secuencia_actual > rango_final_int:
            config_sar.activo = False
        config_sar.save()
        prefix = '-'.join(config_sar.rango_inicial.split('-')[:-1])
        factura_formateada = f"{prefix}-{numero_secuencia:08d}"
        nueva_factura = Facturas.objects.create(
            id_cliente=envio.id_cliente,
            id_sucursal=cajero.id_sucursal,
            id_usuario_emisor=cajero,
            numero_factura=factura_formateada,
            rtn_cliente=envio.id_cliente.rtn,
            nombre_cliente=f'{envio.id_cliente.primer_nombre} {envio.id_cliente.primer_apellido}',
            fecha_emision=timezone.now(),
            subtotal_hnl=subtotal,
            descuento_hnl=0,
            base_gravable_hnl=subtotal,
            isv_hnl=isv,
            total_hnl=total,
            anulada=False
        )
        FacturaDetalle.objects.create(
            id_factura=nueva_factura,
            id_envio=envio,
            descripcion=f'Envío de Paquetería - Tracking: {envio.numero_tracking}',
            cantidad=1,
            precio_unitario_hnl=subtotal,
            descuento_linea_hnl=0,
            subtotal_linea_hnl=subtotal
        )
        messages.success(request, f'Factura {nueva_factura.numero_factura} generada exitosamente.')
        return redirect('facturacion_sar')
    return render(request, "logistica/caja.html", context)