from decimal import Decimal
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from django.db import transaction
import uuid


from rest_framework import viewsets, generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.contrib.auth.hashers import check_password, make_password
from rest_framework_simplejwt.tokens import RefreshToken
import traceback

from .models import (
    Clientes, Envios, Facturas, Ciudades, Seguimiento, TiposServicio,
    ViasEnvio, Tarifas, EstadosEnvio, Paquetes, Sucursales, Rutas,
    TiposCliente,  
)
from .serializers import (
    ClientePerfilSerializer, EnvioListSerializer, EnvioDetailSerializer,
    FacturaListSerializer, FacturaDetailSerializer, RastreoPublicoSerializer,
    CiudadSerializer, TipoServicioSerializer, ViaEnvioSerializer,
    AnunciarPaqueteSerializer,
)

DIVISOR_VOLUMETRICO_AEREO = Decimal('5000')


class LoginClienteView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        try:
            cliente = Clientes.objects.get(email=email, activo=True)
        except Clientes.DoesNotExist:
            return Response({'detail': 'Credenciales inválidas'}, status=status.HTTP_401_UNAUTHORIZED)

        if not cliente.password_hash or not check_password(password, cliente.password_hash):
            return Response({'detail': 'Credenciales inválidas'}, status=status.HTTP_401_UNAUTHORIZED)

        refresh = RefreshToken.for_user(cliente)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'cliente': ClientePerfilSerializer(cliente).data,
        })


class RegistroClienteView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        primer_nombre = request.data.get('primer_nombre')
        primer_apellido = request.data.get('primer_apellido')
        id_tipo_cliente = request.data.get('id_tipo_cliente')

        faltantes = [
            campo for campo, valor in [
                ('email', email), ('password', password),
                ('primer_nombre', primer_nombre),
                ('primer_apellido', primer_apellido),
                ('id_tipo_cliente', id_tipo_cliente),
            ] if not valor
        ]
        if faltantes:
            return Response(
                {'detail': f'Faltan campos obligatorios: {", ".join(faltantes)}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(password) < 8:
            return Response(
                {'detail': 'La contraseña debe tener al menos 8 caracteres.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if Clientes.objects.filter(email=email).exists():
            return Response(
                {'detail': 'Ya existe una cuenta registrada con ese correo.'},
                status=status.HTTP_409_CONFLICT,
            )

        segundo_nombre = request.data.get('segundo_nombre') or None
        segundo_apellido = request.data.get('segundo_apellido') or None
        rtn = request.data.get('rtn') or None
        telefono = request.data.get('telefono') or None
        direccion = request.data.get('direccion') or None
        id_ciudad = request.data.get('id_ciudad') or None 

        razon_social = request.data.get('razon_social') or None
        if not razon_social:
            razon_social = f"{primer_nombre} {primer_apellido}".strip()


        if rtn and Clientes.objects.filter(rtn=rtn).exists():
            return Response(
                {'detail': 'El RTN ingresado ya está registrado en otra cuenta.'},
                status=status.HTTP_409_CONFLICT,
            )

        try:
            cliente = Clientes.objects.create(
                id_tipo_cliente_id=id_tipo_cliente,
                razon_social=razon_social,
                primer_nombre=primer_nombre,
                segundo_nombre=segundo_nombre,
                primer_apellido=primer_apellido,
                segundo_apellido=segundo_apellido,
                rtn=rtn,
                email=email,
                password_hash=make_password(password),
                telefono=telefono,
                direccion=direccion,
                id_ciudad_id=id_ciudad,
                descuento_porcentaje=Decimal('0.00'),
                activo=True,
            )
        except Exception as e:
            traceback.print_exc()
            return Response(
                {'detail': f'DEBUG: {type(e).__name__}: {e}'},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        refresh = RefreshToken.for_user(cliente)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'cliente': ClientePerfilSerializer(cliente).data,
        }, status=status.HTTP_201_CREATED)


class MiPerfilView(generics.RetrieveAPIView):
    serializer_class = ClientePerfilSerializer

    def get_object(self):
        return self.request.user


class MisEnviosViewSet(viewsets.ReadOnlyModelViewSet):
    def get_queryset(self):
        return Envios.objects.filter(id_cliente=self.request.user).order_by('-fecha_recepcion')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return EnvioDetailSerializer
        return EnvioListSerializer


class MisFacturasViewSet(viewsets.ReadOnlyModelViewSet):
    def get_queryset(self):
        return Facturas.objects.filter(id_cliente=self.request.user).order_by('-fecha_emision')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return FacturaDetailSerializer
        return FacturaListSerializer


class RastreoPublicoView(generics.RetrieveAPIView):
    queryset = Envios.objects.all()
    serializer_class = RastreoPublicoSerializer
    permission_classes = [AllowAny]
    lookup_field = 'numero_tracking'
    lookup_url_kwarg = 'numero_tracking'


@api_view(['GET'])
@permission_classes([AllowAny])
def catalogos_view(request):

    tarifas_activas = Tarifas.objects.filter(activa=True).values(
        'id_ciudad_origen', 'id_ciudad_destino', 'id_tipo_servicio', 'id_via',
        'peso_min_kg', 'peso_max_kg',
    )
    return Response({
        'ciudades': CiudadSerializer(
            Ciudades.objects.select_related('id_pais').all(), many=True
        ).data,
        'tipos_servicio': TipoServicioSerializer(TiposServicio.objects.all(), many=True).data,
        'vias_envio': ViaEnvioSerializer(ViasEnvio.objects.all(), many=True).data,
        'tarifas_disponibles': list(tarifas_activas),

        'tipos_cliente': list(
            TiposCliente.objects.values('id_tipo_cliente', 'nombre', 'descripcion')
        ),
    })


class AnunciarPaqueteView(APIView):
    def post(self, request):
        serializer = AnunciarPaqueteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        peso = d['peso_real_kg']
        largo = d['largo_cm']
        ancho = d['ancho_cm']
        alto = d['alto_cm']

        fecha_estimada = request.data.get('fecha_estimada') or None
        observaciones  = request.data.get('observaciones') or None


        via_pk = d['id_via'].pk if hasattr(d['id_via'], 'pk') else int(d['id_via'])
        via_obj = ViasEnvio.objects.get(pk=via_pk)
        es_aerea = 'aérea' in via_obj.nombre.lower() or 'aerea' in via_obj.nombre.lower()

        volumen_cm3 = largo * ancho * alto
        volumen_m3  = volumen_cm3 / Decimal('1000000')

        if es_aerea:
            peso_volumetrico = (volumen_cm3 / DIVISOR_VOLUMETRICO_AEREO).quantize(Decimal('0.001'))
            peso_cobrable    = max(peso, peso_volumetrico)
        else:
            peso_volumetrico = None
            peso_cobrable    = peso


        tarifa = Tarifas.objects.filter(
            id_via=d['id_via'],
            id_tipo_servicio=d['id_tipo_servicio'],
            id_ciudad_origen=d['id_ciudad_origen'],
            id_ciudad_destino=d['id_ciudad_destino'],
            peso_min_kg__lte=peso_cobrable,
            peso_max_kg__gte=peso_cobrable,
            activa=True,
        ).first()

        if not tarifa:
            return Response(
                {'detail': 'No hay una tarifa activa para esa combinación de ruta, servicio y peso. Contactá a soporte.'},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        if es_aerea:
            costo = tarifa.precio_base_hnl + (peso_cobrable * tarifa.precio_por_kg_hnl)
        else:
            costo = (
                tarifa.precio_base_hnl
                + (peso_cobrable * tarifa.precio_por_kg_hnl)
                + (volumen_m3 * tarifa.precio_por_m3_hnl)
            )

        sucursal_origen  = Sucursales.objects.filter(id_ciudad=d['id_ciudad_origen'], activa=True).first()
        sucursal_destino = Sucursales.objects.filter(id_ciudad=d['id_ciudad_destino'], activa=True).first()
        if not sucursal_origen or not sucursal_destino:
            return Response(
                {'detail': 'No hay sucursal activa configurada para esa ruta. Contactá a soporte.'},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        ruta = Rutas.objects.filter(id_sucursal=sucursal_destino.id_sucursal, activa=True).first()
        if not ruta:
            return Response(
                {'detail': 'No hay ruta activa configurada hacia esa sucursal. Contactá a soporte.'},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        estado_inicial = EstadosEnvio.objects.filter(nombre='Recibido').first()
        cliente = request.user

        with transaction.atomic():
            envio = Envios.objects.create(
                numero_tracking=uuid.uuid4(),
                id_cliente=cliente,
                id_via_id=d['id_via'],
                id_tipo_servicio_id=d['id_tipo_servicio'],
                id_estado_actual=estado_inicial,
                id_ciudad_origen_id=d['id_ciudad_origen'],
                id_ciudad_destino_id=d['id_ciudad_destino'],
                id_sucursal_origen=sucursal_origen,
                id_sucursal_destino=sucursal_destino,
                id_ruta=ruta,
                id_tarifa=tarifa,
                nombre_remitente=f"{cliente.primer_nombre or ''} {cliente.primer_apellido or ''}".strip() or cliente.razon_social,
                nombre_destinatario=d['nombre_destinatario'],
                telefono_destinatario=d.get('telefono_destinatario', ''),
                direccion_destino=d['direccion_destino'],
                valor_declarado_hnl=d['valor_declarado_hnl'],
                costo_flete_hnl=costo,
                descuento_hnl=Decimal('0'),
                costo_total_hnl=costo,
                fecha_recepcion=timezone.now(),
                fecha_estimada=fecha_estimada, 
                observaciones=observaciones,    
            )
            Paquetes.objects.create(
                id_envio=envio,
                numero_paquete=1,
                descripcion_contenido=d.get('descripcion_contenido', ''),
                largo_cm=largo,
                ancho_cm=ancho,
                alto_cm=alto,
                peso_real_kg=peso,
                peso_volumetrico_kg=peso_volumetrico,
                peso_cobrable_kg=peso_cobrable,
            )
            Seguimiento.objects.create(
                id_envio=envio,
                id_estado=estado_inicial,
                ubicacion_descripcion=sucursal_origen.nombre,
                fecha_evento=timezone.now(),
            )

        return Response(EnvioDetailSerializer(envio).data, status=status.HTTP_201_CREATED)