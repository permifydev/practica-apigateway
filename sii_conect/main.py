import flet as ft
import logging
import threading
from pathlib import Path
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

from src.utils.constants import BG
from src.views.login_view import build_login
from src.views.home_view import build_home
from src.views.emitir_view import build_emitir
from src.views.mis_boletas_view import build_mis_boletas
from src.views.certificados_view import build_certificados
from src.views.detalle_boleta_view import build_detalle_boleta
from src.views.verificar_autenticidad_view import build_verificar_autenticidad
from src.views.receptores_view import build_receptores
from src.views.perfil_view import build_perfil
from src.views.resumen_ingresos_view import build_resumen_ingresos
from src.views.notificaciones_view import build_notificaciones

def main(page: ft.Page):
    page.title = "SII Connect"
    page.bgcolor = BG
    page.window.width = 420
    page.window.height = 900
    page.padding = 0
    page.theme = ft.Theme(font_family="Roboto")
    page.theme_mode = ft.ThemeMode.LIGHT
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    state = {}

    # Cuando Flet termina la sesion de este navegador (pestaña cerrada sin
    # apretar "Cerrar sesion"), se cierra tambien su sesion en Supabase y se
    # libera su cliente. Solo afecta a esta persona.
    def al_cerrar_sesion_flet(e):
        db = state.get("db_service")
        if db is not None:
            db.cerrar_sesion()
        state.clear()

    page.on_close = al_cerrar_sesion_flet

    # Un cambio de pantalla a la vez: si se hace doble clic en el menu (o un
    # segundo clic mientras la pantalla anterior aun se construye), Flet atiende
    # los dos clics en paralelo y quedaban DOS pantallas una debajo de la otra
    # (menu lateral repetido). El candado los pone en fila.
    candado_navegacion = threading.RLock()  # RLock: permite que una pantalla redirija mientras se construye

    pantallas = {
        "Login": build_login,
        "Inicio": build_home,
        "Emitir": build_emitir,
        "Emitir BHE": build_emitir,
        "Mis BHE": build_mis_boletas,
        "Certificados": build_certificados,
        "Detalle Boleta": build_detalle_boleta,
        "Verificar Autenticidad": build_verificar_autenticidad,
        "Receptores": build_receptores,
        "Perfil": build_perfil,
        # Pantalla unica de la empresa (reemplaza "Resumen ingresos" y
        # "Solicitar emisión BHE", segun el dibujo del jefe)
        "Resumen ventas y comisiones": build_resumen_ingresos,
        "Notificaciones": build_notificaciones,
    }

    def navigate_to(screen_name):
        construir = pantallas.get(screen_name)
        if construir is None:
            logging.warning(f"Pantalla desconocida: {screen_name}")
            return
        with candado_navegacion:
            # Primero se construye la pantalla nueva (puede tardar si consulta
            # Supabase) y recien despues se reemplaza la anterior, de una vez.
            nueva = construir(page, state, navigate_to)
            page.controls.clear()
            page.add(nueva)
            page.update()

    # El login valida contra Supabase Auth y crea el cliente propio de esta
    # persona (ver login_view.py). Por eso la app siempre debe arrancar en Login.
    navigate_to("Login")

if __name__ == "__main__":
    ft.app(target=main, assets_dir="assets")