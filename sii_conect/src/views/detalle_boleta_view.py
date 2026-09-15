import flet as ft
from src.utils.constants import NAVY, RED_TEXT, GREEN, GREY_TEXT, CARD_RADIUS
from src.services.supabase_service import SupabaseService
from src.services.api_gateway import ApiGatewayClient, ApiGatewayError
from src.utils.helpers import mapear_estado_boleta, abrir_pdf_resultado, mensaje_error_api

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
            alignment=ft.alignment.Alignment(0, 0),
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
    codigo_sii = (boleta.get("respuesta_sii") or {}).get("codigo") or str(folio)
    fecha = boleta.get("fecha_emision", "---")
    contraparte = boleta.get("contraparte_nombre", "---")
    monto_bruto = boleta.get("monto_bruto", 0)
    monto_liquido = boleta.get("monto_liquido", monto_bruto)
    estado_actual = ft.Text(str(boleta.get("estado", "pendiente")), size=13, weight=ft.FontWeight.BOLD, color=NAVY)

    # El RUT del emisor debe ser el que quedo registrado en ESTA boleta al emitirla
    # (columna 'rut_emisor'), no el RUT del perfil de quien esta logueado ahora mismo.
    # Esto es clave para el rol 'contador', que puede ver y anular boletas de
    # distintos emisores: si se usara el RUT del usuario logueado, se intentaria
    # anular con el RUT equivocado ante el SII.
    rut_emisor = boleta.get("rut_emisor") or usuario_info.get("rut")
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

    # Si la boleta es antigua (emitida antes de guardar rut_emisor) no habra RUT
    # registrado; se permite ingresarlo manualmente como respaldo.
    rut_emisor_manual = ft.TextField(
        label="RUT Emisor de esta boleta (no quedo registrado)",
        hint_text="12.345.678-9",
        visible=not bool(rut_emisor),
    )
    info_rut_emisor = ft.Text(
        f"RUT Emisor de esta boleta: {rut_emisor}" if rut_emisor else "",
        size=11, color=GREY_TEXT, visible=bool(rut_emisor),
    )

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
                height=42,
                style=ft.ButtonStyle(bgcolor=RED_TEXT, color="white"),
            ),
        ]
    )
    toggle_anular_btn = ft.OutlinedButton("Anular Boleta", height=42)
    btn_descargar_pdf = ft.OutlinedButton("Descargar PDF", height=42)
    btn_enviar_email = ft.OutlinedButton("Enviar por Email", height=42)

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

    def rut_emisor_actual():
        return rut_emisor or (rut_emisor_manual.value.strip() if rut_emisor_manual.value else None)

    def validar_clave():
        if not rut_emisor_actual():
            msg_status.value = "Falta el RUT del emisor de esta boleta (ingresalo arriba)."
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

    async def accion_descargar_pdf(e):
        if not validar_clave():
            return
        try:
            resultado = api_client.descargar_pdf(rut=rut_emisor_actual(), clave=clave_actual(), codigo=codigo_sii)
            msg_status.value = await abrir_pdf_resultado(page, resultado)
            msg_status.color = GREEN
            db_service.registrar_evento_historial(
                boleta_id=boleta.get("id"), usuario_id=usuario_info.get("id"),
                tipo_evento="consulta_sii", detalle="Descarga de PDF"
            )
        except ApiGatewayError as api_err:
            msg_status.value = mensaje_error_api(api_err)
            msg_status.color = RED_TEXT
        page.update()

    btn_descargar_pdf.on_click = accion_descargar_pdf

    def accion_enviar_email(e):
        if not validar_clave():
            return
        try:
            resultado = api_client.enviar_email(
                rut=rut_emisor_actual(),
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
            msg_status.value = mensaje_error_api(api_err)
            msg_status.color = RED_TEXT
        page.update()

    btn_enviar_email.on_click = accion_enviar_email

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
                rut=rut_emisor_actual(),
                clave=clave_actual(),
                emisor=rut_emisor_actual(),
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
            msg_status.value = mensaje_error_api(api_err)
            msg_status.color = RED_TEXT
        page.update()

    def cerrar_confirmacion_anulacion():
        dialog_confirmar_anulacion.open = False
        page.update()

    def abrir_confirmacion_anulacion(e):
        if not validar_clave():
            return
        # page.open()/page.close() no existen en esta version de Flet (usa ft.app,
        # no ft.run); se usa la forma clasica: overlay + open=True/False + update().
        if dialog_confirmar_anulacion not in page.overlay:
            page.overlay.append(dialog_confirmar_anulacion)
        dialog_confirmar_anulacion.open = True
        page.update()

    def confirmar_anulacion(e):
        cerrar_confirmacion_anulacion()
        accion_anular(e)

    dialog_confirmar_anulacion = ft.AlertDialog(
        modal=True,
        title=ft.Text("Confirmar anulación"),
        content=ft.Text(
            f"¿Estás seguro de anular la boleta folio {folio}? "
            "Esta accion es irreversible: una vez anulada ante el SII, no se puede deshacer."
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda e: cerrar_confirmacion_anulacion()),
            ft.ElevatedButton(
                "Confirmar",
                on_click=confirmar_anulacion,
                style=ft.ButtonStyle(bgcolor=RED_TEXT, color="white"),
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    opciones_anulacion.controls[-1].on_click = abrir_confirmacion_anulacion

    # Responsive: en pantallas angostas (celular) las tarjetas y los botones usan
    # el ancho disponible completo en vez de valores fijos, para que nada se corte.
    ANCHO_MAXIMO_TARJETA = 450

    def ancho_tarjeta():
        if page.width and page.width < ANCHO_MAXIMO_TARJETA + 40:
            return page.width - 40
        return ANCHO_MAXIMO_TARJETA

    def ancho_contenido():
        # Ancho util dentro de la tarjeta, descontando el padding=20 de cada lado.
        return ancho_tarjeta() - 40

    toggle_anular_btn.width = ancho_contenido()
    btn_descargar_pdf.width = ancho_contenido()
    btn_enviar_email.width = ancho_contenido()
    opciones_anulacion.controls[-1].width = ancho_contenido()

    tarjeta_resumen = ft.Container(
        bgcolor="white", border_radius=CARD_RADIUS, padding=20, width=ancho_tarjeta(),
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
    )

    tarjeta_acciones = ft.Container(
        bgcolor="white", border_radius=CARD_RADIUS, padding=20, width=ancho_tarjeta(),
        content=ft.Column([
            ft.Text("Acciones sobre el documento", size=13, weight=ft.FontWeight.BOLD, color=NAVY),
            ft.Container(height=8),
            info_rut_emisor,
            rut_emisor_manual,
            clave_sii,
            ft.Row([info_clave, cambiar_clave_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Container(height=6),
            btn_descargar_pdf,
            email_destino,
            btn_enviar_email,
            ft.Container(height=10),
            toggle_anular_btn,
            opciones_anulacion,
            msg_status,
        ])
    )

    def on_resize(e):
        nuevo_ancho = ancho_tarjeta()
        tarjeta_resumen.width = nuevo_ancho
        tarjeta_acciones.width = nuevo_ancho
        nuevo_ancho_contenido = ancho_contenido()
        toggle_anular_btn.width = nuevo_ancho_contenido
        btn_descargar_pdf.width = nuevo_ancho_contenido
        btn_enviar_email.width = nuevo_ancho_contenido
        opciones_anulacion.controls[-1].width = nuevo_ancho_contenido
        page.update()

    page.on_resized = on_resize

    return ft.Container(
        padding=20,
        expand=True,
        content=ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                ft.Row([
                    ft.TextButton("Volver", on_click=lambda e: navigate_to("Mis BHE")),
                    ft.Text(f"Boleta N {folio}", size=20, weight=ft.FontWeight.BOLD, color=NAVY)
                ]),
                tarjeta_resumen,
                ft.Container(height=14),
                tarjeta_acciones,
            ]
        )
    )








