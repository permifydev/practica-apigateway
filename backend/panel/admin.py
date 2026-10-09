"""Panel de administracion: que se ve y que se puede editar de cada tabla.

Regla general: SOLO LECTURA, salvo lo que es seguro tocar a mano:
  - Usuarios: nombre, rol, estado y empresa
  - Empresas: nombre, direccion y % de comision
  - Ventas: crear, editar y borrar (para cargar datos de prueba)
  - Solicitudes: cambiar el estado
  - Correos: reintentar o enviar ahora
Lo que viene del SII (boletas, movimientos, certificados, cache) no se edita aca.
Los RUT se guardan cifrados
"""

from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django import forms
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
from django.db.models import Count, IntegerField, OuterRef, Subquery
from django.http import Http404, HttpResponseRedirect
from django.urls import path, reverse
from django.utils.html import format_html

from correos.services import cliente_supabase, descifrar_rut, procesar_pendientes
from .models import (Boleta, BoletaRecibida, CertificadoDigital, CorreoPendiente, Empresa,
                     HistorialBHE, Notificacion, Perfil, Receptor, SolicitudBHE, Venta)


def clp(valor):
    try:
        return "$" + f"{float(valor or 0):,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return "$0"


def fecha_boleta(valor):
    """El SII entrega solo la fecha (sin hora) y se guarda como medianoche UTC.
    Se muestra en UTC para que no aparezca como el dia anterior a las 21:00."""
    return valor.astimezone(timezone.utc).strftime("%d-%m-%Y") if valor else "---"


def url_firmada_pdf(ruta, segundos=600):
    """URL firmada (temporal) del PDF guardado en Storage. No llama a la API del
    SII, asi que no gasta creditos. None si no se pudo generar."""
    r = cliente_supabase().storage.from_("pdf_boletas").create_signed_url(ruta, segundos)
    return r.get("signedURL") or r.get("signedUrl") or r.get("signed_url")


def enlace(obj, texto=None):
    """Nombre del registro relacionado como enlace a su ficha en el panel."""
    if obj is None:
        return "---"
    url = reverse(f"admin:{obj._meta.app_label}_{obj._meta.model_name}_change", args=[obj.pk])
    return format_html('<a href="{}">{}</a>', url, texto or str(obj))


def enlace_lista(modelo, filtros, texto):
    """Enlace a la lista de 'modelo' ya filtrada (ej. las boletas de un receptor)."""
    url = reverse(f"admin:{modelo._meta.app_label}_{modelo._meta.model_name}_changelist")
    url += "?" + "&".join(f"{k}={v}" for k, v in filtros.items())
    return format_html('<a href="{}">{}</a>', url, texto)


def contar(modelo, campo):
    """Subconsulta que cuenta filas de 'modelo' que apuntan al registro (sin una
    consulta por fila de la lista)."""
    sub = modelo.objects.filter(**{campo: OuterRef("pk")}).order_by() \
        .values(campo).annotate(c=Count("pk")).values("c")
    return Subquery(sub, output_field=IntegerField())


def plural(n, singular, plural_txt):
    return f"{n} {singular if n == 1 else plural_txt}"


def enlace_pdf(boleta, texto="Abrir PDF"):
    """Enlace a la vista del panel que firma el PDF recien al hacer clic (asi
    una lista de boletas no hace una consulta a Storage por cada fila)."""
    if not boleta.pdf_path:
        return "Sin PDF"
    url = reverse("admin:panel_boleta_pdf", args=[boleta.pk])
    return format_html('<a href="{}" target="_blank" rel="noopener">{}</a>', url, texto)


def rut_legible(cifrado):
    if not cifrado:
        return "Sin RUT"
    return "Registrado" if descifrar_rut(cifrado) else "No se puede leer"


class PanelAdmin(admin.ModelAdmin):
    """Base de todas las tablas del panel: el titulo de cada lista es el nombre
    de la tabla (ej. "Movimientos de boletas") en vez del texto de Django
    "Seleccione ... para ver"."""

    def changelist_view(self, request, extra_context=None):
        nombre = str(self.model._meta.verbose_name_plural)
        extra_context = {"title": nombre[:1].upper() + nombre[1:], **(extra_context or {})}
        return super().changelist_view(request, extra_context)


class SoloLectura(PanelAdmin):
    """Se ve todo, no se crea, edita ni borra nada."""

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class SinCrearNiBorrar(PanelAdmin):
    """Se pueden editar algunos campos, pero no crear ni borrar filas."""

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


MESES_NOMBRE = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto",
                "Septiembre", "Octubre", "Noviembre", "Diciembre"]


class MesFiltro(admin.SimpleListFilter):
    """Filtro 'Por mes': lista solo los meses que tienen boletas (si se emite
    una en noviembre, 'Noviembre' aparece solo). Se calcula en UTC, igual que
    la columna Fecha, para que ninguna boleta caiga en el mes equivocado."""
    title = "mes"
    parameter_name = "mes"
    campo = "fecha_emision"
    zona = timezone.utc
    solo_fecha = False  # True para columnas de tipo fecha sin hora (ej. periodo de ventas)

    def lookups(self, request, model_admin):
        qs = model_admin.get_queryset(request)
        if self.solo_fecha:
            meses = qs.dates(self.campo, "month", order="DESC")
        else:
            meses = qs.datetimes(self.campo, "month", order="DESC", tzinfo=self.zona)
        return [(m.strftime("%Y-%m"), f"{MESES_NOMBRE[m.month - 1]} {m.year}") for m in meses]

    def queryset(self, request, queryset):
        if not self.value():
            return queryset
        try:
            anio, mes = (int(x) for x in self.value().split("-"))
        except ValueError:
            return queryset
        if self.solo_fecha:
            desde = date(anio, mes, 1)
            hasta = date(anio + (mes == 12), mes % 12 + 1, 1)
        else:
            desde = datetime(anio, mes, 1, tzinfo=self.zona)
            hasta = datetime(anio + (mes == 12), mes % 12 + 1, 1, tzinfo=self.zona)
        return queryset.filter(**{f"{self.campo}__gte": desde, f"{self.campo}__lt": hasta})


class MesPeriodoFiltro(MesFiltro):
    """Por mes, para la columna 'periodo' (ventas, solicitudes, boletas recibidas)."""
    campo = "periodo"
    solo_fecha = True


# ------------------------------------------------------------------ usuarios
class BoletaDelUsuarioInline(admin.TabularInline):
    """La "carpeta" del usuario: sus boletas emitidas, solo lectura."""
    model = Boleta
    fk_name = "usuario"
    verbose_name = "boleta emitida"
    verbose_name_plural = "boletas emitidas (carpeta del usuario)"
    fields = ("folio_sii", "fecha", "receptor", "bruto", "liquido", "estado", "pdf")
    readonly_fields = fields
    ordering = ("-fecha_emision",)
    extra = 0
    can_delete = False
    show_change_link = True  # cada fila lleva al detalle de la boleta

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Fecha de emisión")
    def fecha(self, obj):
        return fecha_boleta(obj.fecha_emision)

    @admin.display(description="Bruto")
    def bruto(self, obj):
        return clp(obj.monto_bruto)

    @admin.display(description="Líquido")
    def liquido(self, obj):
        return clp(obj.monto_liquido)

    @admin.display(description="PDF")
    def pdf(self, obj):
        return enlace_pdf(obj)


@admin.register(Perfil)
class PerfilAdmin(SinCrearNiBorrar):
    list_display = ("nombre_completo", "email", "rol", "empresa_link", "rut", "boletas", "id")
    list_select_related = ("empresa",)
    inlines = (BoletaDelUsuarioInline,)

    def get_queryset(self, request):
        # Cuenta las boletas de cada usuario en la misma consulta (sin una consulta por fila)
        return super().get_queryset(request).annotate(n_boletas=contar(Boleta, "usuario"))

    @admin.display(description="Empresa", ordering="empresa__nombre")
    def empresa_link(self, obj):
        return enlace(obj.empresa)

    @admin.display(description="Boletas", ordering="n_boletas")
    def boletas(self, obj):
        n = obj.n_boletas or 0
        if not n:
            return "---"
        url = reverse("admin:panel_boleta_changelist") + f"?usuario__id__exact={obj.pk}"
        return format_html('<a href="{}">{} boleta{}</a>', url, n, "" if n == 1 else "s")
    list_filter = ("rol", "empresa")
    search_fields = ("nombre_completo", "email")
    fields = ("id","nombre_completo", "email", "rol", "estado", "empresa", "rut", "created_at")
    readonly_fields = ("id","email", "rut", "created_at")

    @admin.display(description="RUT")
    def rut(self, obj):
        return rut_legible(obj.rut_cifrado)


@admin.register(Empresa)
class EmpresaAdmin(SinCrearNiBorrar):
    list_display = ("nombre", "rut", "direccion", "comision", "receptor_link", "ventas", "solicitudes")
    list_select_related = ("receptor",)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            n_ventas=contar(Venta, "empresa"), n_solicitudes=contar(SolicitudBHE, "empresa"))

    @admin.display(description="Receptor (a quien se emiten las boletas)", ordering="receptor__nombre")
    def receptor_link(self, obj):
        return enlace(obj.receptor)

    @admin.display(description="Ventas", ordering="n_ventas")
    def ventas(self, obj):
        n = obj.n_ventas or 0
        return enlace_lista(Venta, {"empresa__id__exact": obj.pk}, plural(n, "venta", "ventas")) if n else "---"

    @admin.display(description="Solicitudes", ordering="n_solicitudes")
    def solicitudes(self, obj):
        n = obj.n_solicitudes or 0
        return enlace_lista(SolicitudBHE, {"empresa__id__exact": obj.pk},
                            plural(n, "solicitud", "solicitudes")) if n else "---"
    search_fields = ("nombre",)
    fields = ("nombre", "rut", "direccion", "comision_pct", "receptor", "created_at")
    readonly_fields = ("rut", "receptor", "created_at")

    @admin.display(description="RUT")
    def rut(self, obj):
        return rut_legible(obj.rut_cifrado)

    @admin.display(description="Comisión")
    def comision(self, obj):
        return f"{obj.comision_pct:g}%"


@admin.register(Receptor)
class ReceptorAdmin(SinCrearNiBorrar):
    """Se puede corregir nombre y email. El RUT (cifrado) y el usuario dueno no
    se tocan, y no se crean ni borran receptores (la app los crea al emitir)."""
    list_display = ("nombre", "rut", "usuario_link", "email", "boletas")
    list_filter = ("usuario",)
    list_select_related = ("usuario",)
    search_fields = ("nombre", "email")
    fields = ("nombre", "email", "usuario", "rut")

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(n_boletas=contar(Boleta, "receptor"))

    @admin.display(description="Usuario dueño", ordering="usuario__nombre_completo")
    def usuario_link(self, obj):
        return enlace(obj.usuario)

    @admin.display(description="Boletas", ordering="n_boletas")
    def boletas(self, obj):
        n = obj.n_boletas or 0
        return enlace_lista(Boleta, {"receptor__id__exact": obj.pk},
                            plural(n, "boleta", "boletas")) if n else "---"
    readonly_fields = ("usuario", "rut")

    @admin.display(description="RUT")
    def rut(self, obj):
        return rut_legible(obj.rut_cifrado)


# ------------------------------------------------------- ventas y comisiones
class VentaForm(forms.ModelForm):
    class Meta:
        model = Venta
        fields = ("empresa", "emisor", "periodo", "monto", "descripcion")

    def clean_periodo(self):
        periodo = self.cleaned_data["periodo"]
        if periodo and periodo.day != 1:
            raise ValidationError("El periodo debe ser el dia 1 del mes (ej. 01-09-2026 para septiembre).")
        return periodo

    def clean_emisor(self):
        emisor = self.cleaned_data["emisor"]
        if emisor and str(emisor.rol).lower() != "emisor":
            raise ValidationError("Solo se le pueden cargar ventas a usuarios con rol Emisor.")
        return emisor


@admin.register(Venta)
class VentaAdmin(PanelAdmin):
    form = VentaForm
    list_display = ("periodo_mes", "empresa_link", "emisor_link", "monto_clp", "descripcion")
    list_filter = ("empresa", "emisor", MesPeriodoFiltro)
    list_select_related = ("empresa", "emisor")
    search_fields = ("emisor__nombre_completo", "emisor__email", "descripcion")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "emisor":
            kwargs["queryset"] = Perfil.objects.filter(rol="emisor")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    @admin.display(description="Mes", ordering="periodo")
    def periodo_mes(self, obj):
        return f"{MESES_NOMBRE[obj.periodo.month - 1]} {obj.periodo.year}"

    @admin.display(description="Monto", ordering="monto")
    def monto_clp(self, obj):
        return clp(obj.monto)

    @admin.display(description="Empresa", ordering="empresa__nombre")
    def empresa_link(self, obj):
        return enlace(obj.empresa)

    @admin.display(description="Usuario", ordering="emisor__nombre_completo")
    def emisor_link(self, obj):
        return enlace(obj.emisor)


@admin.register(SolicitudBHE)
class SolicitudBHEAdmin(SinCrearNiBorrar):
    list_display = ("created_at", "empresa_link", "emisor_link", "periodo_mes", "ventas", "comision",
                    "a_pagar", "estado", "ver_ventas")
    list_select_related = ("empresa", "emisor")
    list_filter = ("estado", "empresa", MesPeriodoFiltro)
    search_fields = ("emisor__nombre_completo", "emisor__email")
    readonly_fields = ("empresa", "emisor", "periodo", "monto_ventas", "comision_pct",
                       "monto_comision", "monto_a_pagar", "solicitado_por", "created_at")
    fields = readonly_fields[:7] + ("estado",) + readonly_fields[7:]

    @admin.display(description="Mes", ordering="periodo")
    def periodo_mes(self, obj):
        return f"{MESES_NOMBRE[obj.periodo.month - 1]} {obj.periodo.year}"

    @admin.display(description="Ventas")
    def ventas(self, obj):
        return clp(obj.monto_ventas)

    @admin.display(description="Comisión")
    def comision(self, obj):
        return f"{clp(obj.monto_comision)} ({obj.comision_pct:g}%)"

    @admin.display(description="A pagar")
    def a_pagar(self, obj):
        return clp(obj.monto_a_pagar)

    @admin.display(description="Empresa", ordering="empresa__nombre")
    def empresa_link(self, obj):
        return enlace(obj.empresa)

    @admin.display(description="Usuario", ordering="emisor__nombre_completo")
    def emisor_link(self, obj):
        return enlace(obj.emisor)

    @admin.display(description="Ventas del mes")
    def ver_ventas(self, obj):
        """Las ventas que dieron origen a esta solicitud (mismo usuario, empresa y mes)."""
        return enlace_lista(Venta, {"empresa__id__exact": obj.empresa_id, "emisor__id__exact": obj.emisor_id,
                                    "periodo": obj.periodo.isoformat()}, "Ver ventas")


@admin.register(Notificacion)
class NotificacionAdmin(SoloLectura):
    list_display = ("created_at", "usuario_link", "titulo", "leida", "solicitud_link")
    list_select_related = ("usuario", "solicitud")

    @admin.display(description="Usuario", ordering="usuario__nombre_completo")
    def usuario_link(self, obj):
        return enlace(obj.usuario)

    @admin.display(description="Solicitud")
    def solicitud_link(self, obj):
        return enlace(obj.solicitud, "Ver solicitud") if obj.solicitud_id else "---"

    list_filter = ("leida", "tipo")
    search_fields = ("usuario__nombre_completo", "usuario__email", "mensaje")


@admin.register(CorreoPendiente)
class CorreoPendienteAdmin(SoloLectura):
    list_display = ("created_at", "destinatario_link", "asunto", "estado", "intentos",
                    "enviado_at", "ultimo_error", "solicitud_link")
    list_select_related = ("destinatario", "solicitud")

    @admin.display(description="Para", ordering="destinatario_email")
    def destinatario_link(self, obj):
        return enlace(obj.destinatario, obj.destinatario_email)

    @admin.display(description="Solicitud")
    def solicitud_link(self, obj):
        return enlace(obj.solicitud, "Ver solicitud")

    list_filter = ("estado",)
    search_fields = ("destinatario_email", "asunto")
    actions = ("reintentar", "enviar_ahora")

    @admin.action(description="Volver a poner en cola (reintentar)")
    def reintentar(self, request, queryset):
        n = queryset.exclude(estado="enviado").update(estado="pendiente", intentos=0, ultimo_error=None)
        self.message_user(request, f"{n} correo(s) vuelven a la cola.")

    @admin.action(description="Enviar ahora los correos pendientes")
    def enviar_ahora(self, request, queryset):
        try:
            r = procesar_pendientes()
            self.message_user(request, f"Enviados: {r['enviados']}  Reintentar: {r['reintentar']}  "
                                       f"Error: {r['error']}")
        except Exception as e:
            self.message_user(request, f"No se pudo enviar: {e}", level=messages.ERROR)


# ------------------------------------------------------- boletas (solo ver)
class ConPdfFiltro(admin.SimpleListFilter):
    title = "PDF guardado"
    parameter_name = "con_pdf"

    def lookups(self, request, model_admin):
        return (("si", "Con PDF"), ("no", "Sin PDF"))

    def queryset(self, request, queryset):
        if self.value() == "si":
            return queryset.exclude(pdf_path__isnull=True).exclude(pdf_path="")
        if self.value() == "no":
            return queryset.filter(pdf_path__isnull=True) | queryset.filter(pdf_path="")
        return queryset


@admin.register(Boleta)
class BoletaAdmin(SoloLectura):
    list_display = ("folio_sii", "fecha", "emisor_link", "receptor_link", "bruto", "liquido",
                    "estado", "es_test", "tiene_pdf")
    list_select_related = ("usuario", "receptor")
    list_filter = ("usuario", MesFiltro, "estado", ConPdfFiltro, "es_test")
    ordering = ("usuario__nombre_completo", "-fecha_emision")  # agrupadas por usuario, mas nuevas primero
    search_fields = ("folio_sii", "usuario__nombre_completo", "receptor__nombre")
    exclude = ("rut_emisor_cifrado",)
    readonly_fields = ("ver_pdf",)

    @admin.display(description="Bruto", ordering="monto_bruto")
    def bruto(self, obj):
        return clp(obj.monto_bruto)

    @admin.display(description="Líquido", ordering="monto_liquido")
    def liquido(self, obj):
        return clp(obj.monto_liquido)

    @admin.display(description="Fecha de emisión", ordering="fecha_emision")
    def fecha(self, obj):
        return fecha_boleta(obj.fecha_emision)

    @admin.display(description="Emisor", ordering="usuario__nombre_completo")
    def emisor_link(self, obj):
        return enlace(obj.usuario)

    @admin.display(description="Receptor", ordering="receptor__nombre")
    def receptor_link(self, obj):
        return enlace(obj.receptor)

    def get_urls(self):
        propias = [path("<path:object_id>/pdf/", self.admin_site.admin_view(self.abrir_pdf_vista),
                        name="panel_boleta_pdf")]
        return propias + super().get_urls()

    def abrir_pdf_vista(self, request, object_id):
        """Firma el PDF recien al hacer clic y redirige a el (enlace valido 10 min)."""
        boleta = self.get_object(request, object_id)
        if boleta is None or not self.has_view_permission(request, boleta) or not boleta.pdf_path:
            raise Http404("Esta boleta no tiene PDF guardado.")
        try:
            url = url_firmada_pdf(boleta.pdf_path)
        except Exception:
            url = None
        if not url:
            raise Http404("No se pudo abrir el PDF en Storage.")
        return HttpResponseRedirect(url)

    @admin.display(description="PDF", boolean=True)
    def tiene_pdf(self, obj):
        return bool(obj.pdf_path)

    @admin.display(description="Abrir PDF")
    def ver_pdf(self, obj):
        return enlace_pdf(obj, "Abrir PDF")


TIPOS_EVENTO = {"consulta_sii": "Consulta al SII", "anulacion": "Anulación", "emision": "Emisión"}


class TipoEventoFiltro(admin.SimpleListFilter):
    title = "qué pasó"
    parameter_name = "tipo"

    def lookups(self, request, model_admin):
        tipos = model_admin.get_queryset(request).order_by("tipo_evento") \
            .values_list("tipo_evento", flat=True).distinct()
        return [(t, TIPOS_EVENTO.get(t, t)) for t in tipos if t]

    def queryset(self, request, queryset):
        return queryset.filter(tipo_evento=self.value()) if self.value() else queryset


class MesHistorialFiltro(MesFiltro):
    # Los eventos tienen hora real: el mes se cuenta en hora de Chile
    campo = "fecha"
    zona = ZoneInfo("America/Santiago")


@admin.register(HistorialBHE)
class HistorialBHEAdmin(SoloLectura):
    list_display = ("fecha_hora", "boleta_link", "usuario_link", "que_paso", "detalle")
    list_filter = ("usuario", MesHistorialFiltro, TipoEventoFiltro)
    list_select_related = ("boleta", "usuario")
    search_fields = ("boleta__folio_sii", "usuario__nombre_completo", "usuario__email",
                     "detalle", "tipo_evento")
    search_help_text = "Busca por folio, nombre o correo del usuario, o texto del detalle (ej. 784, PDF, email)."

    @admin.display(description="Fecha", ordering="fecha")
    def fecha_hora(self, obj):
        return obj.fecha.astimezone(ZoneInfo("America/Santiago")).strftime("%d-%m-%Y %H:%M") if obj.fecha else "---"

    @admin.display(description="Qué pasó", ordering="tipo_evento")
    def que_paso(self, obj):
        return TIPOS_EVENTO.get(obj.tipo_evento, obj.tipo_evento)

    @admin.display(description="Boleta", ordering="boleta__folio_sii")
    def boleta_link(self, obj):
        return enlace(obj.boleta)

    @admin.display(description="Usuario", ordering="usuario__nombre_completo")
    def usuario_link(self, obj):
        return enlace(obj.usuario)


@admin.register(CertificadoDigital)
class CertificadoDigitalAdmin(SoloLectura):
    list_display = ("alias", "usuario_link", "fecha_carga", "fecha_vencimiento", "estado")
    list_filter = ("estado",)
    list_select_related = ("usuario",)

    @admin.display(description="Usuario", ordering="usuario__nombre_completo")
    def usuario_link(self, obj):
        return enlace(obj.usuario)


@admin.register(BoletaRecibida)
class BoletaRecibidaAdmin(SoloLectura):
    list_display = ("periodo", "folio", "emisor_nombre", "emisor_rut", "fecha", "monto",
                    "estado", "usuario_link")
    list_select_related = ("receptor_usuario",)

    @admin.display(description="Usuario", ordering="receptor_usuario__nombre_completo")
    def usuario_link(self, obj):
        return enlace(obj.receptor_usuario)
    list_filter = (MesPeriodoFiltro, "estado")
    exclude = ("emisor_rut_cifrado", "emisor_rut_hash")

    @admin.display(description="RUT emisor")
    def emisor_rut(self, obj):
        return rut_legible(obj.emisor_rut_cifrado)

    @admin.display(description="Monto", ordering="monto_bruto")
    def monto(self, obj):
        return clp(obj.monto_bruto)

# ------------------------------------------------- etiquetas en español
# Nombres de columnas y campos que ve el jefe en el panel (la base de datos no
# cambia: solo el texto que muestra Django). Con ayuda donde se presta a dudas.
ETIQUETAS = {
    Perfil: {"nombre_completo": "nombre", "created_at": "creado el"},
    Empresa: {"direccion": "dirección", "comision_pct": "comisión %", "created_at": "creada el"},
    Venta: {"emisor": "usuario", "periodo": "mes", "descripcion": "descripción", "created_at": "registrada el"},
    SolicitudBHE: {"monto_ventas": "ventas", "comision_pct": "comisión %", "monto_comision": "comisión",
                   "monto_a_pagar": "a pagar", "solicitado_por": "solicitado por", "created_at": "enviada el"},
    Notificacion: {"titulo": "título", "leida": "leída", "created_at": "creada el"},
    CorreoPendiente: {"destinatario": "para (usuario)", "destinatario_email": "para",
                      "ultimo_error": "motivo del error", "enviado_at": "enviado el", "created_at": "creado el"},
    Boleta: {"usuario": "emisor", "folio_sii": "folio", "fecha_emision": "fecha de emisión",
             "tasa_retencion": "tasa de retención", "monto_retenido": "retención",
             "monto_liquido": "monto líquido", "modo_retencion": "modo de retención",
             "descripcion": "descripción", "es_test": "de prueba", "respuesta_sii": "respuesta del SII",
             "pdf_path": "ruta del PDF", "certificado_id": "certificado", "created_at": "registrada el"},
    HistorialBHE: {"tipo_evento": "qué pasó"},
    CertificadoDigital: {"fecha_carga": "cargado el", "fecha_vencimiento": "vence el", "archivo_path": "archivo"},
    BoletaRecibida: {"emisor_nombre": "emisor", "actualizado_en": "actualizada el"},
}
AYUDAS = {
    CorreoPendiente: {
        "estado": "Pendiente: espera envío. Enviado: llegó bien. Error: falló 3 veces y se dejó de intentar.",
        "intentos": "Cuántas veces se trató de enviar. Se reintenta hasta 3 veces.",
        "ultimo_error": "Por qué falló el último intento (vacío si se envió bien).",
        "enviado_at": "Fecha y hora en que se envió con éxito.",
    },
    Boleta: {
        "es_test": "Boleta emitida en el ambiente de prueba (certificación) del SII.",
        "pdf_path": "Dónde está guardado el PDF en Storage. Lo usan VER PDF y DESCARGAR.",
    },
    SolicitudBHE: {"monto_a_pagar": "Ventas menos la comisión: el monto por el que el usuario debe emitir su boleta."},
}
for _modelo, _campos in ETIQUETAS.items():
    for _campo, _texto in _campos.items():
        _modelo._meta.get_field(_campo).verbose_name = _texto
for _modelo, _campos in AYUDAS.items():
    for _campo, _texto in _campos.items():
        _modelo._meta.get_field(_campo).help_text = _texto


# ------------------------------------------------- orden del menu del panel
# Django ordena las tablas alfabeticamente. Aca se ordenan como se usan, y las
# tablas tecnicas quedan aparte al final, en "Registros tecnicos".
ORDEN_MENU = ["Perfil", "Boleta", "HistorialBHE", "Receptor", "Empresa", "Venta", "SolicitudBHE",
              "Notificacion", "CorreoPendiente"]
TABLAS_TECNICAS = ["CertificadoDigital", "BoletaRecibida"]

_get_app_list_original = admin.site.get_app_list


def _get_app_list_ordenado(request, app_label=None):
    apps = _get_app_list_original(request, app_label)
    resultado = []
    for app in apps:
        if app["app_label"] != "panel":
            continue
        modelos = {m["object_name"]: m for m in app["models"]}
        principales = [modelos[n] for n in ORDEN_MENU if n in modelos]
        tecnicas = [modelos[n] for n in TABLAS_TECNICAS if n in modelos]
        otras = [m for n, m in modelos.items() if n not in ORDEN_MENU and n not in TABLAS_TECNICAS]
        resultado.append({**app, "models": principales + otras})
        if tecnicas:
            resultado.append({**app, "name": "Registros técnicos", "models": tecnicas})
    # Las cuentas para entrar al panel (usuarios de Django) van al final, con
    # nombres que no se confundan con los usuarios de la app.
    for app in apps:
        if app["app_label"] == "panel":
            continue
        if app["app_label"] == "auth":
            nombres = {"User": "Administradores del panel", "Group": "Grupos de permisos"}
            modelos = [{**m, "name": nombres.get(m["object_name"], m["name"])} for m in app["models"]]
            app = {**app, "name": "Acceso al panel", "models": modelos}
        resultado.append(app)
    return resultado


admin.site.get_app_list = _get_app_list_ordenado
