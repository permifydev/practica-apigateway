"""Panel de administracion: que se ve y que se puede editar de cada tabla.

Regla general: SOLO LECTURA, salvo lo que es seguro tocar a mano:
  - Usuarios: nombre, rol, estado y empresa
  - Empresas: nombre, direccion y % de comision
  - Ventas: crear, editar y borrar (para cargar datos de prueba)
  - Solicitudes: cambiar el estado
  - Correos: reintentar o enviar ahora
Lo que viene del SII (boletas, historial, certificados, cache) no se edita aca.
Los RUT se guardan cifrados
"""

from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django import forms

from django.utils.html import format_html

from correos.services import cliente_supabase, descifrar_rut, procesar_pendientes
from .models import (Boleta, BoletaRecibida, CertificadoDigital, CorreoPendiente, Empresa,
                     HistorialBHE, Notificacion, Perfil, Receptor, SolicitudBHE, Venta)


def clp(valor):
    try:
        return "$" + f"{float(valor or 0):,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return "$0"


def rut_legible(cifrado):
    if not cifrado:
        return "Sin RUT"
    return "Registrado" if descifrar_rut(cifrado) else "No se puede leer"


class SoloLectura(admin.ModelAdmin):
    """Se ve todo, no se crea, edita ni borra nada."""

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class SinCrearNiBorrar(admin.ModelAdmin):
    """Se pueden editar algunos campos, pero no crear ni borrar filas."""

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# ------------------------------------------------------------------ usuarios
@admin.register(Perfil)
class PerfilAdmin(SinCrearNiBorrar):
    list_display = ("nombre_completo", "email", "rol", "empresa", "rut", "id")
    list_filter = ("rol", "empresa")
    search_fields = ("nombre_completo", "email")
    fields = ("id","nombre_completo", "email", "rol", "estado", "empresa", "rut", "created_at")
    readonly_fields = ("id","email", "rut", "created_at")

    @admin.display(description="RUT")
    def rut(self, obj):
        return rut_legible(obj.rut_cifrado)


@admin.register(Empresa)
class EmpresaAdmin(SinCrearNiBorrar):
    list_display = ("nombre", "rut", "direccion", "comision")
    search_fields = ("nombre",)
    fields = ("nombre", "rut", "direccion", "comision_pct", "receptor", "created_at")
    readonly_fields = ("rut", "receptor", "created_at")

    @admin.display(description="RUT")
    def rut(self, obj):
        return rut_legible(obj.rut_cifrado)

    @admin.display(description="Comision")
    def comision(self, obj):
        return f"{obj.comision_pct:g}%"


@admin.register(Receptor)
class ReceptorAdmin(SoloLectura):
    list_display = ("nombre", "rut", "usuario", "email")
    list_filter = ("usuario",)
    search_fields = ("nombre", "email")
    exclude = ("rut_cifrado", "rut_hash")
    readonly_fields = ("rut",)

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
class VentaAdmin(admin.ModelAdmin):
    form = VentaForm
    list_display = ("periodo_mes", "empresa", "emisor", "monto_clp", "descripcion")
    list_filter = ("empresa", "periodo")
    search_fields = ("emisor__nombre_completo", "emisor__email", "descripcion")
    date_hierarchy = "periodo"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "emisor":
            kwargs["queryset"] = Perfil.objects.filter(rol="emisor")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    @admin.display(description="Mes", ordering="periodo")
    def periodo_mes(self, obj):
        return obj.periodo.strftime("%m/%Y")

    @admin.display(description="Monto", ordering="monto")
    def monto_clp(self, obj):
        return clp(obj.monto)


@admin.register(SolicitudBHE)
class SolicitudBHEAdmin(SinCrearNiBorrar):
    list_display = ("created_at", "empresa", "emisor", "periodo_mes", "ventas", "comision",
                    "a_pagar", "estado")
    list_filter = ("estado", "empresa", "periodo")
    search_fields = ("emisor__nombre_completo", "emisor__email")
    readonly_fields = ("empresa", "emisor", "periodo", "monto_ventas", "comision_pct",
                       "monto_comision", "monto_a_pagar", "solicitado_por", "created_at")
    fields = readonly_fields[:7] + ("estado",) + readonly_fields[7:]

    @admin.display(description="Mes", ordering="periodo")
    def periodo_mes(self, obj):
        return obj.periodo.strftime("%m/%Y")

    @admin.display(description="Ventas")
    def ventas(self, obj):
        return clp(obj.monto_ventas)

    @admin.display(description="Comision")
    def comision(self, obj):
        return f"{clp(obj.monto_comision)} ({obj.comision_pct:g}%)"

    @admin.display(description="A pagar")
    def a_pagar(self, obj):
        return clp(obj.monto_a_pagar)


@admin.register(Notificacion)
class NotificacionAdmin(SoloLectura):
    list_display = ("created_at", "usuario", "titulo", "leida")
    list_filter = ("leida", "tipo")
    search_fields = ("usuario__nombre_completo", "usuario__email", "mensaje")


@admin.register(CorreoPendiente)
class CorreoPendienteAdmin(SoloLectura):
    list_display = ("created_at", "destinatario_email", "asunto", "estado", "intentos",
                    "enviado_at", "ultimo_error")
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
@admin.register(Boleta)
class BoletaAdmin(SoloLectura):
    list_display = ("folio_sii", "fecha_emision", "usuario", "receptor", "bruto", "liquido",
                    "estado", "es_test", "tiene_pdf")
    list_filter = ("estado", "es_test")
    search_fields = ("folio_sii", "usuario__nombre_completo", "receptor__nombre")
    exclude = ("rut_emisor_cifrado",)
    readonly_fields = ("ver_pdf",)

    @admin.display(description="Bruto", ordering="monto_bruto")
    def bruto(self, obj):
        return clp(obj.monto_bruto)

    @admin.display(description="Liquido", ordering="monto_liquido")
    def liquido(self, obj):
        return clp(obj.monto_liquido)

    @admin.display(description="PDF", boolean=True)
    def tiene_pdf(self, obj):
        return bool(obj.pdf_path)

    @admin.display(description="Abrir PDF")
    def ver_pdf(self, obj):
        """Enlace firmado (10 minutos) al PDF guardado en Storage. No llama a la
        API del SII, asi que no gasta creditos."""
        if not obj.pdf_path:
            return "Sin PDF guardado"
        try:
            r = cliente_supabase().storage.from_("pdf_boletas").create_signed_url(obj.pdf_path, 600)
            url = r.get("signedURL") or r.get("signedUrl") or r.get("signed_url")
        except Exception as e:
            return f"No se pudo generar el enlace: {e}"
        if not url:
            return "No se pudo generar el enlace."
        return format_html('<a href="{}" target="_blank" rel="noopener">Abrir PDF (enlace valido 10 minutos)</a>', url)

@admin.register(HistorialBHE)
class HistorialBHEAdmin(SoloLectura):
    list_display = ("fecha", "boleta", "usuario", "tipo_evento", "detalle")
    list_filter = ("tipo_evento",)


@admin.register(CertificadoDigital)
class CertificadoDigitalAdmin(SoloLectura):
    list_display = ("alias", "usuario", "fecha_carga", "fecha_vencimiento", "estado")
    list_filter = ("estado",)


@admin.register(BoletaRecibida)
class BoletaRecibidaAdmin(SoloLectura):
    list_display = ("periodo", "folio", "emisor_nombre", "emisor_rut", "fecha", "monto",
                    "estado", "receptor_usuario")
    list_filter = ("periodo", "estado")
    exclude = ("emisor_rut_cifrado", "emisor_rut_hash")

    @admin.display(description="RUT emisor")
    def emisor_rut(self, obj):
        return rut_legible(obj.emisor_rut_cifrado)

    @admin.display(description="Monto", ordering="monto_bruto")
    def monto(self, obj):
        return clp(obj.monto_bruto)
