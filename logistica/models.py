from django.db import models
from django.db.models import F

class AsignacionesRuta(models.Model):
    id_asignacion = models.AutoField(primary_key=True)
    id_ruta = models.ForeignKey('Rutas', models.DO_NOTHING, db_column='id_ruta')
    id_repartidor = models.ForeignKey('Repartidores', models.DO_NOTHING, db_column='id_repartidor')
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(blank=True, null=True)
    activo = models.BooleanField()

    def __str__(self):
        return f"{self.id_ruta} → {self.id_repartidor} (desde {self.fecha_inicio})"

    class Meta:
        managed = False
        db_table = 'asignaciones_ruta'


class Ciudades(models.Model):
    id_ciudad = models.AutoField(primary_key=True)
    id_pais = models.ForeignKey('Paises', models.DO_NOTHING, db_column='id_pais')
    nombre = models.CharField(max_length=100)
    
    def __str__(self):
        return f"{self.nombre} ({self.id_pais})"

    class Meta:
        managed = False
        db_table = 'ciudades'
        unique_together = (('id_pais', 'nombre'),)


class Clientes(models.Model):
    id_cliente = models.AutoField(primary_key=True)
    id_tipo_cliente = models.ForeignKey('TiposCliente', models.DO_NOTHING, db_column='id_tipo_cliente')
    razon_social = models.CharField(max_length=200)
    primer_nombre = models.CharField(max_length=100, blank=True, null=True)
    segundo_nombre = models.CharField(max_length=100, blank=True, null=True)
    primer_apellido = models.CharField(max_length=100, blank=True, null=True)
    segundo_apellido = models.CharField(max_length=100, blank=True, null=True)
    rtn = models.CharField(unique=True, max_length=20, blank=True, null=True)
    email = models.CharField(unique=True, max_length=150)
    password_hash = models.CharField(max_length=255, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    direccion = models.TextField(blank=True, null=True)
    id_ciudad = models.ForeignKey(Ciudades, models.DO_NOTHING, db_column='id_ciudad', blank=True, null=True)
    descuento_porcentaje = models.DecimalField(max_digits=10, decimal_places=2)
    activo = models.BooleanField()
    creado_por = models.ForeignKey('Usuarios', models.DO_NOTHING, db_column='creado_por', blank=True, null=True)

    def __str__(self):
        nombre = f"{self.primer_nombre or ''} {self.primer_apellido or ''}".strip()
        return nombre or self.razon_social

    class Meta:
        managed = False
        db_table = 'clientes'


class ConfiguracionesSar(models.Model):
    id_conf_sar = models.AutoField(primary_key=True)
    id_sucursal = models.ForeignKey('Sucursales', models.DO_NOTHING, db_column='id_sucursal')
    cai = models.CharField(unique=True, max_length=50)
    rango_inicial = models.CharField(max_length=20)
    rango_final = models.CharField(max_length=20)
    secuencia_actual = models.IntegerField()
    fecha_limite_emision = models.DateField()
    activo = models.BooleanField()

    def __str__(self):
        return f"CAI {self.cai} — {self.id_sucursal}"

    class Meta:
        managed = False
        db_table = 'configuraciones_sar'


class Envios(models.Model):
    id_envio = models.AutoField(primary_key=True)
    numero_tracking = models.UUIDField(unique=True)
    id_cliente = models.ForeignKey(Clientes, models.DO_NOTHING, db_column='id_cliente')
    id_via = models.ForeignKey('ViasEnvio', models.DO_NOTHING, db_column='id_via')
    id_tipo_servicio = models.ForeignKey('TiposServicio', models.DO_NOTHING, db_column='id_tipo_servicio')
    id_estado_actual = models.ForeignKey('EstadosEnvio', models.DO_NOTHING, db_column='id_estado_actual')
    id_ciudad_origen = models.ForeignKey(Ciudades, models.DO_NOTHING, db_column='id_ciudad_origen')
    id_ciudad_destino = models.ForeignKey(Ciudades, models.DO_NOTHING, db_column='id_ciudad_destino', related_name='envios_id_ciudad_destino_set')
    id_sucursal_origen = models.ForeignKey('Sucursales', models.DO_NOTHING, db_column='id_sucursal_origen')
    id_sucursal_destino = models.ForeignKey('Sucursales', models.DO_NOTHING, db_column='id_sucursal_destino', related_name='envios_id_sucursal_destino_set')
    id_ruta = models.ForeignKey('Rutas', models.DO_NOTHING, db_column='id_ruta')
    id_tarifa = models.ForeignKey('Tarifas', models.DO_NOTHING, db_column='id_tarifa')
    nombre_remitente = models.CharField(max_length=200)
    nombre_destinatario = models.CharField(max_length=200)
    telefono_destinatario = models.CharField(max_length=20, blank=True, null=True)
    direccion_destino = models.TextField()
    valor_declarado_hnl = models.DecimalField(max_digits=12, decimal_places=2)
    costo_flete_hnl = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    descuento_hnl = models.DecimalField(max_digits=12, decimal_places=2)
    costo_total_hnl = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    fecha_recepcion = models.DateTimeField()
    fecha_estimada = models.DateField(blank=True, null=True)
    fecha_entrega_real = models.DateTimeField(blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)
    creado_por = models.ForeignKey('Usuarios', models.DO_NOTHING, db_column='creado_por', blank=True, null=True)

    def __str__(self):
        return str(self.numero_tracking)

    class Meta:
        managed = False
        db_table = 'envios'


class EstadosEnvio(models.Model):
    id_estado = models.AutoField(primary_key=True)
    nombre = models.CharField(unique=True, max_length=100)
    es_estado_final = models.BooleanField(blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre

    class Meta:
        managed = False
        db_table = 'estados_envio'


class FacturaDetalle(models.Model):
    id_detalle = models.AutoField(primary_key=True)
    id_factura = models.ForeignKey('Facturas', models.DO_NOTHING, db_column='id_factura')
    id_envio = models.ForeignKey(Envios, models.DO_NOTHING, db_column='id_envio', blank=True, null=True)
    descripcion = models.TextField()
    cantidad = models.DecimalField(max_digits=8, decimal_places=2)
    precio_unitario_hnl = models.DecimalField(max_digits=12, decimal_places=2)
    descuento_linea_hnl = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal_linea_hnl = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.descripcion} — L.{self.subtotal_linea_hnl}"

    class Meta:
        managed = False
        db_table = 'factura_detalle'


class Facturas(models.Model):
    id_factura = models.AutoField(primary_key=True)
    # id_conf_sar fue removido — NO existe en la tabla facturas de la BD
    id_cliente = models.ForeignKey(Clientes, models.DO_NOTHING, db_column='id_cliente')
    id_sucursal = models.ForeignKey('Sucursales', models.DO_NOTHING, db_column='id_sucursal')
    id_usuario_emisor = models.ForeignKey('Usuarios', models.DO_NOTHING, db_column='id_usuario_emisor')
    numero_factura = models.CharField(unique=True, max_length=20)
    rtn_cliente = models.CharField(max_length=20, blank=True, null=True)
    nombre_cliente = models.CharField(max_length=200)
    fecha_emision = models.DateTimeField()
    subtotal_hnl = models.DecimalField(max_digits=12, decimal_places=2)
    descuento_hnl = models.DecimalField(max_digits=12, decimal_places=2)
    base_gravable_hnl = models.DecimalField(max_digits=12, decimal_places=2)
    isv_hnl = models.DecimalField(max_digits=12, decimal_places=2)
    total_hnl = models.DecimalField(max_digits=12, decimal_places=2)
    moneda = models.CharField(max_length=3)
    anulada = models.BooleanField()
    motivo_anulacion = models.TextField(blank=True, null=True)
    creado_por = models.ForeignKey('Usuarios', models.DO_NOTHING, db_column='creado_por', related_name='facturas_creado_por_set', blank=True, null=True)

    def __str__(self):
        return f"Factura {self.numero_factura} — {self.nombre_cliente}"

    class Meta:
        managed = False
        db_table = 'facturas'


class Paises(models.Model):
    id_pais = models.AutoField(primary_key=True)
    codigo_pais = models.CharField(unique=True, max_length=10)
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre

    class Meta:
        managed = False
        db_table = 'paises'


class Paquetes(models.Model):
    id_paquete = models.AutoField(primary_key=True)
    id_envio = models.ForeignKey(Envios, models.DO_NOTHING, db_column='id_envio')
    numero_paquete = models.IntegerField()
    descripcion_contenido = models.TextField(blank=True, null=True)
    largo_cm = models.DecimalField(max_digits=8, decimal_places=2)
    ancho_cm = models.DecimalField(max_digits=8, decimal_places=2)
    alto_cm = models.DecimalField(max_digits=8, decimal_places=2)
    peso_real_kg = models.DecimalField(max_digits=8, decimal_places=3)
    volumen_m3 = models.GeneratedField(
        expression=(F('largo_cm') * F('ancho_cm') * F('alto_cm')) / 1000000,
        output_field=models.DecimalField(max_digits=12, decimal_places=6),
        db_persist=True,
        blank=True,
        null=True,
    )
    peso_volumetrico_kg = models.DecimalField(max_digits=8, decimal_places=3, blank=True, null=True)
    peso_cobrable_kg = models.DecimalField(max_digits=8, decimal_places=3, blank=True, null=True)

    def __str__(self):
        return f"Paquete #{self.numero_paquete} de {self.id_envio}"

    class Meta:
        managed = False
        db_table = 'paquetes'
        unique_together = (('id_envio', 'numero_paquete'),)


class Repartidores(models.Model):
    id_repartidor = models.AutoField(primary_key=True)
    id_usuario = models.OneToOneField('Usuarios', models.DO_NOTHING, db_column='id_usuario')
    numero_licencia = models.CharField(unique=True, max_length=50, blank=True, null=True)
    tipo_vehiculo = models.CharField(max_length=80, blank=True, null=True)
    placa_vehiculo = models.CharField(max_length=20, blank=True, null=True)
    activo = models.BooleanField()

    def __str__(self):
        return f"{self.id_usuario} ({self.tipo_vehiculo or 'sin vehículo'})"

    class Meta:
        managed = False
        db_table = 'repartidores'


class Roles(models.Model):
    id_rol = models.AutoField(primary_key=True)
    nombre = models.CharField(unique=True, max_length=100)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre

    class Meta:
        managed = False
        db_table = 'roles'


class RutaZonas(models.Model):
    pk = models.CompositePrimaryKey('id_ruta', 'id_zona')
    id_ruta = models.ForeignKey('Rutas', models.DO_NOTHING, db_column='id_ruta')
    id_zona = models.ForeignKey('Zonas', models.DO_NOTHING, db_column='id_zona')

    def __str__(self):
        return f"{self.id_ruta} — {self.id_zona}"

    class Meta:
        managed = False
        db_table = 'ruta_zonas'


class Rutas(models.Model):
    id_ruta = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    id_sucursal = models.ForeignKey('Sucursales', models.DO_NOTHING, db_column='id_sucursal')
    activa = models.BooleanField()

    def __str__(self):
        return self.nombre

    class Meta:
        managed = False
        db_table = 'rutas'


class Seguimiento(models.Model):
    id_seguimiento = models.AutoField(primary_key=True)
    id_envio = models.ForeignKey(Envios, models.DO_NOTHING, db_column='id_envio')
    id_estado = models.ForeignKey(EstadosEnvio, models.DO_NOTHING, db_column='id_estado')
    id_usuario = models.ForeignKey('Usuarios', models.DO_NOTHING, db_column='id_usuario', blank=True, null=True)
    id_repartidor = models.ForeignKey(Repartidores, models.DO_NOTHING, db_column='id_repartidor', blank=True, null=True)
    id_sucursal = models.ForeignKey('Sucursales', models.DO_NOTHING, db_column='id_sucursal', blank=True, null=True)
    ubicacion_descripcion = models.TextField(blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)
    fecha_evento = models.DateTimeField()

    def __str__(self):
        return f"{self.id_envio} — {self.id_estado} ({self.fecha_evento:%d/%m/%Y %H:%M})"

    class Meta:
        managed = False
        db_table = 'seguimiento'


class Sucursales(models.Model):
    id_sucursal = models.AutoField(primary_key=True)
    codigosar = models.CharField(max_length=3, db_column='codigosar')  
    nombre = models.CharField(max_length=100)
    direccion = models.TextField()
    id_ciudad = models.ForeignKey(Ciudades, models.DO_NOTHING, db_column='id_ciudad')
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.CharField(max_length=150, blank=True, null=True)
    activa = models.BooleanField()

    def __str__(self):
        return f"{self.nombre} ({self.id_ciudad})"

    class Meta:
        managed = False
        db_table = 'sucursales'

class Tarifas(models.Model):
    id_tarifa = models.AutoField(primary_key=True)
    id_via = models.ForeignKey('ViasEnvio', models.DO_NOTHING, db_column='id_via')
    id_tipo_servicio = models.ForeignKey('TiposServicio', models.DO_NOTHING, db_column='id_tipo_servicio')
    id_ciudad_origen = models.ForeignKey(Ciudades, models.DO_NOTHING, db_column='id_ciudad_origen')
    id_ciudad_destino = models.ForeignKey(Ciudades, models.DO_NOTHING, db_column='id_ciudad_destino', related_name='tarifas_id_ciudad_destino_set')
    peso_min_kg = models.DecimalField(max_digits=10, decimal_places=3)
    peso_max_kg = models.DecimalField(max_digits=10, decimal_places=3)
    precio_base_hnl = models.DecimalField(max_digits=12, decimal_places=2)
    precio_por_kg_hnl = models.DecimalField(max_digits=10, decimal_places=2)
    precio_por_m3_hnl = models.DecimalField(max_digits=10, decimal_places=2)
    vigencia_desde = models.DateField()
    vigencia_hasta = models.DateField(blank=True, null=True)
    activa = models.BooleanField()

    def __str__(self):
        return f"{self.id_via} / {self.id_tipo_servicio}: {self.id_ciudad_origen} → {self.id_ciudad_destino}"

    class Meta:
        managed = False
        db_table = 'tarifas'
        unique_together = (('id_via', 'id_tipo_servicio', 'id_ciudad_origen', 'id_ciudad_destino', 'peso_min_kg', 'vigencia_desde'),)


class TiposCliente(models.Model):
    id_tipo_cliente = models.AutoField(primary_key=True)
    nombre = models.CharField(unique=True, max_length=100)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre

    class Meta:
        managed = False
        db_table = 'tipos_cliente'


class TiposServicio(models.Model):
    id_tipo_servicio = models.AutoField(primary_key=True)
    nombre = models.CharField(unique=True, max_length=100)
    factor_precio = models.DecimalField(max_digits=10, decimal_places=2)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre

    class Meta:
        managed = False
        db_table = 'tipos_servicio'


class Usuarios(models.Model):
    id_usuario = models.AutoField(primary_key=True)
    id_sucursal = models.ForeignKey(Sucursales, models.DO_NOTHING, db_column='id_sucursal')
    id_rol = models.ForeignKey(Roles, models.DO_NOTHING, db_column='id_rol')
    primer_nombre = models.CharField(max_length=100)
    segundo_nombre = models.CharField(max_length=100, blank=True, null=True)
    primer_apellido = models.CharField(max_length=100)
    segundo_apellido = models.CharField(max_length=100, blank=True, null=True)
    dni = models.CharField(unique=True, max_length=20, blank=True, null=True)
    email = models.CharField(unique=True, max_length=150)
    password_hash = models.CharField(max_length=255)
    activo = models.BooleanField()

    def __str__(self):
        return f"{self.primer_nombre} {self.primer_apellido}"

    class Meta:
        managed = False
        db_table = 'usuarios'


class ViasEnvio(models.Model):
    id_via = models.AutoField(primary_key=True)
    nombre = models.CharField(unique=True, max_length=100)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre

    class Meta:
        managed = False
        db_table = 'vias_envio'


class Zonas(models.Model):
    id_zona = models.AutoField(primary_key=True)
    id_ciudad = models.ForeignKey(Ciudades, models.DO_NOTHING, db_column='id_ciudad')
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.nombre} ({self.id_ciudad})"

    class Meta:
        managed = False
        db_table = 'zonas'
        unique_together = (('id_ciudad', 'nombre'),)