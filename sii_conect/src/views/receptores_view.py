import flet as ft
from src.utils.constants import NAVY, RED_TEXT, GREEN, GREY_TEXT, CARD_RADIUS
from src.services.supabase_service import SupabaseService

db_service = SupabaseService()


def build_receptores(page: ft.Page, state: dict, navigate_to):
    usuario_info = state.get("usuario", {})
    rol = str(usuario_info.get("rol", "")).lower()

    if rol not in ("emisor", "contador"):
        return ft.Container(
            padding=40,
            alignment=ft.Alignment.CENTER,
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text("Acceso Denegado", size=22, weight=ft.FontWeight.BOLD, color=NAVY),
                    ft.Text("Solo Emisor y Contador administran receptores.", color=GREY_TEXT),
                    ft.Container(height=15),
                    ft.ElevatedButton("Volver al Inicio", on_click=lambda e: navigate_to("Inicio"))
                ]
            )
        )

    lista_container = ft.Column(spacing=8)
    msg_status = ft.Text("", size=12)

    rut_field = ft.TextField(label="RUT", hint_text="76.111.222-3", width=200)
    nombre_field = ft.TextField(label="Nombre / Razon Social", expand=True)
    email_field = ft.TextField(label="Correo (opcional)", expand=True)
    editando_id = {"value": None}

    def cargar_lista():
        lista_container.controls.clear()
        receptores = db_service.listar_receptores()
        if not receptores:
            lista_container.controls.append(ft.Text("Aun no hay receptores registrados.", color=GREY_TEXT))
        for r in receptores:
            lista_container.controls.append(
                ft.Container(
                    bgcolor="white", border_radius=10, padding=12,
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Column([
                                ft.Text(r.get("nombre", "---"), weight=ft.FontWeight.BOLD, color=NAVY, size=13),
                                ft.Text(f"{r.get('rut', '---')} · {r.get('email') or 'sin correo'}", size=11, color=GREY_TEXT),
                            ]),
                            ft.IconButton(icon=ft.Icons.EDIT_OUTLINED, icon_color=NAVY, tooltip="Editar",
                                          on_click=cargar_para_editar(r)),
                        ]
                    )
                )
            )

    def cargar_para_editar(r):
        def handler(e):
            editando_id["value"] = r.get("id")
            rut_field.value = r.get("rut", "")
            rut_field.disabled = True
            nombre_field.value = r.get("nombre", "")
            email_field.value = r.get("email", "")
            msg_status.value = f"Editando a {r.get('nombre')}. Guarda para aplicar los cambios."
            msg_status.color = GREY_TEXT
            page.update()
        return handler

    def limpiar_formulario():
        editando_id["value"] = None
        rut_field.value = ""
        rut_field.disabled = False
        nombre_field.value = ""
        email_field.value = ""

    def guardar(e):
        if not rut_field.value or not nombre_field.value:
            msg_status.value = "Completa al menos RUT y nombre."
            msg_status.color = RED_TEXT
            page.update()
            return

        if editando_id["value"]:
            resultado = db_service.actualizar_receptor(
                editando_id["value"], nombre_field.value.strip(), email_field.value.strip()
            )
        else:
            resultado = db_service.crear_receptor(
                rut_field.value.strip(), nombre_field.value.strip(), email_field.value.strip()
            )

        if resultado is not None:
            msg_status.value = "Receptor guardado correctamente."
            msg_status.color = GREEN
            limpiar_formulario()
            cargar_lista()
        else:
            msg_status.value = "No se pudo guardar el receptor."
            msg_status.color = RED_TEXT
        page.update()

    def cancelar_edicion(e):
        limpiar_formulario()
        msg_status.value = ""
        page.update()

    cargar_lista()

    return ft.Container(
        padding=20,
        content=ft.Column(
            scroll=ft.ScrollMode.AUTO,
            controls=[
                ft.Row([
                    ft.TextButton("Volver", on_click=lambda e: navigate_to("Inicio")),
                    ft.Text("Receptores", size=20, weight=ft.FontWeight.BOLD, color=NAVY)
                ]),
                ft.Container(
                    bgcolor="white", border_radius=CARD_RADIUS, padding=20, width=450,
                    content=ft.Column([
                        ft.Text("Agregar / Editar receptor", size=13, weight=ft.FontWeight.BOLD, color=NAVY),
                        ft.Row([rut_field]),
                        nombre_field,
                        email_field,
                        msg_status,
                        ft.Row([
                            ft.ElevatedButton("Guardar", on_click=guardar, width=190, height=42),
                            ft.OutlinedButton("Cancelar", on_click=cancelar_edicion, width=190, height=42),
                        ])
                    ])
                ),
                ft.Container(height=14),
                ft.Text("Receptores registrados", size=13, weight=ft.FontWeight.BOLD, color=NAVY),
                lista_container,
            ]
        )
    )