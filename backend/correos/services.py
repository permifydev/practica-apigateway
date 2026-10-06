"""Logica de envio de correos de solicitudes de BHE.

Flujo:
  1. La app Flet crea una solicitud -> la BD deja una fila 'pendiente' en
     correos_pendientes (trigger de la migracion 007).
  2. Este modulo toma cada fila 'pendiente', la marca 'enviando' (asi dos
     procesos nunca envian el mismo correo), arma el correo con el detalle
     de la solicitud y lo envia por SMTP.
  3. Marca la fila 'enviado', o la devuelve a 'pendiente' para reintentar,
     o la deja en 'error' despues de CORREOS_MAX_INTENTOS fallos.

El correo LLEGA al email con que se registro el usuario (perfiles.email).
Lo ENVIA la cuenta del sistema (EMAIL_HOST_USER) con el nombre de la empresa,
y "Responder" va directo al email del usuario de la empresa que lo solicito.
"""
import logging
from datetime import datetime, timezone

from cryptography.fernet import Fernet
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from supabase import create_client

logger = logging.getLogger(__name__)

MESES = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

_cliente = None


def cliente_supabase():
    """Cliente con service_role: puede leer correos_pendientes (la app no)."""
    global _cliente
    if _cliente is None:
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
            raise RuntimeError("Faltan SUPABASE_URL o SUPABASE_SERVICE_KEY en el .env")
        _cliente = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
    return _cliente


# ---------------------------------------------------------------- formato
def descifrar_rut(rut_cifrado):
    if not rut_cifrado or not settings.RUT_ENCRYPTION_KEY:
        return None
    try:
        return Fernet(settings.RUT_ENCRYPTION_KEY.encode()).decrypt(rut_cifrado.encode()).decode()
    except Exception:
        return None


def formato_rut(rut):
    """'76123456-0' -> '76.123.456-0'."""
    if not rut or "-" not in rut:
        return rut or "---"
    cuerpo, dv = rut.replace(".", "").split("-", 1)
    partes = []
    while len(cuerpo) > 3:
        partes.insert(0, cuerpo[-3:])
        cuerpo = cuerpo[:-3]
    partes.insert(0, cuerpo)
    return ".".join(partes) + "-" + dv.upper()


def clp(valor):
    try:
        return "$" + f"{float(valor or 0):,.0f}".replace(",", ".")
    except (TypeError, ValueError):
        return "$0"


def mes_texto(periodo):
    try:
        return f"{MESES[int(periodo[5:7])]} {periodo[0:4]}"
    except Exception:
        return str(periodo)


# ---------------------------------------------------------------- datos
def _uno(tabla, columnas, **filtros):
    q = cliente_supabase().table(tabla).select(columnas)
    for campo, valor in filtros.items():
        q = q.eq(campo, valor)
    datos = q.limit(1).execute().data
    return datos[0] if datos else None


def datos_del_correo(fila):
    """Junta todo lo que va en el correo a partir de una fila de correos_pendientes."""
    sol = _uno("solicitudes_bhe",
               "id, empresa_id, periodo, monto_ventas, comision_pct, monto_comision, "
               "monto_a_pagar, solicitado_por", id=fila["solicitud_id"])
    if not sol:
        raise ValueError("La solicitud ya no existe")
    emp = _uno("empresas", "nombre, rut_cifrado, direccion", id=sol["empresa_id"]) or {}
    usuario = _uno("perfiles", "nombre_completo, email", id=fila["destinatario_id"]) or {}
    solicitante = (_uno("perfiles", "nombre_completo, email", id=sol["solicitado_por"])
                   if sol.get("solicitado_por") else None) or {}

    return {
        "usuario_nombre": usuario.get("nombre_completo") or fila["destinatario_email"],
        "empresa_nombre": emp.get("nombre") or "La empresa",
        "empresa_rut": formato_rut(descifrar_rut(emp.get("rut_cifrado"))),
        "empresa_direccion": emp.get("direccion") or "---",
        "mes": mes_texto(sol["periodo"]),
        "ventas": clp(sol["monto_ventas"]),
        "comision_pct": f"{float(sol['comision_pct']):g}",
        "comision": clp(sol["monto_comision"]),
        "monto_boleta": clp(sol["monto_a_pagar"]),
        "responder_a": solicitante.get("email"),
    }


# ---------------------------------------------------------------- envio
def enviar_un_correo(fila):
    datos = datos_del_correo(fila)
    texto = render_to_string("correos/solicitud_bhe.txt", datos)
    html = render_to_string("correos/solicitud_bhe.html", datos)
    remitente = f'"{datos["empresa_nombre"]} via SII Connect" <{settings.EMAIL_HOST_USER}>'
    correo = EmailMultiAlternatives(
        subject=fila["asunto"],
        body=texto,
        from_email=remitente,
        to=[fila["destinatario_email"]],
        reply_to=[datos["responder_a"]] if datos["responder_a"] else None,
    )
    correo.attach_alternative(html, "text/html")
    correo.send(fail_silently=False)


def procesar_pendientes(limite=20):
    """Envia hasta `limite` correos pendientes. Devuelve un resumen."""
    db = cliente_supabase()
    pendientes = (db.table("correos_pendientes")
                  .select("id, solicitud_id, destinatario_id, destinatario_email, asunto, intentos")
                  .eq("estado", "pendiente")
                  .order("created_at")
                  .limit(limite)
                  .execute().data) or []

    resumen = {"enviados": 0, "reintentar": 0, "error": 0, "omitidos": 0}
    for fila in pendientes:
        # "Reservar" la fila: solo uno de los procesos logra pasarla a 'enviando'
        tomada = (db.table("correos_pendientes")
                  .update({"estado": "enviando"})
                  .eq("id", fila["id"]).eq("estado", "pendiente")
                  .execute().data)
        if not tomada:
            resumen["omitidos"] += 1
            continue

        intentos = (fila.get("intentos") or 0) + 1
        try:
            enviar_un_correo(fila)
            db.table("correos_pendientes").update({
                "estado": "enviado",
                "intentos": intentos,
                "enviado_at": datetime.now(timezone.utc).isoformat(),
                "ultimo_error": None,
            }).eq("id", fila["id"]).execute()
            resumen["enviados"] += 1
            logger.info(f"Correo enviado a {fila['destinatario_email']}")
        except Exception as e:
            definitivo = intentos >= settings.CORREOS_MAX_INTENTOS
            db.table("correos_pendientes").update({
                "estado": "error" if definitivo else "pendiente",
                "intentos": intentos,
                "ultimo_error": str(e)[:500],
            }).eq("id", fila["id"]).execute()
            resumen["error" if definitivo else "reintentar"] += 1
            logger.error(f"No se pudo enviar a {fila['destinatario_email']}: {e}")
    return resumen
