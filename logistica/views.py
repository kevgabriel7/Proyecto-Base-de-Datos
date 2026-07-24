from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as django_login, logout as django_logout
from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password
from .models import Clientes, Sucursales


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