import uuid
from decimal import Decimal
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from .services import calcular_tarifa_envio, generar_factura_automatica
from .models import ViasEnvio, TiposServicio, EstadosEnvio, Rutas, Ciudades, TiposCliente
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

# dinde mandar al usuario cuado entra ala pagina principal
def home_redirect(request):
    if request.session.get('id_cliente'):    #buscamos si el cliente existe
        return redirect('portal_cliente')    #si existe lo envia ala pagina del portal del cliente
    return redirect('login')                 # si no lo envia al login

#funcion para inicio de sesion
def login_view(request):
    error = None

    # comprobar si el usuario toco el boton de iniciar sesion

    if request.method == 'POST':
        identificador = request.POST.get('email', '').strip() # obtiene lo que el usuario escribio en el correo y elimina espacios
        password = request.POST.get('password', '')            # aqui vamos a obtener el password que ingreso el cliente

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
            return redirect('/admin-portal/')

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

    from .models import ViasEnvio
    vias = ViasEnvio.objects.all()

    context = {
        'nombre_completo': nombre_completo,
        'direccion_local': direccion_local,
        'telefono_local': telefono_local,
        'email_local': email_local,
        'ciudad_local': ciudad_local,
        'tipo_cliente': tipo_cliente,
        'descuento': descuento,
        'sucursal_miami': sucursal_miami,
        'vias': vias,
    }
    return render(request, 'logistica/portal_cliente.html', context)

def mis_paquetes(request):
    cliente = get_cliente_actual(request)
    if not cliente:
        return redirect('login')
    from .models import Envios, FacturaDetalle, PagosFactura

    envios = Envios.objects.filter(id_cliente=cliente)
    
    for e in envios:
        e.pagado_o_en_proceso = False
        e.mensaje_pago = ""
        detalle = FacturaDetalle.objects.filter(id_envio=e).first()
        if detalle:
            pago = PagosFactura.objects.filter(id_factura=detalle.id_factura).exclude(estado_verificacion="Rechazado").first()
            if pago:
                e.pagado_o_en_proceso = True
                if pago.estado_verificacion == "Pendiente":
                    e.mensaje_pago = "Pago en Revisión"
                else:
                    e.mensaje_pago = "Pago Completado"
                    
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
            cliente.rtn = request.POST.get('rtn', '').strip() or None
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
            
            from .models import Tarifas
            tarifa_db = Tarifas.objects.filter(id_via=id_via, activa=True).first()
            
            if id_via == 1: # Aéreo
                peso_volumetrico = volumen_cm3 / 5000.0
                peso_cobrable = max(peso_kg, peso_volumetrico)
                
                if tarifa_db:
                    resultado_hnl = float(tarifa_db.precio_base_hnl) + (peso_cobrable * float(tarifa_db.precio_por_kg_hnl))
                else:
                    resultado_hnl = peso_cobrable * 125.0
                
            else: # Marítimo
                volumen_m3 = volumen_cm3 / 1000000.0
                peso_volumetrico = volumen_m3 

                if tarifa_db:
                    resultado_hnl = float(tarifa_db.precio_base_hnl) + (volumen_m3 * float(tarifa_db.precio_por_m3_hnl))
                else:
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
                ubicacion_descripcion=ubicacion,
                fecha_evento=timezone.now(),
                id_usuario=creado_por
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
        
        # Guardar el pago en efectivo (Físico)
        from .models import PagosFactura, MetodosPago, MetodosEntrega, EstadosEnvio, Seguimiento
        metodo_pago_efectivo = MetodosPago.objects.filter(nombre__icontains="Efectivo").first() or MetodosPago.objects.first()
        metodo_entrega_local = MetodosEntrega.objects.first()
        
        PagosFactura.objects.create(
            id_factura=nueva_factura,
            id_metodo_pago=metodo_pago_efectivo,
            id_metodo_entrega=metodo_entrega_local,
            monto_pagado=total,
            estado_verificacion="Aprobado",
            verificado_por=cajero
        )
        
        # Pasar a tránsito
        estado_transito = EstadosEnvio.objects.get(pk=3)
        envio.id_estado_actual = estado_transito
        envio.save()
        
        Seguimiento.objects.create(
            id_envio=envio,
            id_estado=estado_transito,
            id_usuario=cajero,
            ubicacion_descripcion="Bodega Central (Despachado)"
        )
        
        messages.success(request, f'Factura {nueva_factura.numero_factura} generada exitosamente. Envío en Tránsito.')
        return redirect('facturacion_sar')
        
    return render(request, "logistica/caja.html", context)

def registro_cliente(request):
    from .models import Ciudades, TiposCliente
    # Solo mostrar ciudades locales excluyendo la id_ciudad=1 que es Miami
    ciudades = Ciudades.objects.exclude(id_ciudad=1).exclude(nombre__icontains="Madrid").exclude(nombre__icontains="Texas")
    if request.method == "POST":
        primer_nombre = request.POST.get("primer_nombre", "").strip()
        segundo_nombre = request.POST.get("segundo_nombre", "").strip()
        primer_apellido = request.POST.get("primer_apellido", "").strip()
        segundo_apellido = request.POST.get("segundo_apellido", "").strip()
        razon_social = request.POST.get("razon_social", "").strip()
        
        email = request.POST.get("email", "").strip()
        telefono = request.POST.get("telefono", "").strip()
        direccion = request.POST.get("direccion", "").strip()
        password = request.POST.get("password")
        id_ciudad = request.POST.get("ciudad")
        
        if Clientes.objects.filter(email=email).exists():
            messages.error(request, "Este correo electrónico ya está registrado.")
            return render(request, "logistica/registro_cliente.html", {"ciudades": ciudades})

        tipo_cliente = TiposCliente.objects.first()
        
        ciudad = None
        if id_ciudad:
            try:
                ciudad = Ciudades.objects.get(pk=id_ciudad)
            except Ciudades.DoesNotExist:
                ciudad = Ciudades.objects.first()
        else:
            ciudad = Ciudades.objects.first()
            
        cliente = Clientes.objects.create(
            id_tipo_cliente=tipo_cliente,
            id_ciudad=ciudad,
            razon_social=razon_social,
            primer_nombre=primer_nombre,
            segundo_nombre=segundo_nombre,
            primer_apellido=primer_apellido,
            segundo_apellido=segundo_apellido,
            telefono=telefono,
            direccion=direccion,
            email=email,
            password_hash=make_password(password),
            activo=True,
            descuento_porcentaje=Decimal("0")
        )
        messages.success(request, "Cuenta creada correctamente. ¡Bienvenido!")
        return redirect("login")
    return render(request, "logistica/registro_cliente.html", {"ciudades": ciudades})

def programar_envio(request):
    cliente = get_cliente_actual(request)
    if not cliente:
        return redirect("login")
    if request.method == "POST":
        id_via = request.POST.get("id_via")
        id_tipo_servicio = request.POST.get("id_tipo_servicio")
        descripcion = request.POST.get("descripcion")
        largo = Decimal(request.POST.get("largo"))
        ancho = Decimal(request.POST.get("ancho"))
        alto = Decimal(request.POST.get("alto"))
        peso = Decimal(request.POST.get("peso_real"))
        valor_declarado = Decimal(request.POST.get("valor_declarado", "0"))
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
            # Hugo's dynamic calculator is used later, so just grab any valid tarifa to satisfy the DB constraint
            tarifa = Tarifas.objects.first()
            if not tarifa:
                messages.error(request, "Contacte a soporte, la tabla de tarifas base está vacía.")
                return redirect("programar_envio")
        costo = tarifa.precio_base_hnl
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
            costo_flete_hnl=None,
            descuento_hnl=Decimal("0"),
            costo_total_hnl=None,
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
        # generar_factura_automatica(envio) # Desactivado para pago manual
        messages.success(request, f"Solicitud creada correctamente. Tracking: {envio.numero_tracking}")
        return redirect("portal_cliente")
    context = {
        "vias": ViasEnvio.objects.all(),
        "servicios": TiposServicio.objects.all(),
    }
    return render(request, "logistica/programar_envio.html", context)

from .models import MetodosEntrega, MetodosPago, PagosFactura
from django.core.files.storage import FileSystemStorage

def checkout_envio(request, tracking):
    cliente = get_cliente_actual(request)
    if not cliente:
        return redirect("login")

    envio = Envios.objects.filter(numero_tracking=tracking, id_cliente=cliente).first()
    if not envio:
        messages.error(request, "Envío no encontrado.")
        return redirect("mis_paquetes")

    # Verificar si ya tiene factura/pago
    from .models import FacturaDetalle
    detalle = FacturaDetalle.objects.filter(id_envio=envio).first()
    if detalle:
        pago_existente = PagosFactura.objects.filter(id_factura=detalle.id_factura).exclude(estado_verificacion="Rechazado").first()
        if pago_existente:
            if pago_existente.estado_verificacion == "Pendiente":
                messages.warning(request, "Tu pago ya está en revisión.")
            else:
                messages.warning(request, "Este envío ya fue pagado.")
            return redirect("mis_paquetes")

    if envio.id_estado_actual.id_estado != 1 or not envio.costo_total_hnl:
        messages.error(request, "Este envío no está habilitado para pago o aún no ha sido pesado.")
        return redirect("mis_paquetes")

    metodos_entrega = MetodosEntrega.objects.filter(activo=True)
    metodos_pago = MetodosPago.objects.filter(activo=True)

    if request.method == "POST":
        id_metodo_entrega = request.POST.get("metodo_entrega")
        id_metodo_pago = request.POST.get("metodo_pago")
        direccion_alternativa = request.POST.get("direccion_alternativa")

        metodo_entrega = MetodosEntrega.objects.get(pk=id_metodo_entrega)
        metodo_pago = MetodosPago.objects.get(pk=id_metodo_pago)
        
        sucursal_retiro = request.POST.get("sucursal_retiro")
        
        if direccion_alternativa and direccion_alternativa.strip():
            envio.direccion_destino = direccion_alternativa.strip()
        elif sucursal_retiro:
            try:
                from .models import Sucursales
                sucursal = Sucursales.objects.get(pk=sucursal_retiro)
                envio.id_sucursal_destino = sucursal
            except:
                pass
                
        envio.save()

        comprobante_url = None
        if metodo_pago.requiere_comprobante and "comprobante" in request.FILES:
            imagen = request.FILES["comprobante"]
            fs = FileSystemStorage()
            filename = fs.save(imagen.name, imagen)
            comprobante_url = fs.url(filename)

        # Reusar Factura si ya existe, o Generar una nueva
        detalle_existente = FacturaDetalle.objects.filter(id_envio=envio).first()
        if detalle_existente:
            factura = detalle_existente.id_factura
        else:
            factura = generar_factura_automatica(envio)
            if not factura:
                messages.error(request, "Error generando la factura. Contacte soporte.")
                return redirect("checkout_envio", tracking=tracking)

        # Generar Pago
        estado_verif = "Pendiente" if metodo_pago.requiere_comprobante else "Aprobado"
        PagosFactura.objects.create(
            id_factura=factura,
            id_metodo_pago=metodo_pago,
            id_metodo_entrega=metodo_entrega,
            monto_pagado=factura.total_hnl,
            comprobante_url=comprobante_url,
            estado_verificacion=estado_verif
        )

        messages.success(request, "Pago registrado con éxito. ¡Gracias por preferirnos!")
        return redirect("mis_paquetes")

    from .models import Sucursales
    sucursales_locales = Sucursales.objects.exclude(nombre__icontains="Miami").exclude(nombre__icontains="Hub")

    context = {
        "envio": envio,
        "metodos_entrega": metodos_entrega,
        "metodos_pago": metodos_pago,
        "sucursales_locales": sucursales_locales
    }
    return render(request, "logistica/checkout_envio.html", context)

def verificar_pagos(request):
    if not request.user.is_authenticated or not request.user.is_staff:
        return redirect("login")

    if request.method == "POST":
        id_pago = request.POST.get("id_pago")
        accion = request.POST.get("accion") # aprobar o rechazar
        pago = PagosFactura.objects.get(pk=id_pago)
        empleado = Usuarios.objects.first() # mock empleado

        if accion == "aprobar":
            pago.estado_verificacion = "Aprobado"
            pago.verificado_por = empleado
            
            # Pasar a tránsito
            from .models import EstadosEnvio, Seguimiento, FacturaDetalle
            detalle = FacturaDetalle.objects.filter(id_factura=pago.id_factura).first()
            if detalle:
                envio = detalle.id_envio
                estado_transito = EstadosEnvio.objects.get(pk=3)
                envio.id_estado_actual = estado_transito
                envio.save()
                
                Seguimiento.objects.create(
                    id_envio=envio,
                    id_estado=estado_transito,
                    id_usuario=empleado,
                    ubicacion_descripcion="Verificación Web - Despachado a Tránsito",
                    fecha_evento=timezone.now()
                )
                
        elif accion == "rechazar":
            pago.estado_verificacion = "Rechazado"
            pago.verificado_por = empleado

        pago.save()
        messages.success(request, f"Pago {accion}do correctamente.")
        return redirect("verificar_pagos")

    pagos = PagosFactura.objects.filter(estado_verificacion="Pendiente").order_by("-fecha_pago")
    return render(request, "logistica/verificar_pagos.html", {"pagos": pagos})

def auditar_paquetes(request):
    if not request.user.is_authenticated or not request.user.is_staff:
        return redirect("login")

    if request.method == "POST":
        id_envio = request.POST.get("id_envio")
        peso_real = request.POST.get("peso_real")
        largo = request.POST.get("largo")
        ancho = request.POST.get("ancho")
        alto = request.POST.get("alto")

        envio = Envios.objects.get(pk=id_envio)
        paquete = Paquetes.objects.filter(id_envio=envio).first()

        if paquete:
            # Actualizar dimensiones y pesos
            paquete.largo_cm = Decimal(largo)
            paquete.ancho_cm = Decimal(ancho)
            paquete.alto_cm = Decimal(alto)
            paquete.peso_real_kg = Decimal(peso_real)

            volumen = (paquete.largo_cm * paquete.ancho_cm * paquete.alto_cm) / Decimal(1000000)
            paquete.peso_volumetrico_kg = (paquete.largo_cm * paquete.ancho_cm * paquete.alto_cm) / Decimal(5000)
            paquete.peso_cobrable_kg = max(paquete.peso_real_kg, paquete.peso_volumetrico_kg)
            paquete.save()

            from .services import calcular_tarifa_envio
            resultado = calcular_tarifa_envio(
                peso_real=paquete.peso_real_kg,
                largo_cm=paquete.largo_cm,
                ancho_cm=paquete.ancho_cm,
                alto_cm=paquete.alto_cm,
                envio=envio
            )
            # Aplicar factor si tiene servicio express
            costo_base = resultado["costo"]
            if hasattr(envio.id_tipo_servicio, "factor_precio"):
                costo_base = costo_base * envio.id_tipo_servicio.factor_precio
                
            # Calcular impuestos y descuentos igual que la factura SAR
            cliente = envio.id_cliente
            descuento_porcentaje = cliente.descuento_porcentaje or Decimal('0')
            descuento = costo_base * descuento_porcentaje / Decimal('100')
            base_gravable = costo_base - descuento
            isv = base_gravable * Decimal('0.15')
            
            envio.costo_flete_hnl = costo_base
            envio.descuento_hnl = descuento
            envio.costo_total_hnl = base_gravable + isv

            # Cambiar estado del envío a Recibido en Bodega (Auditoría Completada)
            estado_auditado = EstadosEnvio.objects.get(pk=1) # Mantenemos en 1 para que el cliente pague
            envio.id_estado_actual = estado_auditado
            envio.save()

            # Registrar evento de seguimiento
            Seguimiento.objects.create(
                id_envio=envio,
                id_estado=estado_auditado,
                ubicacion_descripcion="Bodega Central",
                fecha_evento=timezone.now(),
                id_usuario=Usuarios.objects.first()
            )

            messages.success(request, f"Paquete {envio.numero_tracking} auditado correctamente. El cliente ya puede pagar.")
        return redirect("auditar_paquetes")

    # Mostrar envíos en estado 1 (Recibidos por el sistema, sin auditar físicamente)
    envios_pendientes = Envios.objects.filter(id_estado_actual__id_estado=1).order_by("-fecha_recepcion")
    return render(request, "logistica/auditar_paquetes.html", {"envios": envios_pendientes})
