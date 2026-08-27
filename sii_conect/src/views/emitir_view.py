import flet as ft
from src.utils.constants import NAVY, RED_TEXT, CARD_RADIUS, GREY_TEXT, BLUE, TASA_RETENCION_REF
from src.services.supabase_service import SupabaseService

db_service = SupabaseService()

def build_emitir_bhe(page: ft.Page, state: dict, navigate_to):
    usuario_info = state.get("usuario", {})
    rol = str(usuario_info.get("rol", "emisor")).lower()

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
                    ft.Text("Tu rol actual no tiene atribucion legal para emitir boletas.", color=GREY_TEXT),
                    ft.Container(height=15),
                    ft.ElevatedButton("Volver al Inicio", on_click=lambda e: navigate_to("Inicio"))
                ]
            )
        )

    rut_receptor = ft.TextField(label="RUT Receptor", hint_text="76.111.222-3")
    nombre_receptor = ft.TextField(label="Nombre / Razon Social")
    descripcion_servicio = ft.TextField(label="Descripcion del Servicio", multiline=True, min_lines=2)
    monto_bruto = ft.TextField(label="Monto Bruto ($)", keyboard_type=ft.KeyboardType.NUMBER)

    modo_retencion = ft.RadioGroup(
        value="1",
        content=ft.Column(
            spacing=2,
            controls=[
                ft.Radio(value="0", label="Sin retencion (soc. profesionales 1a categoria)"),
                ft.Radio(value="1", label="Retiene el receptor"),
                ft.Radio(value="2", label="Retiene el emisor"),
            ],
        ),
    )
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
            msg_status.value = "Ingresa un monto numerico valido."
            msg_status.color = RED_TEXT
            page.update()
            return

        certificado = db_service.obtener_certificado_activo(usuario_info.get("id"))
        if not certificado:
            msg_status.value = "No tienes un certificado digital activo cargado. Sube uno en 'Certificados' antes de emitir."
            msg_status.color = RED_TEXT
            page.update()
            return

        try:
            receptor = db_service.obtener_o_crear_receptor(
                rut=rut_receptor.value.strip(),
                nombre=nombre_receptor.value.strip() or "Receptor Sin Nombre"
            )

            receptor_id = receptor.get("id") if isinstance(receptor, dict) else receptor

            modo = int(modo_retencion.value)
            retenido = round(monto_val * TASA_RETENCION_REF) if modo != 0 else 0

            boleta_payload = {
                "usuario_id": usuario_info.get("id"),
                "certificado_id": certificado.get("id"),
                "receptor_id": receptor_id,
                "monto_bruto": monto_val,
                "tasa_retencion": TASA_RETENCION_REF if modo != 0 else 0,
                "monto_retenido": retenido,
                "monto_liquido": monto_val - retenido,
                "modo_retencion": modo,
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
                        ft.Text("Retencion", size=13, weight=ft.FontWeight.BOLD, color=NAVY),
                        modo_retencion,
                        msg_status,
                        ft.ElevatedButton("Emitir Documento", on_click=procesar_emision, width=400, height=45)
                    ])
                )
            ]
        )
    )

build_emitir = build_emitir_bhe