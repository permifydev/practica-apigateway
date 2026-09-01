import re
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
    