"""Tablas de Supabase vistas desde Django.

managed = False  ->  Django NO crea, cambia ni borra estas tablas: solo las lee
(y edita filas donde el panel lo permite). La estructura se sigue cambiando
con SQL en Supabase, como siempre.
"""
import uuid

from django.db import models
from django.utils import timezone

ROLES = [
    ("emisor", "Emisor"),
    ("receptor", "Receptor (empresa)"),
    ("cliente", "Cliente"),
    ("contador", "Contador"),
]


class Perfil(models.Model):
    id = models.UUIDField(primary_key=True)
    nombre_completo = models.TextField(blank=True, null=True)
    email = models.TextField(blank=True, null=True)
    rol = models.CharField(max_length=20, choices=ROLES)
    estado = models.TextField(blank=True, null=True)
    rut_cifrado = models.TextField(blank=True, null=True)
    empresa = models.ForeignKey("Empresa", models.DO_NOTHING, db_column="empresa_id",
                                blank=True, null=True, related_name="usuarios")
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "perfiles"
        verbose_name = "usuario"
        verbose_name_plural = "usuarios (perfiles)"
        ordering = ["nombre_completo"]

    def __str__(self):
        return self.nombre_completo or self.email or str(self.id)


class Receptor(models.Model):
    id = models.UUIDField(primary_key=True)
    nombre = models.TextField()
    email = models.TextField(blank=True, null=True)
    usuario = models.ForeignKey(Perfil, models.DO_NOTHING, db_column="usuario_id",
                                blank=True, null=True, related_name="+")
    rut_hash = models.TextField(blank=True, null=True)
    rut_cifrado = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "receptores"
        verbose_name = "receptor"
        verbose_name_plural = "receptores"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Empresa(models.Model):
    id = models.UUIDField(primary_key=True)
    nombre = models.TextField()
    rut_cifrado = models.TextField()
    rut_hash = models.TextField()
    receptor = models.ForeignKey(Receptor, models.DO_NOTHING, db_column="receptor_id",
                                 related_name="+")
    direccion = models.TextField(blank=True, null=True)
    comision_pct = models.DecimalField("comision %", max_digits=5, decimal_places=2)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "empresas"
        verbose_name = "empresa"
        verbose_name_plural = "empresas"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Venta(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey(Empresa, models.DO_NOTHING, db_column="empresa_id",
                                related_name="ventas")
    emisor = models.ForeignKey(Perfil, models.DO_NOTHING, db_column="emisor_id",
                               related_name="ventas", verbose_name="usuario")
    periodo = models.DateField(help_text="Siempre el dia 1 del mes (ej. 01-09-2026 = septiembre)")
    monto = models.DecimalField(max_digits=14, decimal_places=0)
    descripcion = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        managed = False
        db_table = "ventas"
        verbose_name = "venta"
        verbose_name_plural = "ventas"
        ordering = ["-periodo"]

    def __str__(self):
        return f"{self.emisor} - {self.periodo:%m/%Y}"


class SolicitudBHE(models.Model):
    ESTADOS = [("pendiente", "Pendiente"), ("emitida", "Emitida"), ("anulada", "Anulada")]
    id = models.UUIDField(primary_key=True)
    empresa = models.ForeignKey(Empresa, models.DO_NOTHING, db_column="empresa_id", related_name="+")
    emisor = models.ForeignKey(Perfil, models.DO_NOTHING, db_column="emisor_id",
                               related_name="+", verbose_name="usuario")
    periodo = models.DateField()
    monto_ventas = models.DecimalField(max_digits=14, decimal_places=0)
    comision_pct = models.DecimalField("comision %", max_digits=5, decimal_places=2)
    monto_comision = models.DecimalField(max_digits=14, decimal_places=0)
    monto_a_pagar = models.DecimalField(max_digits=14, decimal_places=0)
    estado = models.CharField(max_length=20, choices=ESTADOS)
    solicitado_por = models.ForeignKey(Perfil, models.DO_NOTHING, db_column="solicitado_por",
                                       blank=True, null=True, related_name="+")
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "solicitudes_bhe"
        verbose_name = "solicitud de BHE"
        verbose_name_plural = "solicitudes de BHE"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.empresa} -> {self.emisor} ({self.periodo:%m/%Y})"


class Notificacion(models.Model):
    id = models.UUIDField(primary_key=True)
    usuario = models.ForeignKey(Perfil, models.DO_NOTHING, db_column="usuario_id", related_name="+")
    tipo = models.TextField()
    titulo = models.TextField()
    mensaje = models.TextField()
    solicitud = models.ForeignKey(SolicitudBHE, models.DO_NOTHING, db_column="solicitud_id",
                                  blank=True, null=True, related_name="+")
    leida = models.BooleanField()
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "notificaciones"
        verbose_name = "notificacion"
        verbose_name_plural = "notificaciones"
        ordering = ["-created_at"]

    def __str__(self):
        return self.titulo


class CorreoPendiente(models.Model):
    ESTADOS = [("pendiente", "Pendiente"), ("enviando", "Enviando"),
               ("enviado", "Enviado"), ("error", "Error")]
    id = models.UUIDField(primary_key=True)
    solicitud = models.ForeignKey(SolicitudBHE, models.DO_NOTHING, db_column="solicitud_id", related_name="+")
    destinatario = models.ForeignKey(Perfil, models.DO_NOTHING, db_column="destinatario_id", related_name="+")
    destinatario_email = models.TextField()
    asunto = models.TextField()
    estado = models.CharField(max_length=20, choices=ESTADOS)
    intentos = models.IntegerField()
    ultimo_error = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    enviado_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "correos_pendientes"
        verbose_name = "correo"
        verbose_name_plural = "correos (bandeja de salida)"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.destinatario_email} - {self.estado}"


class Boleta(models.Model):
    id = models.UUIDField(primary_key=True)
    usuario = models.ForeignKey(Perfil, models.DO_NOTHING, db_column="usuario_id",
                                related_name="+", verbose_name="emisor")
    receptor = models.ForeignKey(Receptor, models.DO_NOTHING, db_column="receptor_id",
                                 blank=True, null=True, related_name="+")
    certificado_id = models.UUIDField(blank=True, null=True)
    folio_sii = models.TextField(blank=True, null=True)
    monto_bruto = models.DecimalField(max_digits=14, decimal_places=0, blank=True, null=True)
    tasa_retencion = models.DecimalField(max_digits=6, decimal_places=4, blank=True, null=True)
    monto_retenido = models.DecimalField(max_digits=14, decimal_places=0, blank=True, null=True)
    monto_liquido = models.DecimalField(max_digits=14, decimal_places=0, blank=True, null=True)
    estado = models.CharField(max_length=30, blank=True, null=True)
    fecha_emision = models.DateTimeField(blank=True, null=True)
    fecha_vencimiento = models.DateField(blank=True, null=True)
    modo_retencion = models.IntegerField(blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True)
    es_test = models.BooleanField(blank=True, null=True)
    respuesta_sii = models.JSONField(blank=True, null=True)
    rut_emisor_cifrado = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "boletas"
        verbose_name = "boleta emitida"
        verbose_name_plural = "boletas emitidas"
        ordering = ["-fecha_emision"]

    def __str__(self):
        return f"Folio {self.folio_sii or '---'}"


class HistorialBHE(models.Model):
    id = models.UUIDField(primary_key=True)
    boleta = models.ForeignKey(Boleta, models.DO_NOTHING, db_column="boleta_id", related_name="+")
    usuario = models.ForeignKey(Perfil, models.DO_NOTHING, db_column="usuario_id", related_name="+")
    tipo_evento = models.CharField(max_length=40)
    detalle = models.TextField(blank=True, null=True)
    fecha = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "historial_bhe"
        verbose_name = "evento de boleta"
        verbose_name_plural = "historial de boletas"
        ordering = ["-fecha"]


class CertificadoDigital(models.Model):
    id = models.UUIDField(primary_key=True)
    usuario = models.ForeignKey(Perfil, models.DO_NOTHING, db_column="usuario_id", related_name="+")
    alias = models.TextField(blank=True, null=True)
    archivo_path = models.TextField(blank=True, null=True)
    fecha_carga = models.DateTimeField(blank=True, null=True)
    fecha_vencimiento = models.DateField(blank=True, null=True)
    estado = models.CharField(max_length=30, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "certificados_digitales"
        verbose_name = "certificado digital"
        verbose_name_plural = "certificados digitales"


class BoletaRecibida(models.Model):
    id = models.UUIDField(primary_key=True)
    receptor_usuario = models.ForeignKey(Perfil, models.DO_NOTHING, db_column="receptor_usuario_id",
                                         related_name="+", verbose_name="usuario")
    periodo = models.DateField()
    folio = models.TextField()
    codigo = models.TextField(blank=True, null=True)
    estado = models.TextField(blank=True, null=True)
    emisor_nombre = models.TextField(blank=True, null=True)
    emisor_rut_cifrado = models.TextField()
    emisor_rut_hash = models.TextField()
    fecha = models.DateField(blank=True, null=True)
    monto_bruto = models.DecimalField(max_digits=14, decimal_places=0, blank=True, null=True)
    actualizado_en = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "boletas_recibidas_cache"
        verbose_name = "boleta recibida (cache)"
        verbose_name_plural = "boletas recibidas (cache)"
        ordering = ["-periodo"]
