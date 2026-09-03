import flet as ft
from datetime import date
from src.utils.constants import NAVY, RED_TEXT, GREEN, GREY_TEXT, CARD_RADIUS
from src.services.api_gateway import ApiGatewayClient, ApiGatewayError
from src.utils.helpers import formato_clp, abrir_pdf_resultado, mensaje_error_api

api_client = ApiGatewayClient()

CAUSAS_OBSERVACION = {
    "1": "No se reconoce la relacion contractual o comercial con el emisor",
    "2": "No se reconoce al emisor de la BHE",
}

ESTADOS_BHE = {"N": "Vigente", "S": "Anulada", "V": "Anulacion pendiente", "R": "Observada", "U": "Observada por SII"}


def build_boletas_recibidas(page: ft.Page, state: dict, navigate_to):
    usuario_info = state.get("usuario", {})
    rol = str(usuario_info.get("rol", "")).lower()

    if rol != "cliente":
        return ft.Container(
            padding=40,
            alignment=ft.Alignment.CENTER,
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text("Acceso Denegado", size=22, weight=ft.FontWeight.BOLD, color=NAVY),
                    ft.Text("Esta consulta en vivo al SII es solo para el rol Receptor/Cliente.", color=GREY_TEXT),
                    ft.Container(height=15),
                    ft.ElevatedButton("Volver al Inicio", on_click=lambda e: navigate_to("Inicio"))
                ]
            )
        )

    rut_receptor = usuario_info.get("rut")
    clave_sii = ft.TextField(
        label="Clave SII (tuya, no se guarda)",
        password=True, can_reveal_password=True,
        visible=not bool(state.get("clave_sii_temp")),
    )
    periodo = ft.TextField(label="Periodo (YYYYMM)", value=date.today().strftime("%Y%m"), width=180)
    msg_status = ft.Text("", size=12)
    resultados = ft.Column(spacing=10)

    def clave_actual():
        return state.get("clave_sii_temp") or (clave_sii.value.strip() if clave_sii.value else None)

    def fila_boleta(b):
        estado_txt = ESTADOS_BHE.get(str(b.get("estado", "")).upper(), b.get("estado", "---"))
        causa_obs = ft.RadioGroup(
            value="1",
            content=ft.Row([ft.Radio(value=k, label=v) for k, v in CAUSAS_OBSERVACION.items()]),
        )

        async def accion_pdf(e):
            if not clave_actual():
                msg_status.value = "Ingresa tu Clave SII para continuar."
                msg_status.color = RED_TEXT
                page.update()
                return
            try:
                resultado = api_client.descargar_pdf_recibida(
                    rut=rut_receptor, clave=clave_actual(), codigo=str(b.get("codigo", b.get("folio")))
                )
                msg_status.value = await abrir_pdf_resultado(page, resultado)
                msg_status.color = GREEN
            except ApiGatewayError as api_err:
                msg_status.value = mensaje_error_api(api_err)
                msg_status.color = RED_TEXT
            page.update()

        def accion_observar(e):
            if not clave_actual():
                msg_status.value = "Ingresa tu Clave SII para continuar."
                msg_status.color = RED_TEXT
                page.update()
                return
            try:
                resultado = api_client.observar_recibida(
                    rut=rut_receptor, clave=clave_actual(),
                    emisor=str(b.get("emisor")), folio=str(b.get("folio")),
                    causa=int(causa_obs.value),
                )
                msg_status.value = resultado.get("mensaje", "Boleta observada.")
                msg_status.color = GREEN
            except ApiGatewayError as api_err:
                msg_status.value = mensaje_error_api(api_err)
                msg_status.color = RED_TEXT
            page.update()

        return ft.Container(
            bgcolor="white", border_radius=CARD_RADIUS, padding=14, width=420,
            content=ft.Column([
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text(f"Folio {b.get('folio')}", weight=ft.FontWeight.BOLD, color=NAVY),
                        ft.Text(estado_txt, size=12, color=GREY_TEXT),
                    ],
                ),
                ft.Text(f"Emisor: {b.get('razon_social_emisor', b.get('emisor'))}", size=12, color=NAVY),
                ft.Text(f"Fecha: {b.get('fecha', '---')} · {formato_clp(b.get('monto_bruto', 0))}", size=12, color=GREY_TEXT),
                ft.Row([
                    ft.OutlinedButton("Ver PDF", on_click=accion_pdf),
                ]),
                ft.Text("Observar boleta:", size=11, color=RED_TEXT),
                causa_obs,
                ft.OutlinedButton("Observar", on_click=accion_observar,
                                  style=ft.ButtonStyle(color=RED_TEXT)),
            ])
        )

    def consultar(e):
        if not clave_actual():
            msg_status.value = "Ingresa tu Clave SII para continuar."
            msg_status.color = RED_TEXT
            page.update()
            return
        if not periodo.value:
            msg_status.value = "Indica el periodo a consultar."
            msg_status.color = RED_TEXT
            page.update()
            return

        if clave_sii.value:
            state["clave_sii_temp"] = clave_sii.value.strip()
            clave_sii.visible = False

        msg_status.value = "Consultando al SII, espera un momento..."
        msg_status.color = GREY_TEXT
        resultados.controls.clear()
        page.update()

        try:
            respuesta = api_client.listar_recibidas(
                rut=rut_receptor, clave=clave_actual(), receptor=rut_receptor, periodo=periodo.value.strip()
            )
            boletas = respuesta.get("boletas", [])
            if not boletas:
                resultados.controls.append(ft.Text("No hay boletas recibidas en ese periodo.", color=GREY_TEXT))
            else:
                for b in boletas:
                    resultados.controls.append(fila_boleta(b))
            msg_status.value = f"{len(boletas)} boleta(s) encontrada(s)."
            msg_status.color = GREEN
        except ApiGatewayError as api_err:
            msg_status.value = mensaje_error_api(api_err)
            msg_status.color = RED_TEXT
        page.update()

    return ft.Container(
        padding=20,
        content=ft.Column(
            scroll=ft.ScrollMode.AUTO,
            controls=[
                ft.Row([
                    ft.TextButton("Volver", on_click=lambda e: navigate_to("Inicio")),
                    ft.Text("Boletas Recibidas (consulta al SII)", size=18, weight=ft.FontWeight.BOLD, color=NAVY)
                ]),
                ft.Container(
                    bgcolor="white", border_radius=CARD_RADIUS, padding=20, width=450,
                    content=ft.Column([
                        clave_sii,
                        periodo,
                        ft.ElevatedButton("Consultar", on_click=consultar, width=200, height=42),
                        msg_status,
                    ])
                ),
                ft.Container(height=14),
                resultados,
            ]
        )
    )