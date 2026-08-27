import flet as ft
from src.utils.constants import BG
from src.views.login_view import build_login
from src.views.home_view import build_home
from src.views.emitir_view import build_emitir
from src.views.documentos_view import build_documentos

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
            page.add(build_documentos(page, state, navigate_to))
        page.update()

    # Pantalla inicial
    navigate_to("Login")

if __name__ == "__main__":
    ft.app(target=main)