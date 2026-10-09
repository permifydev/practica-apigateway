"""Un solo servidor para todo SII Connect (una sola URL en Render).

  https://<servicio>.onrender.com/         -> app Flet (emisores y empresas)
  https://<servicio>.onrender.com/admin/   -> panel Django (administracion)

Como funciona: es una aplicacion ASGI muy chica que mira la ruta de cada
peticion y la entrega a Django (si empieza con /admin, /admin-static o
/correos) o a Flet (todo lo demas). Las dos apps siguen siendo las mismas de
siempre: sii_conect/main.py y backend/.

Local:   uvicorn servidor:app --reload
Render:  uvicorn servidor:app --host 0.0.0.0 --port $PORT
"""
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ / "backend"))      # paquete 'config' y apps de Django
sys.path.insert(0, str(RAIZ / "sii_conect"))   # paquete 'src' y main.py de Flet

# ----------------------------------------------------------------- Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
from django.core.asgi import get_asgi_application  # noqa: E402

django_app = get_asgi_application()

# ----------------------------------------------------------------- Flet
import flet.fastapi as flet_fastapi  # noqa: E402
from main import main as flet_main  # noqa: E402  (sii_conect/main.py)

flet_app = flet_fastapi.app(flet_main, assets_dir=str(RAIZ / "sii_conect" / "assets"))

# ----------------------------------------------------------------- reparto
RUTAS_DJANGO = ("/admin", "/admin-static/", "/correos/")


async def app(scope, receive, send):
    """Las rutas del panel van a Django; todo lo demas (incluido el arranque y
    cierre del servidor, 'lifespan') va a Flet."""
    if scope["type"] in ("http", "websocket") and scope["path"].startswith(RUTAS_DJANGO):
        await django_app(scope, receive, send)
    else:
        await flet_app(scope, receive, send)
