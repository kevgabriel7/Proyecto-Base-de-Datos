from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as django_login, logout as django_logout
from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password
from .models import Clientes, Sucursales, Envios, Facturas, Seguimiento, Usuarios, Paquetes, Tarifas


def get_cliente_actual(request):
    """Devuelve el Cliente logueado en esta sesión, o None si no hay nadie logueado."""
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

        # 1) Intentar como staff (auth.User de Django -> panel admin)
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

        # 2) Intentar como cliente
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

def mis_paquetes(request):
    cliente = get_cliente_actual(request)
    if not cliente:
        return redirect('login')
    from .models import Envios

    envios = Envios.objects.filter(id_cliente=cliente)
    
    context = {
        'paquetes': envios,
    }
    return render(request, 'logistica/mis_paquetes.html', context)

def rastreo(request):
    from .models import Envios, Seguimiento
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
    from .models import Facturas

    # Jalamos las facturas reales del cliente
    facturas_lista = Facturas.objects.filter(id_cliente=cliente).order_by('-fecha_emision')
    
    context = {
        'facturas': facturas_lista,
    }
    return render(request, 'logistica/facturas.html', context)

def mis_datos(request):
    cliente = get_cliente_actual(request)
    if not cliente:
        return redirect('login')
    from .models import Ciudades
    
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
    from .models import ViasEnvio, TiposServicio
    vias = ViasEnvio.objects.all()
    servicios = TiposServicio.objects.all()
    
    resultado_hnl = None
    peso_volumetrico = None
    
    if request.method == 'POST':
        try:
            peso_kg = float(request.POST.get('peso', 0))
            largo_cm = float(request.POST.get('largo', 0))
            ancho_cm = float(request.POST.get('ancho', 0))
            alto_cm = float(request.POST.get('alto', 0))
            id_via = int(request.POST.get('via', 1))
            

            # Volumen en cm3
            volumen_cm3 = largo_cm * ancho_cm * alto_cm
            
            if id_via == 1: # Aéreo

                peso_volumetrico = volumen_cm3 / 5000.0
                peso_cobrable = max(peso_kg, peso_volumetrico)

                resultado_hnl = peso_cobrable * 125.0
                
            else: # Marítimo

                volumen_m3 = volumen_cm3 / 1000000.0
                peso_volumetrico = volumen_m3 

                resultado_hnl = volumen_m3 * 5000.0
                if resultado_hnl < 500: 
                    resultado_hnl = 500.0
                    
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
    from django.utils import timezone
    
    # Harcoded employee for simplicity as requested by user
    empleado = Usuarios.objects.filter(id_rol__nombre__icontains='empleado').first()
    if not empleado:
        empleado = Usuarios.objects.first()
        
    hoy = timezone.now().date()
    
    # Stats
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

from django.contrib import messages
from django.shortcuts import redirect
import uuid
from decimal import Decimal

def recepcion_paquetes(request):
    from .models import Clientes, ViasEnvio, TiposServicio, EstadosEnvio, Sucursales, Ciudades, Envios, Paquetes, Rutas, Tarifas, Usuarios
    
    if request.method == 'POST':
        # Recoger datos
        id_cliente = request.POST.get('id_cliente')
        id_via = request.POST.get('id_via')
        id_tipo_servicio = request.POST.get('id_tipo_servicio')
        descripcion = request.POST.get('descripcion')
        valor_declarado = request.POST.get('valor_declarado')
        largo = Decimal(request.POST.get('largo'))
        ancho = Decimal(request.POST.get('ancho'))
        alto = Decimal(request.POST.get('alto'))
        peso_real = Decimal(request.POST.get('peso_real'))
        
        cliente = Clientes.objects.get(pk=id_cliente)
        via = ViasEnvio.objects.get(pk=id_via)
        servicio = TiposServicio.objects.get(pk=id_tipo_servicio)
        
        # Valores por defecto para la simulacion
        estado_inicial = EstadosEnvio.objects.first() # Asumiendo el primero es Recibido
        sucursal_origen = Sucursales.objects.filter(nombre__icontains='Miami').first()
        sucursal_destino = Sucursales.objects.exclude(nombre__icontains='Miami').first()
        ciudad_origen = sucursal_origen.id_ciudad
        ciudad_destino = sucursal_destino.id_ciudad
        ruta = Rutas.objects.first()
        tarifa = Tarifas.objects.first()
        creado_por = Usuarios.objects.first()
        
        # Crear Envio
        from django.utils import timezone
        nuevo_envio = Envios.objects.create(
            numero_tracking=uuid.uuid4(),
            id_cliente=cliente,
            id_via=via,
            id_tipo_servicio=servicio,
            id_estado_actual=estado_inicial,
            id_ciudad_origen=ciudad_origen,
            id_ciudad_destino=ciudad_destino,
            id_sucursal_origen=sucursal_origen,
            id_sucursal_destino=sucursal_destino,
            id_ruta=ruta,
            id_tarifa=tarifa,
            nombre_remitente='BODEGA MIAMI',
            nombre_destinatario=f'{cliente.primer_nombre} {cliente.primer_apellido}',
            telefono_destinatario=cliente.telefono,
            direccion_destino=cliente.direccion or 'Conocido',
            valor_declarado_hnl=valor_declarado,
            descuento_hnl=0,
            fecha_recepcion=timezone.now(),
            creado_por=creado_por
        )
        
        # Calcular pesos
        volumen = (largo * ancho * alto) / Decimal(1000000)
        peso_volumetrico = (largo * ancho * alto) / Decimal(5000) # factor estandar aereo
        peso_cobrable = max(peso_real, peso_volumetrico)
        
        # Crear Paquete
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
        
        messages.success(request, f'Paquete registrado con éxito. Tracking: {nuevo_envio.numero_tracking}')
        return redirect("recepcion_paquetes")
        
    context = {
        'clientes': Clientes.objects.all(),
        'vias': ViasEnvio.objects.all(),
        'servicios': TiposServicio.objects.all(),
    }
    return render(request, "logistica/recepcion.html", context)

def actualizar_rastreo(request):
    from .models import EstadosEnvio, Envios, Seguimiento, Usuarios
    from django.utils import timezone
    from django.core.exceptions import ValidationError
    
    if request.method == 'POST':
        tracking_str = request.POST.get('tracking')
        id_estado = request.POST.get('id_estado')
        ubicacion = request.POST.get('ubicacion')
        
        try:
            envio = Envios.objects.get(numero_tracking=tracking_str)
            estado = EstadosEnvio.objects.get(pk=id_estado)
            creado_por = Usuarios.objects.first()
            
            # Actualizar el estado del envio principal
            envio.id_estado_actual = estado
            envio.save()
            
            # Crear el evento de seguimiento
            Seguimiento.objects.create(
                id_envio=envio,
                id_estado=estado,
                ubicacion=ubicacion,
                fecha_evento=timezone.now(),
                creado_por=creado_por
            )
            
            messages.success(request, f'Estado del paquete actualizado a: {estado.nombre}')
            
        except Envios.DoesNotExist:
            messages.error(request, 'Error: No se encontró ningún paquete con ese número de tracking.')
        except ValidationError:
            messages.error(request, 'Error: El formato del número de tracking (UUID) no es válido.')
            
        return redirect("actualizar_rastreo")

    context = {
        'estados': EstadosEnvio.objects.all().order_by('id_estado')
    }
    return render(request, "logistica/tracking.html", context)

def facturacion_sar(request):
    from .models import Envios, ConfiguracionesSar, Facturas, FacturaDetalle, Usuarios
    from django.utils import timezone
    from decimal import Decimal
    from django.contrib import messages
    from django.shortcuts import render, redirect
    
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
        
        config_sar = ConfiguracionesSar.objects.filter(activa=True).first()
        if not config_sar:
            messages.error(request, 'Error crítico: No hay una configuración SAR activa.')
            return redirect('facturacion_sar')
            
        numero_factura = config_sar.rango_actual
        config_sar.rango_actual += 1
        if config_sar.rango_actual > config_sar.rango_final:
            config_sar.activa = False
        config_sar.save()
        
        nueva_factura = Facturas.objects.create(
            id_cliente=envio.id_cliente,
            id_sucursal=cajero.id_sucursal,
            id_usuario_emisor=cajero,
            numero_factura=f"000-001-01-{numero_factura:08d}",
            rtn_cliente=envio.id_cliente.rtn_identidad,
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
