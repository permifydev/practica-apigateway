import flet as ft
from src.utils.constants import NAVY, GREY_TEXT, CARD_RADIUS



def build_perfil(page: ft.Page, state: dict, navigate_to):
    usuario_info = state.get("usuario", {})

    nombre = ft.TextField(label="Nombre completo", value=usuario_info.get("nombre", ""), disabled=True)
    rut = ft.TextField(label="RUT", value=usuario_info.get("rut", ""), disabled=True)
    rol = ft.TextField(label="Rol", value=str(usuario_info.get("rol", "")).capitalize(), disabled=True)
    email = ft.TextField(label="Correo", value=usuario_info.get("email", ""), disabled=True)

    return ft.Container(
        padding=20,
        expand=True,
        content=ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                ft.Row([
                    ft.TextButton("Volver", on_click=lambda e: navigate_to("Inicio")),
                    ft.Text("Mi Perfil", size=20, weight=ft.FontWeight.BOLD, color=NAVY)
                ]),
                ft.Container(
                    bgcolor="white", border_radius=CARD_RADIUS, padding=20, width=450,
                    content=ft.Column([
                        ft.Text(
                            "Estos datos los administra tu jefe o administrador. Si necesitas cambiar alguno, pideselo a el.",
                            size=11, color=GREY_TEXT
                        ),
                        ft.Container(height=8),
                        nombre,
                        rut,
                        rol,
                        email,
                    ])
                )
            ]
        )
    )







