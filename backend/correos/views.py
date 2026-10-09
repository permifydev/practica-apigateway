import hmac

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .services import procesar_pendientes


def _token_valido(request):
    esperado = settings.CORREOS_API_TOKEN
    recibido = request.headers.get("X-Token", "")
    return bool(esperado) and hmac.compare_digest(esperado, recibido)


@csrf_exempt          # la llama la app Flet, no un formulario web
@require_POST
def enviar_pendientes(request):
    """POST /correos/enviar/  (header X-Token: CORREOS_API_TOKEN)
    La app Flet la llama justo despues de crear una solicitud, para que el
    correo salga al tiro en vez de esperar al envio periodico."""
    if not _token_valido(request):
        return JsonResponse({"ok": False, "error": "token invalido"}, status=401)
    try:
        resumen = procesar_pendientes()
        return JsonResponse({"ok": True, **resumen})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


@require_GET
def estado(request):
    """GET /correos/estado/ -> para comprobar que el servidor esta arriba."""
    return JsonResponse({"ok": True, "servicio": "backend"})
