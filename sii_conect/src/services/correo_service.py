"""Le avisa al backend Django (carpeta backend/) que hay correos nuevos para enviar.

La solicitud y el correo en cola ya quedaron guardados en Supabase ANTES de
llamar esto: si Django no esta corriendo o falla, no se pierde nada; el correo
sigue 'pendiente' y sale en el siguiente envio (python manage.py enviar_correos).

Variables en el .env de la raiz del proyecto:
  CORREOS_API_URL    ej. http://127.0.0.1:8000/correos/enviar/
  CORREOS_API_TOKEN  el mismo valor que usa Django
"""
import logging
import os

import requests

logger = logging.getLogger(__name__)


def pedir_envio_correos() -> bool:
    """True si Django confirmo al menos un correo enviado."""
    url = os.getenv("CORREOS_API_URL")
    token = os.getenv("CORREOS_API_TOKEN")
    if not url or not token:
        return False
    try:
        r = requests.post(url, headers={"X-Token": token}, timeout=10)
        datos = r.json() if r.ok else {}
        return bool(datos.get("enviados"))
    except Exception as e:
        logger.warning(f"El backend Django no respondio ({e}); el correo queda en cola")
        return False
