import re
import base64
import inspect
import datetime

MESES_ES = {
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
    "jul": 7, "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12,
}

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


async def abrir_pdf_resultado(page, resultado: dict) -> str:
    """Abre en el navegador el PDF devuelto por descargar_pdf/descargar_pdf_recibida
    (que puede venir como bytes binarios o, en modo mock, como una URL) y devuelve
    el texto de estado a mostrar al usuario."""
    pdf_bytes = resultado.get("pdf_bytes")
    data = resultado.get("data") or {}

    if pdf_bytes:
        b64 = base64.b64encode(pdf_bytes).decode("ascii")
        await _abrir_url(page, f"data:application/pdf;base64,{b64}")
        return "PDF abierto en una pestaña nueva."

    pdf_url = data.get("pdf_url")
    if pdf_url:
        await _abrir_url(page, pdf_url)
        return f"PDF abierto: {pdf_url}"

    return "El SII no devolvió un PDF para este documento."


def mapear_estado_boleta(estado_api):
    """Traduce el estado que devuelve la API Gateway al enum estado_boleta de Supabase."""
    if not estado_api:
        return "pendiente"
    estado_normalizado = str(estado_api).strip().upper()
    mapa = {
        "EMITIDA": "pendiente",
        "PAGADA": "pagada",
        "VENCIDA": "vencida",
        "ANULADA": "anulada",
    }
    return mapa.get(estado_normalizado, "pendiente")
    