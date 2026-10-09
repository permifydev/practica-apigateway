import re
import inspect
import datetime
from pathlib import Path

# sii_conect/src/utils/helpers.py -> sii_conect/assets/pdfs
CARPETA_ASSETS_PDF = Path(__file__).resolve().parent.parent.parent / "assets" / "pdfs"

MESES_ES = {
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
    "jul": 7, "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12,
}

def validar_rut(rut: str) -> bool:
    """Valida formato y digito verificador de un RUT chileno (ej. 12.345.678-9 o 12345678-9)."""
    if not rut:
        return False
    rut_limpio = re.sub(r"[.\s]", "", rut).upper()
    if "-" not in rut_limpio:
        return False
    cuerpo, dv = rut_limpio.rsplit("-", 1)
    if not cuerpo.isdigit() or not (1 <= len(cuerpo) <= 8):
        return False

    suma = 0
    multiplo = 2
    for digito in reversed(cuerpo):
        suma += int(digito) * multiplo
        multiplo = multiplo + 1 if multiplo < 7 else 2

    resto = 11 - (suma % 11)
    dv_esperado = {11: "0", 10: "K"}.get(resto, str(resto))
    return dv == dv_esperado


def formato_rut(rut: str) -> str:
    """Normaliza un RUT a formato sin puntos, con guion (ej. 12345678-9), para mostrar errores consistentes."""
    return re.sub(r"[.\s]", "", rut).upper() if rut else ""


def formato_rut_puntos(rut_crudo: str) -> str:
    """Formatea SOLO digitos (+ opcional K final) a RUT con puntos y guion mientras
    el usuario escribe, ej. '123456789' -> '12.345.678-9'. No valida el digito
    verificador (eso lo sigue haciendo validar_rut al enviar el formulario), solo
    da formato visual en vivo."""
    solo_validos = re.sub(r"[^0-9kK]", "", rut_crudo or "").upper()[:9]  # 8 digitos + DV
    if len(solo_validos) <= 1:
        return solo_validos

    cuerpo, dv = solo_validos[:-1], solo_validos[-1]
    partes = []
    while len(cuerpo) > 3:
        partes.insert(0, cuerpo[-3:])
        cuerpo = cuerpo[:-3]
    if cuerpo:
        partes.insert(0, cuerpo)
    return ".".join(partes) + "-" + dv


def activar_formato_rut_en_vivo(campo) -> None:
    """Conecta un ft.TextField para que el usuario solo tenga que tipear numeros
    (y la K si corresponde): los puntos y el guion se agregan solos mientras
    escribe. Uso: activar_formato_rut_en_vivo(mi_campo_rut) justo despues de
    crear el TextField, antes de usarlo en el layout.

    OJO: al reescribir field.value en cada tecla, el cursor del campo se va al
    final del texto (Flet no permite fijar la posicion del cursor en un
    TextField). Para un RUT (corto, se escribe de corrido de izquierda a
    derecha) no se nota en la practica."""
    on_change_previo = campo.on_change

    def on_change(e):
        formateado = formato_rut_puntos(campo.value)
        if formateado != campo.value:
            campo.value = formateado
            campo.update()
        if on_change_previo:
            on_change_previo(e)

    campo.on_change = on_change


def parse_monto(texto):
    """Convierte cualquier entrada a entero descartando caracteres no numéricos."""
    if not texto:
        return None
    solo_digitos = re.sub(r"[^\d]", "", str(texto))
    return int(solo_digitos) if solo_digitos else None

def formato_clp(monto):
    """Formatea entero como moneda chilena ($1.234.567)."""
    if monto is None:
        return "$0"
    return f"${monto:,.0f}".replace(",", ".")

def parse_fecha_bhe(texto):
    """Convierte texto tipo '28 jul 2026' a un objeto date real."""
    try:
        dia, mes_txt, anio = texto.strip().split()
        mes = MESES_ES[mes_txt.lower()[:3]]
        return datetime.date(int(anio), mes, int(dia))
    except Exception:
        return datetime.date.min

def mensaje_error_api(api_err) -> str:
    """Traduce un ApiGatewayError a un mensaje en español para el usuario final,
    siguiendo la tabla de codigos de la Academia de API Gateway
    (https://www.apigateway.cl/academy/primeros-pasos/punto-de-partida/manejo-de-errores).
    Si el SII/API Gateway trae un 'detail' especifico (ej. cuantos creditos faltan),
    se muestra tal cual porque suele ser mas preciso que un mensaje generico."""
    detalle_api = None
    if isinstance(getattr(api_err, "payload", None), dict):
        detalle_api = api_err.payload.get("detail")

    codigo = api_err.status_code
    mensajes = {
        400: "Solicitud invalida: revisa que todos los campos esten completos y con el formato correcto.",
        401: "Clave SII invalida, o la sesion con el SII se debe reautenticar. Vuelve a ingresar tu Clave SII.",
        402: "Creditos insuficientes en la conexion de API Gateway, o la IP de origen esta en uso por otra "
             "conexion sin creditos. Revisa tu cuenta en app.apigateway.cl.",
        403: "Tu conexion de API Gateway no tiene contratado este recurso. Revisa los productos activos en tu cuenta.",
        404: "El recurso solicitado no existe (revisa el folio/codigo ingresado).",
        405: "Metodo HTTP no permitido para este recurso (error de integracion, no del usuario).",
        406: "El formato de respuesta solicitado no es compatible con este recurso.",
        409: "Conflicto con los datos ya registrados en el SII para este documento.",
        410: "Este recurso ya no esta disponible en la version actual de la API.",
        423: "La cuenta de API Gateway esta bloqueada por incumplimiento de terminos. Contacta a soporte.",
        429: "Superaste el limite de peticiones del plan. Espera unos minutos antes de reintentar.",
    }

    base = mensajes.get(codigo, f"Error {codigo} de API Gateway." if codigo else "Error de conexion con API Gateway.")
    if detalle_api:
        return f"{base} Detalle: {detalle_api}"
    return base


async def _abrir_url(page, url: str):
    """page.launch_url() cambio de sincrono a asincrono segun la version de Flet.
    Este wrapper funciona con ambas: si devuelve una corutina, la espera."""
    resultado = page.launch_url(url)
    if inspect.isawaitable(resultado):
        await resultado


def mapear_estado_boleta(estado_api):
    """Traduce el estado que devuelve la API Gateway al enum estado_boleta de Supabase."""
    if not estado_api:
        return "pendiente"
    estado_normalizado = str(estado_api).strip().upper()
    mapa = {
        "EMITIDA": "emitida",
        "PAGADA": "pagada",
        "VENCIDA": "vencida",
        "ANULADA": "anulada",
    }
    return mapa.get(estado_normalizado, "pendiente")


def fecha_corta(valor) -> str:
    """'2026-10-06T00:00:00+00:00' (o '2026-10-06') -> '06-10-2026'. Si no se
    reconoce el formato, devuelve el valor tal cual (o '---' si viene vacio)."""
    txt = str(valor or "").strip()
    if len(txt) >= 10 and txt[4] == "-" and txt[7] == "-":
        return f"{txt[8:10]}-{txt[5:7]}-{txt[0:4]}"
    return txt or "---"
