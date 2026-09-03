import flet as ft
from dotenv import load_dotenv
load_dotenv()  # carga variables desde .env si existe (no falla si no existe)

from src.utils.constants import BG
from src.views.login_view import build_login
from src.views.home_view import build_home
from src.views.emitir_view import build_emitir
from src.views.mis_boletas_view import build_mis_boletas
from src.views.certificados_view import build_certificados
from src.views.detalle_boleta_view import build_detalle_boleta
from src.views.boletas_recibidas_view import build_boletas_recibidas
from src.views.verificar_autenticidad_view import build_verificar_autenticidad
from src.views.receptores_view import build_receptores
from src.views.perfil_view import build_perfil

def main(page: ft.Page):
    page.title = "SII Connect"
    page.bgcolor = BG
    page.window.width = 420
    page.window.height = 900
    page.padding = 0
    page.theme = ft.Theme(font_family="Roboto")
    page.theme_mode = ft.ThemeMode.LIGHT
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    state = {"nombre": "María", "folio_boleta": 1204}

    def navigate_to(screen_name):
        page.controls.clear()
        if screen_name == "Login":
            page.add(build_login(page, state, navigate_to))
        elif screen_name == "Inicio":
            page.add(build_home(page, state, navigate_to))
        elif screen_name == "Emitir" or screen_name == "Emitir BHE":
            page.add(build_emitir(page, state, navigate_to))
        elif screen_name == "Mis BHE":
            page.add(build_mis_boletas(page, state, navigate_to))
        elif screen_name == "Certificados":
            page.add(build_certificados(page, state, navigate_to))
        elif screen_name == "Detalle Boleta":
            page.add(build_detalle_boleta(page, state, navigate_to))
        elif screen_name == "Boletas Recibidas":
            page.add(build_boletas_recibidas(page, state, navigate_to))
        elif screen_name == "Verificar Autenticidad":
            page.add(build_verificar_autenticidad(page, state, navigate_to))
        elif screen_name == "Receptores":
            page.add(build_receptores(page, state, navigate_to))
        elif screen_name == "Perfil":
            page.add(build_perfil(page, state, navigate_to))
        page.update()

    navigate_to("Login")

if __name__ == "__main__":
    ft.app(target=main)