import flet as ft
from src.utils.constants import NAVY, GREY_TEXT, RED_TEXT, CARD_RADIUS
from src.services.supabase_service import SupabaseService

def build_login(page: ft.Page, state: dict, navigate_to):
    db_service = SupabaseService()

    def ir_a_password(e):
        pass_field.focus()

    email_field = ft.TextField(
        label="Correo electrónico",
        hint_text="tu@empresa.cl",
        color=NAVY,
        label_style=ft.TextStyle(color=GREY_TEXT),
        border_radius=10,
        border_color="#D8DCE3",
        bgcolor="white",
        height=52,
        on_submit=ir_a_password,
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
            error_text.value = "Ingresa correo y contraseña para continuar"
            page.update()
            return

        if db_service.client:
            auth_user = db_service.iniciar_sesion(user_input, pass_input)
            if not auth_user:
                error_text.value = "Correo o contraseña incorrectos"
                page.update()
                return

            usuario_db = db_service.obtener_perfil_propio(auth_user["id"])
            if not usuario_db:
                error_text.value = (
                    "Tu cuenta existe pero no tiene un perfil asociado en 'perfiles'. "
                    "Contacta al administrador."
                )
                page.update()
                return
        else:
            usuario_db = db_service.validar_usuario(user_input)
            if not usuario_db:
                error_text.value = "Acceso denegado: Usuario no registrado en el sistema"
                page.update()
                return

        state["logged_in"] = True
        state["usuario"] = usuario_db
        state["nombre"] = usuario_db.get("nombre", "Usuario")
        page.session.set("db_service", db_service)
        error_text.value = ""
        navigate_to("Inicio")

    pass_field.on_submit = do_login

    return ft.Container(
        width=420,
        padding=24,
        expand=True,
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=0,
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                ft.Container(height=60),
                ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    controls=[
                        ft.Container(
                            width=44, height=44, bgcolor=NAVY, border_radius=10,
                            alignment=ft.alignment.Alignment(0, 0),
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
                                content=ft.Text("Ingresar", weight=ft.FontWeight.BOLD, size=15),
                                width=400,
                                height=48,
                                style=ft.ButtonStyle(
                                    bgcolor=NAVY, color="white",
                                    shape=ft.RoundedRectangleBorder(radius=10),
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