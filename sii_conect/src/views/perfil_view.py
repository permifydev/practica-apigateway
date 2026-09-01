import flet as ft
from src.utils.constants import NAVY, RED_TEXT, GREEN, GREY_TEXT, CARD_RADIUS
from src.services.supabase_service import SupabaseService

db_service = SupabaseService()


def build_perfil(page: ft.Page, state: dict, navigate_to):
    usuario_info = state.get("usuario", {})

    nombre = ft.TextField(label="Nombre completo", value=usuario_info.get("nombre", ""), disabled=True)
    rut = ft.TextField(label="RUT", value=usuario_info.get("rut", ""), disabled=True)
    rol = ft.TextField(label="Rol", value=str(usuario_info.get("rol", "")).capitalize(), disabled=True)
    email = ft.TextField(label="Correo de contacto", value=usuario_info.get("email", ""))
    msg_status = ft.Text("", size=12)

    def guardar(e):
        if not email.value or "@" not in email.value:
            msg_status.value = "Ingresa un correo valido."
            msg_status.color = RED_TEXT
            page.update()
            return

        resultado = db_service.actualizar_perfil(usuario_info.get("id"), email.value.strip())
        if resultado is not None:
            usuario_info["email"] = email.value.strip()
            state["usuario"] = usuario_info
            msg_status.value = "Perfil actualizado correctamente."
            msg_status.color = GREEN
        else:
            msg_status.value = "No se pudo actualizar el perfil."
            msg_status.color = RED_TEXT
        page.update()

    return ft.Container(
        padding=20,
        content=ft.Column(
            controls=[
                ft.Row([
                    ft.TextButton("Volver", on_click=lambda e: navigate_to("Inicio")),
                    ft.Text("Mi Perfil", size=20, weight=ft.FontWeight.BOLD, color=NAVY)
                ]),
                ft.Container(
                    bgcolor="white", border_radius=CARD_RADIUS, padding=20, width=450,
                    content=ft.Column([
                        ft.Text(
                            "RUT y rol los administra tu jefe/administrador; solo puedes actualizar tu correo.",
                            size=11, color=GREY_TEXT
                        ),
                        ft.Container(height=8),
                        nombre,
                        rut,
                        rol,
                        email,
                        msg_status,
                        ft.ElevatedButton("Guardar Cambios", on_click=guardar, width=400, height=45),
                    ])
                )
            ]
        )
    )