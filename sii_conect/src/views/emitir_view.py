import flet as ft
from src.utils.constants import NAVY, RED_TEXT, CARD_RADIUS, GREY_TEXT
from src.services.supabase_service import SupabaseService

db_service = SupabaseService()

def build_emitir_bhe(page: ft.Page, state: dict, navigate_to):
    usuario_info = state.get("usuario", {})
    rol = str(usuario_info.get("rol", "emisor")).lower()

    # BLOQUEO DE SEGURIDAD: Solo el rol 'emisor' puede emitir
    if rol != "emisor":
        return ft.Container(
            padding=40,
            alignment=ft.Alignment.CENTER,
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                controls=[
                    ft.Icon(ft.Icons.LOCK, size=50, color=RED_TEXT),
                    ft.Text("Acceso Denegado", size=22, weight=ft.FontWeight.BOLD, color=NAVY),
                    ft.Text("Tu rol actual no tiene atribución legal para emitir boletas.", color=GREY_TEXT),
                    ft.Container(height=15),
                    ft.ElevatedButton("Volver al Inicio", on_click=lambda e: navigate_to("Inicio"))
                ]
            )
        )

    # Campos del formulario (Corregido: min_lines en lugar de rows)
    rut_receptor = ft.TextField(label="RUT Receptor", hint_text="76.111.222-3")
    nombre_receptor = ft.TextField(label="Nombre / Razón Social")
    descripcion_servicio = ft.TextField(label="Descripción del Servicio", multiline=True, min_lines=2)
    monto_bruto = ft.TextField(label="Monto Bruto ($)", keyboard_type=ft.KeyboardType.NUMBER)
    msg_status = ft.Text("", size=12)

    def procesar_emision(e):
        if not rut_receptor.value or not monto_bruto.value:
            msg_status.value = "Completa el RUT y el Monto Bruto."
            msg_status.color = RED_TEXT
            page.update()
            return

        try:
            monto_val = float(monto_bruto.value.replace(".", "").replace("$", "").strip())
        except ValueError:
            msg_status.value = "Ingresa un monto numérico válido."
            msg_status.color = RED_TEXT
            page.update()
            return

        try:
            receptor = db_service.obtener_o_crear_receptor(
                rut=rut_receptor.value.strip(),
                nombre=nombre_receptor.value.strip() or "Receptor Sin Nombre"
            )

            receptor_id = receptor.get("id") if isinstance(receptor, dict) else receptor

            retencion = round(monto_val * 0.145)
            boleta_payload = {
                "usuario_id": usuario_info.get("id", "1"),
                "receptor_id": receptor_id,
                "descripcion": descripcion_servicio.value or "Servicios profesionales",
                "monto_bruto": monto_val,
                "monto_retencion": retencion,
                "monto_liquido": monto_val - retencion,
                "monto_total": monto_val,
                "estado": "Vigente"
            }

            resultado = db_service.guardar_boleta(boleta_payload)

            if resultado is not None:
                navigate_to("Mis BHE")
            else:
                msg_status.value = "Error al guardar en la base de datos."
                msg_status.color = RED_TEXT
                page.update()

        except Exception as err:
            msg_status.value = f"Error en proceso: {err}"
            msg_status.color = RED_TEXT
            page.update()

    return ft.Container(
        padding=20,
        content=ft.Column(
            controls=[
                ft.Row([
                    ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda e: navigate_to("Inicio")),
                    ft.Text("Emitir Boleta de Honorarios", size=20, weight=ft.FontWeight.BOLD, color=NAVY)
                ]),
                ft.Container(
                    bgcolor="white", border_radius=CARD_RADIUS, padding=20, width=450,
                    content=ft.Column([
                        rut_receptor,
                        nombre_receptor,
                        descripcion_servicio,
                        monto_bruto,
                        msg_status,
                        ft.ElevatedButton("Emitir Documento", on_click=procesar_emision, width=400, height=45)
                    ])
                )
            ]
        )
    )

build_emitir = build_emitir_bhe