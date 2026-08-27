import flet as ft
from src.utils.constants import NAVY, GREY_TEXT, RED_TEXT, CARD_RADIUS
from src.services.supabase_service import SupabaseService

db_service = SupabaseService()

def build_login(page: ft.Page, state: dict, navigate_to):
    email_field = ft.TextField(
        label="Correo electrónico o RUT",
        hint_text="tu@empresa.cl o 11.111.111-1",
        color=NAVY,
        label_style=ft.TextStyle(color=GREY_TEXT),
        border_radius=10,
        border_color="#D8DCE3",
        bgcolor="white",
        height=52,
    )
    pass_field = ft.TextField(
        label="Contraseña",
        hint_text="********",
        password=True,
        can_reveal_password=True,
        color=NAVY,
        label_style=ft.TextStyle(color=GREY_TEXT),
        border_radius=10,
        border_color="#D8DCE3",
        bgcolor="white",
        height=52,
    )
    
    error_text = ft.Text("", color=RED_TEXT, size=12)

    def do_login(e):
        user_input = (email_field.value or "").strip()
        pass_input = (pass_field.value or "").strip()

        if not user_input or not pass_input:
            error_text.value = "Ingresa correo/RUT y contraseña para continuar"
            page.update()
            return

        # Validar si el usuario existe en la tabla perfiles
        usuario_db = db_service.validar_usuario(user_input)

        if usuario_db:
            state["logged_in"] = True
            state["usuario"] = usuario_db  # Mantiene dict completo con ID, Nombre, RUT y Rol
            state["nombre"] = usuario_db.get("nombre", "Usuario")
            error_text.value = ""
            navigate_to("Inicio")
        else:
            error_text.value = "Acceso denegado: Usuario no registrado en el sistema"
            page.update()

    return ft.Container(
        width=420,
        padding=24,
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=0,
            controls=[
                ft.Container(height=60),
                ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    controls=[
                        ft.Container(
                            width=44, height=44, bgcolor=NAVY, border_radius=10,
                            alignment=ft.Alignment.CENTER,
                            content=ft.Text("S", color="white", size=20, weight=ft.FontWeight.BOLD),
                        ),
                        ft.Container(width=10),
                        ft.Column(
                            spacing=0,
                            horizontal_alignment=ft.CrossAxisAlignment.START,
                            controls=[
                                ft.Text("SII Connect", size=18, weight=ft.FontWeight.BOLD, color=NAVY),
                                ft.Text("API Servicios Impuestos Internos", size=11, color=GREY_TEXT),
                            ],
                        ),
                    ],
                ),
                ft.Container(height=28),
                ft.Container(
                    bgcolor="white",
                    border_radius=CARD_RADIUS,
                    padding=24,
                    shadow=ft.BoxShadow(blur_radius=20, color="#1A000000", offset=ft.Offset(0, 6)),
                    content=ft.Column(
                        spacing=14,
                        controls=[
                            ft.Text("Iniciar sesión", size=22, weight=ft.FontWeight.BOLD, color=NAVY),
                            ft.Text("Accede a tu cuenta SII Connect", size=13, color=GREY_TEXT),
                            ft.Container(height=6),
                            email_field,
                            pass_field,
                            error_text,
                            ft.Container(height=6),
                            ft.ElevatedButton(
                                content=ft.Text("Ingresar"),
                                width=400,
                                height=48,
                                style=ft.ButtonStyle(
                                    bgcolor=NAVY, color="white",
                                    shape=ft.RoundedRectangleBorder(radius=10),
                                    text_style=ft.TextStyle(weight=ft.FontWeight.BOLD, size=15),
                                ),
                                on_click=do_login,
                            ),
                        ],
                    ),
                ),
                ft.Container(height=20),
                ft.Text("Acceso restringido a usuarios autorizados", size=11, color=GREY_TEXT, text_align=ft.TextAlign.CENTER),
            ],
        ),
    )