import flet as ft
from src.utils.constants import NAVY, RED_TEXT, GREEN, GREY_TEXT, CARD_RADIUS
from src.services.supabase_service import SupabaseService
from src.services.api_gateway import ApiGatewayClient, ApiGatewayError
from src.utils.helpers import mapear_estado_boleta

db_service = SupabaseService()
api_client = ApiGatewayClient()

CAUSAS_ANULACION = {
    "1": "No se efectuo el pago de los servicios por parte del receptor",
    "2": "No se efectuo la prestacion de servicios",
    "3": "Error en la digitacion",
}


def build_detalle_boleta(page: ft.Page, state: dict, navigate_to):
    usuario_info = state.get("usuario", {})
    boleta = state.get("boleta_seleccionada")

    if not boleta:
        return ft.Container(
            padding=40,
            alignment=ft.Alignment.CENTER,
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text("No hay boleta seleccionada", size=18, weight=ft.FontWeight.BOLD, color=NAVY),
                    ft.Container(height=10),
                    ft.ElevatedButton("Volver a Mis BHE", on_click=lambda e: navigate_to("Mis BHE"))
                ]
            )
        )

    folio = boleta.get("folio_sii", "---")
    codigo_sii = boleta.get("codigo_sii") or str(folio)
    fecha = boleta.get("fecha_emision", "---")
    contraparte = boleta.get("contraparte_nombre", "---")
    monto_bruto = boleta.get("monto_bruto", 0)
    monto_liquido = boleta.get("monto_liquido", monto_bruto)
    estado_actual = ft.Text(str(boleta.get("estado", "pendiente")), size=13, weight=ft.FontWeight.BOLD, color=NAVY)

    rut_emisor = usuario_info.get("rut")
    clave_ya_guardada = bool(state.get("clave_sii_temp"))

    clave_sii = ft.TextField(
        label="Clave SII (tuya, no se guarda en la base de datos)",
        password=True, can_reveal_password=True,
        visible=not clave_ya_guardada,
    )
    info_clave = ft.Row(
        visible=clave_ya_guardada,
        controls=[
            ft.Icon(ft.Icons.CHECK_CIRCLE, color=GREEN, size=16),
            ft.Text("Clave SII verificada para esta sesion.", size=12, color=GREEN),
        ]
    )
    cambiar_clave_btn = ft.TextButton("Cambiar clave", visible=clave_ya_guardada)

    email_destino = ft.TextField(label="Enviar a otro correo (opcional)", hint_text="cliente@ejemplo.com")

    causa_anulacion = ft.RadioGroup(
        value="3",
        content=ft.Column(
            spacing=2,
            controls=[ft.Radio(value=k, label=v) for k, v in CAUSAS_ANULACION.items()],
        ),
    )
    opciones_anulacion = ft.Column(
        visible=False,
        controls=[
            ft.Container(height=10),
            ft.Text("Motivo de anulacion", size=13, weight=ft.FontWeight.BOLD, color=RED_TEXT),
            causa_anulacion,
            ft.ElevatedButton(
                "Confirmar Anulacion",
                width=400, height=42,
                style=ft.ButtonStyle(bgcolor=RED_TEXT, color="white"),
            ),
        ]
    )
    toggle_anular_btn = ft.OutlinedButton("Anular Boleta", width=400, height=42)

    msg_status = ft.Text("", size=12)

    def on_cambiar_clave(e):
        state["clave_sii_temp"] = None
        clave_sii.value = ""
        clave_sii.visible = True
        info_clave.visible = False
        cambiar_clave_btn.visible = False
        page.update()

    cambiar_clave_btn.on_click = on_cambiar_clave

    def clave_actual():
        return state.get("clave_sii_temp") or (clave_sii.value.strip() if clave_sii.value else None)

    def validar_clave():
        if not rut_emisor:
            msg_status.value = "Tu perfil no tiene RUT registrado."
            msg_status.color = RED_TEXT
            page.update()
            return False
        if not clave_actual():
            msg_status.value = "Ingresa tu Clave SII para continuar."
            msg_status.color = RED_TEXT
            page.update()
            return False
        if not state.get("clave_sii_temp") and clave_sii.value:
            state["clave_sii_temp"] = clave_sii.value.strip()
            clave_sii.visible = False
            info_clave.visible = True
            cambiar_clave_btn.visible = True
        return True

    def accion_descargar_pdf(e):
        if not validar_clave():
            return
        try:
            resultado = api_client.descargar_pdf(rut=rut_emisor, clave=clave_actual(), codigo=codigo_sii)
            msg_status.value = f"PDF disponible: {resultado.get('pdf_url', 'sin url')}"
            msg_status.color = GREEN
            db_service.registrar_evento_historial(
                boleta_id=boleta.get("id"), usuario_id=usuario_info.get("id"),
                tipo_evento="consulta_sii", detalle="Descarga de PDF"
            )
        except ApiGatewayError as api_err:
            msg_status.value = f"Error al obtener PDF: {api_err}"
            msg_status.color = RED_TEXT
        page.update()

    def accion_enviar_email(e):
        if not validar_clave():
            return
        try:
            resultado = api_client.enviar_email(
                rut=rut_emisor,
                clave=clave_actual(),
                codigo=codigo_sii,
                email_destino=email_destino.value.strip() or None,
            )
            msg_status.value = resultado.get("mensaje", "Correo enviado.")
            msg_status.color = GREEN
            db_service.registrar_evento_historial(
                boleta_id=boleta.get("id"), usuario_id=usuario_info.get("id"),
                tipo_evento="consulta_sii", detalle="Envio por email"
            )
        except ApiGatewayError as api_err:
            msg_status.value = f"Error al enviar email: {api_err}"
            msg_status.color = RED_TEXT
        page.update()

    def toggle_anulacion(e):
        opciones_anulacion.visible = not opciones_anulacion.visible
        toggle_anular_btn.text = "Cancelar Anulacion" if opciones_anulacion.visible else "Anular Boleta"
        page.update()

    toggle_anular_btn.on_click = toggle_anulacion

    def accion_anular(e):
        if not validar_clave():
            return
        try:
            resultado = api_client.anular_boleta(
                rut=rut_emisor,
                clave=clave_actual(),
                emisor=rut_emisor,
                folio=str(folio),
                causa=int(causa_anulacion.value),
            )

            nuevo_estado = mapear_estado_boleta(resultado.get("estado"))
            db_service.actualizar_estado_boleta(boleta_id=boleta.get("id"), nuevo_estado=nuevo_estado)
            db_service.registrar_evento_historial(
                boleta_id=boleta.get("id"), usuario_id=usuario_info.get("id"),
                tipo_evento="anulacion", detalle=CAUSAS_ANULACION.get(causa_anulacion.value, "Sin motivo especificado")
            )

            estado_actual.value = nuevo_estado
            msg_status.value = resultado.get("mensaje", "Boleta anulada.")
            msg_status.color = GREEN
            opciones_anulacion.visible = False
            toggle_anular_btn.text = "Anular Boleta"
        except ApiGatewayError as api_err:
            msg_status.value = f"Error al anular: {api_err}"
            msg_status.color = RED_TEXT
        page.update()

    opciones_anulacion.controls[-1].on_click = accion_anular

    return ft.Container(
        padding=20,
        content=ft.Column(
            controls=[
                ft.Row([
                    ft.TextButton("Volver", on_click=lambda e: navigate_to("Mis BHE")),
                    ft.Text(f"Boleta N {folio}", size=20, weight=ft.FontWeight.BOLD, color=NAVY)
                ]),
                ft.Container(
                    bgcolor="white", border_radius=CARD_RADIUS, padding=20, width=450,
                    content=ft.Column([
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Text("Estado", size=12, color=GREY_TEXT),
                                estado_actual,
                            ]
                        ),
                        ft.Divider(height=1, color="#EEF0F3"),
                        ft.Text(f"Receptor: {contraparte}", size=13, color=NAVY),
                        ft.Text(f"Fecha emision: {fecha}", size=12, color=GREY_TEXT),
                        ft.Container(height=6),
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Column([
                                    ft.Text("Monto Bruto", size=11, color=GREY_TEXT),
                                    ft.Text(f"${monto_bruto:,.0f}".replace(",", "."), size=16, weight=ft.FontWeight.BOLD, color=NAVY),
                                ]),
                                ft.Column([
                                    ft.Text("Monto Liquido", size=11, color=GREY_TEXT),
                                    ft.Text(f"${monto_liquido:,.0f}".replace(",", "."), size=16, weight=ft.FontWeight.BOLD, color=NAVY),
                                ]),
                            ]
                        ),
                    ])
                ),
                ft.Container(height=14),
                ft.Container(
                    bgcolor="white", border_radius=CARD_RADIUS, padding=20, width=450,
                    content=ft.Column([
                        ft.Text("Acciones sobre el documento", size=13, weight=ft.FontWeight.BOLD, color=NAVY),
                        ft.Container(height=8),
                        clave_sii,
                        ft.Row([info_clave, cambiar_clave_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Container(height=6),
                        ft.OutlinedButton("Descargar PDF", on_click=accion_descargar_pdf, width=400, height=42),
                        email_destino,
                        ft.OutlinedButton("Enviar por Email", on_click=accion_enviar_email, width=400, height=42),
                        ft.Container(height=10),
                        toggle_anular_btn,
                        opciones_anulacion,
                        msg_status,
                    ])
                )
            ]
        )
    )