import flet as ft
from src.utils.constants import NAVY, RED_TEXT, GREEN, GREY_TEXT, CARD_RADIUS
from src.services.api_gateway import ApiGatewayClient, ApiGatewayError
from src.utils.helpers import mensaje_error_api

api_client = ApiGatewayClient()


def build_verificar_autenticidad(page: ft.Page, state: dict, navigate_to):
    usuario_info = state.get("usuario", {})
    rut_usuario = usuario_info.get("rut")

    modo = ft.RadioGroup(
        value="codigo",
        content=ft.Row([
            ft.Radio(value="codigo", label="Por codigo de barras"),
            ft.Radio(value="datos", label="Por datos del documento"),
        ]),
    )

    clave_sii = ft.TextField(
        label="Clave SII (tuya, no se guarda)",
        password=True, can_reveal_password=True,
        visible=not bool(state.get("clave_sii_temp")),
    )

    codigo_barras = ft.TextField(label="Codigo de barras", visible=True)
    emisor = ft.TextField(label="RUT Emisor", hint_text="76.192.083-9", visible=False)
    receptor = ft.TextField(label="RUT Receptor", hint_text="76.111.222-3", visible=False)
    periodo = ft.TextField(label="Fecha del documento (YYYY-MM-DD)", visible=False)
    folio = ft.TextField(label="Folio", visible=False)

    msg_status = ft.Text("", size=12)

    def on_modo_change(e):
        es_codigo = modo.value == "codigo"
        codigo_barras.visible = es_codigo
        emisor.visible = not es_codigo
        receptor.visible = not es_codigo
        periodo.visible = not es_codigo
        folio.visible = not es_codigo
        page.update()

    modo.on_change = on_modo_change

    def clave_actual():
        return state.get("clave_sii_temp") or (clave_sii.value.strip() if clave_sii.value else None)

    def verificar(e):
        if not clave_actual():
            msg_status.value = "Ingresa tu Clave SII para continuar."
            msg_status.color = RED_TEXT
            page.update()
            return

        if modo.value == "codigo" and not codigo_barras.value:
            msg_status.value = "Ingresa el codigo de barras del documento."
            msg_status.color = RED_TEXT
            page.update()
            return
        if modo.value == "datos" and not all([emisor.value, receptor.value, periodo.value, folio.value]):
            msg_status.value = "Completa emisor, receptor, fecha y folio."
            msg_status.color = RED_TEXT
            page.update()
            return

        if clave_sii.value:
            state["clave_sii_temp"] = clave_sii.value.strip()
            clave_sii.visible = False

        msg_status.value = "Verificando en el SII..."
        msg_status.color = GREY_TEXT
        page.update()

        try:
            if modo.value == "codigo":
                resultado = api_client.verificar_autenticidad(
                    rut=rut_usuario, clave=clave_actual(), codigo_barras=codigo_barras.value.strip()
                )
            else:
                resultado = api_client.verificar_autenticidad(
                    rut=rut_usuario, clave=clave_actual(),
                    emisor=emisor.value.strip(), receptor=receptor.value.strip(),
                    periodo=periodo.value.strip(), folio=folio.value.strip(),
                )
            if resultado.get("valido", True):
                msg_status.value = resultado.get("mensaje", "Documento verificado correctamente.")
                msg_status.color = GREEN
            else:
                msg_status.value = "El documento no pudo ser verificado con esos datos."
                msg_status.color = RED_TEXT
        except ApiGatewayError as api_err:
            msg_status.value = mensaje_error_api(api_err)
            msg_status.color = RED_TEXT
        page.update()

    return ft.Container(
        padding=20,
        content=ft.Column(
            controls=[
                ft.Row([
                    ft.TextButton("Volver", on_click=lambda e: navigate_to("Inicio")),
                    ft.Text("Verificar Autenticidad BHE", size=18, weight=ft.FontWeight.BOLD, color=NAVY)
                ]),
                ft.Text(
                    "Comprueba si una boleta de honorarios que te muestren es real y coincide "
                    "con los datos que tiene el SII.", size=12, color=GREY_TEXT
                ),
                ft.Container(height=10),
                ft.Container(
                    bgcolor="white", border_radius=CARD_RADIUS, padding=20, width=450,
                    content=ft.Column([
                        clave_sii,
                        modo,
                        codigo_barras,
                        emisor,
                        receptor,
                        periodo,
                        folio,
                        msg_status,
                        ft.ElevatedButton("Verificar", on_click=verificar, width=400, height=45),
                    ])
                )
            ]
        )
    )