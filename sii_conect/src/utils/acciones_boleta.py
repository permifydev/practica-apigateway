"""Logica compartida por 'Detalle Boleta' y 'Mis BHE' para Ver PDF / Descargar / Enviar.

Ahorra creditos de apigateway.cl: el codigo SII y las URLs del PDF se guardan en
'state' (memoria de la sesion) y el PDF se busca primero en Supabase Storage antes
de pedirlo de nuevo al SII.
"""
import time
import uuid
import logging
from datetime import date

from src.services.api_gateway import ApiGatewayError
from src.utils.helpers import CARPETA_ASSETS_PDF

logger = logging.getLogger(__name__)

VIGENCIA_URL_SEG = 50 * 60  # las URLs firmadas duran 1 hora; se renuevan a los 50 min


def _clave_cache(rut_emisor: str, folio) -> str:
    return f"{(rut_emisor or '').replace('.', '').upper()}|{folio}"


def codigo_sii_de_boleta(api_client, state: dict, boleta: dict, rut_emisor: str, clave: str) -> str:
    """Codigo real que pide el SII para pdf/email (viene del listado, no de la emision)."""
    folio = str(boleta.get("folio_sii"))
    codigos = state.setdefault("codigos_sii", {})
    key = _clave_cache(rut_emisor, folio)
    if codigos.get(key):
        return codigos[key]
    try:
        fecha = str(boleta.get("fecha_emision") or "")
        periodo = fecha[:7].replace("-", "") if len(fecha) >= 7 else date.today().strftime("%Y%m")
        respuesta = api_client.listar_emitidas(rut=rut_emisor, clave=clave, emisor=rut_emisor, periodo=periodo)
        for b_sii in respuesta.get("boletas", []):
            if str(b_sii.get("folio") or b_sii.get("numero")) == folio and b_sii.get("codigo"):
                codigos[key] = b_sii["codigo"]
                return b_sii["codigo"]
    except ApiGatewayError:
        pass
    return (boleta.get("respuesta_sii") or {}).get("codigo") or folio


def preparar_pdf(api_client, db_service, state: dict, boleta: dict,
                 rut_emisor: str, clave: str, usuario_id: str) -> dict:
    """Deja el PDF listo y devuelve {'ver', 'descarga', 'origen', 'mensaje'}.
    origen: 'memoria' | 'supabase' (instantaneos) | 'sii' (se pidio al SII y se guardo).
    Lanza ApiGatewayError si el SII rechaza la peticion."""
    folio = str(boleta.get("folio_sii"))
    key = _clave_cache(rut_emisor, folio)
    cache = state.setdefault("pdf_urls", {})

    hit = cache.get(key)
    if hit and time.time() - hit["ts"] < VIGENCIA_URL_SEG:
        return {"ver": hit["ver"], "descarga": hit["descarga"], "origen": "memoria", "mensaje": "PDF listo."}

    urls = db_service.urls_pdf_boleta(usuario_id, folio)
    if urls:
        cache[key] = {**urls, "ts": time.time()}
        return {**urls, "origen": "supabase", "mensaje": "PDF listo (ya estaba guardado en Supabase)."}

    codigo = codigo_sii_de_boleta(api_client, state, boleta, rut_emisor, clave)
    resultado = api_client.descargar_pdf(rut=rut_emisor, clave=clave, codigo=codigo)
    pdf_bytes = resultado.get("pdf_bytes")
    data = resultado.get("data") or {}

    if pdf_bytes:
        urls = db_service.subir_pdf_boleta_urls(usuario_id, folio, pdf_bytes)
        if urls:
            cache[key] = {**urls, "ts": time.time()}
            return {**urls, "origen": "sii", "mensaje": "PDF listo y guardado en Supabase."}
        # Respaldo: disco local del servidor (dura hasta que se reinicie)
        CARPETA_ASSETS_PDF.mkdir(parents=True, exist_ok=True)
        nombre = f"boleta_{uuid.uuid4().hex[:12]}.pdf"
        (CARPETA_ASSETS_PDF / nombre).write_bytes(pdf_bytes)
        url_local = f"/pdfs/{nombre}"
        return {"ver": url_local, "descarga": url_local, "origen": "sii",
                "mensaje": "PDF listo (no se pudo guardar en Supabase, queda temporal en el servidor)."}

    if data.get("pdf_url"):
        return {"ver": data["pdf_url"], "descarga": data["pdf_url"], "origen": "sii", "mensaje": "PDF listo."}

    return {"ver": None, "descarga": None, "origen": "sii", "mensaje": "El SII no devolvio un PDF para este documento."}


def enviar_boleta_por_email(api_client, state: dict, boleta: dict, rut_emisor: str,
                            clave: str, email_destino: str | None = None) -> dict:
    codigo = codigo_sii_de_boleta(api_client, state, boleta, rut_emisor, clave)
    return api_client.enviar_email(rut=rut_emisor, clave=clave, codigo=codigo, email_destino=email_destino)


def recordar_codigos(state: dict, rut_emisor: str, boletas_sii: list) -> None:
    """Guarda en memoria el codigo real de cada folio del listado del SII, asi
    Ver PDF / Descargar / Enviar no tienen que volver a listar (ahorra creditos)."""
    codigos = state.setdefault("codigos_sii", {})
    for b_sii in boletas_sii:
        folio = b_sii.get("folio") or b_sii.get("numero")
        if folio and b_sii.get("codigo"):
            codigos[_clave_cache(rut_emisor, folio)] = b_sii["codigo"]