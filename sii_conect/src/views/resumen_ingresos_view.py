import asyncio
from datetime import date
import flet as ft
from src.utils.constants import NAVY, RED_TEXT, GREEN, ORANGE, GREY_TEXT, CARD_RADIUS, tasa_retencion_vigente
from src.services.supabase_service import SupabaseService
from src.services.api_gateway import ApiGatewayClient, ApiGatewayError
from src.utils.helpers import formato_clp, mensaje_error_api, _abrir_url
from src.utils.acciones_boleta import preparar_pdf_recibida

db_service = SupabaseService()
api_client = ApiGatewayClient()

MESES_NOMBRE = [
    "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]

ESTADOS_BHE = {"N": "Vigente", "S": "Anulada", "V": "Anulacion pendiente", "R": "Observada", "U": "Observada por SII"}
ESTADO_BG = {"Vigente": "#E3F3EA", "Anulada": "#FDE7E7", "Anulacion pendiente": "#FCF0D8",
             "Observada": "#FDE7E7", "Observada por SII": "#FDE7E7"}
ESTADO_COLOR = {"Vigente": GREEN, "Anulada": RED_TEXT, "Anulacion pendiente": "#B5790E",
                "Observada": RED_TEXT, "Observada por SII": RED_TEXT}


def build_resumen_ingresos(page: ft.Page, state: dict, navigate_to):
    usuario_info = state.get("usuario", {})
    rol = str(usuario_info.get("rol", "")).lower()

    if rol != "receptor":
        return ft.Container(
            padding=40,
            alignment=ft.alignment.Alignment(0, 0),
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                controls=[
                    ft.Text("Acceso Denegado", size=22, weight=ft.FontWeight.BOLD, color=NAVY),
                    ft.Text("El resumen de ingresos es solo para el rol Receptor.", color=GREY_TEXT),
                    ft.Container(height=15),
                    ft.ElevatedButton("Volver al Inicio", on_click=lambda e: navigate_to("Inicio"))
                ]
            )
        )

    rut_receptor = usuario_info.get("rut")
    usuario_id = usuario_info.get("id")

    if not rut_receptor:
        return ft.Container(
            padding=40,
            alignment=ft.alignment.Alignment(0, 0),
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                controls=[
                    ft.Text("Falta tu RUT", size=22, weight=ft.FontWeight.BOLD, color=NAVY),
                    ft.Text(
                        "Tu perfil todavia no tiene un RUT registrado; sin eso no se puede "
                        "sincronizar con el SII. Pidele a tu administrador que te lo asigne.",
                        color=GREY_TEXT, text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Container(height=15),
                    ft.ElevatedButton("Volver al Inicio", on_click=lambda e: navigate_to("Inicio"))
                ]
            )
        )

    clave_sii = ft.TextField(
        label="Clave SII (tuya, no se guarda)",
        password=True, can_reveal_password=True,
        visible=not bool(state.get("clave_sii_temp")),
    )

    hoy = date.today()
    periodo_sel = {"anio": hoy.year, "mes": hoy.month}

    label_periodo = ft.Text(f"{MESES_NOMBRE[periodo_sel['mes']]} {periodo_sel['anio']}", size=14, weight=ft.FontWeight.BOLD, color=NAVY)
    msg_status = ft.Text("", size=12)

    texto_bruto = ft.Text("$0", size=18, weight=ft.FontWeight.BOLD, color=NAVY)
    texto_retenido = ft.Text("$0", size=18, weight=ft.FontWeight.BOLD, color=ORANGE)
    texto_liquido = ft.Text("$0", size=18, weight=ft.FontWeight.BOLD, color=GREEN)

    resumen_montos = ft.Container(
        visible=False,
        bgcolor="#F1F3F6", border_radius=10,
        padding=ft.padding.symmetric(vertical=10, horizontal=14),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Column([ft.Text("Bruto", size=11, color=GREY_TEXT), texto_bruto]),
                ft.Column([ft.Text("Retencion (estimada)", size=11, color=GREY_TEXT), texto_retenido]),
                ft.Column([ft.Text("Liquido", size=11, color=GREY_TEXT), texto_liquido]),
            ],
        ),
    )

    resultados = ft.Column(spacing=10)

    def clave_actual():
        return state.get("clave_sii_temp") or (clave_sii.value.strip() if clave_sii.value else None)

    def periodo_str():
        return f"{periodo_sel['anio']:04d}{periodo_sel['mes']:02d}"

    def fila_boleta(b):
        """Fila con el detalle de la boleta + acciones Ver PDF / Descargar, igual que
        en 'Mis BHE' (mismo helper preparar_pdf_recibida, mismo cache en Supabase
        Storage: pedir el PDF dos veces de la misma boleta no vuelve a gastar
        creditos). No se ofrece 'Enviar por email' aca: a diferencia de las boletas
        EMITIDAS, la API de apigateway.cl no tiene un endpoint de envio de correo
        para boletas RECIBIDAS (solo listar, descargar PDF y observar)."""
        estado_txt = ESTADOS_BHE.get(str(b.get("estado", "")).upper(), b.get("estado", "---"))
        msg_fila = ft.Text("", size=11)

        async def accion_pdf(modo):
            if not clave_actual():
                msg_fila.value = "Ingresa tu Clave SII arriba (en 'Sincronizar') para pedir el PDF."
                msg_fila.color = RED_TEXT
                page.update()
                return
            msg_fila.value = "Preparando PDF..."
            msg_fila.color = GREY_TEXT
            page.update()
            try:
                pdf = await asyncio.to_thread(
                    preparar_pdf_recibida, api_client, db_service, state, b,
                    rut_receptor, clave_actual(), usuario_id,
                )
            except ApiGatewayError as api_err:
                msg_fila.value = mensaje_error_api(api_err)
                msg_fila.color = RED_TEXT
                page.update()
                return

            if not pdf["ver"]:
                msg_fila.value = pdf["mensaje"]
                msg_fila.color = RED_TEXT
                page.update()
                return

            url = pdf["descarga"] if modo == "descargar" else pdf["ver"]
            try:
                await _abrir_url(page, url)
                msg_fila.value = pdf["mensaje"]
                msg_fila.color = GREEN
            except Exception:
                msg_fila.value = f"{pdf['mensaje']} Si no se abrio solo, copia este link: {url}"
                msg_fila.color = GREEN
            page.update()

        def handler(modo):
            async def h(e):
                await accion_pdf(modo)
            return h

        estilo_btn = ft.ButtonStyle(
            padding=ft.padding.symmetric(horizontal=6),
            text_style=ft.TextStyle(size=12, weight=ft.FontWeight.BOLD),
        )

        return ft.Container(
            padding=ft.padding.symmetric(vertical=10),
            border=ft.border.only(bottom=ft.BorderSide(1, "#EEF0F3")),
            content=ft.Column(
                spacing=4,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Column(
                                spacing=2,
                                horizontal_alignment=ft.CrossAxisAlignment.START,
                                controls=[
                                    ft.Text(f"Folio {b.get('folio', '---')}", size=13, weight=ft.FontWeight.BOLD, color=NAVY),
                                    ft.Text(f"Emisor: {b.get('emisor_nombre', b.get('emisor', '---'))}", size=12, color=GREY_TEXT),
                                    ft.Text(f"RUT emisor: {b.get('emisor_rut', '---')}", size=11, color=GREY_TEXT),
                                    ft.Text(f"{b.get('fecha', '---')} · {formato_clp(b.get('monto_bruto', 0))}", size=12, color=GREY_TEXT),
                                ],
                            ),
                            ft.Container(
                                bgcolor=ESTADO_BG.get(estado_txt, "#EEF0F3"),
                                border_radius=12,
                                padding=ft.padding.symmetric(horizontal=10, vertical=3),
                                content=ft.Text(estado_txt, size=11, color=ESTADO_COLOR.get(estado_txt, GREY_TEXT), weight=ft.FontWeight.BOLD),
                            ),
                        ],
                    ),
                    ft.Row(
                        spacing=0,
                        controls=[
                            ft.TextButton("VER PDF", on_click=handler("ver"), style=estilo_btn),
                            ft.TextButton("DESCARGAR", on_click=handler("descargar"), style=estilo_btn),
                        ],
                    ),
                    msg_fila,
                ],
            ),
        )

    def mostrar_boletas(boletas: list[dict]):
        """Pinta la pantalla (totales + lista) a partir de lo que sea que se le pase
        -- SIEMPRE datos que ya estan en memoria/Supabase, nunca dispara una llamada
        al SII por si sola."""
        resultados.controls.clear()

        vigentes = [b for b in boletas if str(b.get("estado", "")).upper() != "S"]
        total_bruto = sum(b.get("monto_bruto") or 0 for b in vigentes)
        tasa = tasa_retencion_vigente()
        total_retenido = round(total_bruto * tasa)
        total_liquido = total_bruto - total_retenido

        texto_bruto.value = formato_clp(total_bruto)
        texto_retenido.value = formato_clp(total_retenido)
        texto_liquido.value = formato_clp(total_liquido)
        resumen_montos.visible = True

        if not boletas:
            resultados.controls.append(ft.Text("No hay boletas guardadas para este mes todavia.", color=GREY_TEXT))
        else:
            for b in boletas:
                resultados.controls.append(fila_boleta(b))

    def cargar_desde_cache():
        """Lee lo que ya esta guardado en Supabase para el mes seleccionado. Gratis,
        no llama al SII. Esto es lo que se ve SIEMPRE que abres la pantalla o cambias
        de mes."""
        boletas = db_service.listar_boletas_recibidas_cache(usuario_id, periodo_str())
        if boletas:
            ultima = max((b.get("actualizado_en") or "" for b in boletas), default="")
            msg_status.value = f"Mostrando datos guardados (ultima sincronizacion: {ultima[:16].replace('T', ' ')})."
            msg_status.color = GREY_TEXT
        else:
            msg_status.value = "Todavia no has sincronizado este mes. Aprieta 'Sincronizar con el SII' para traer tus boletas."
            msg_status.color = GREY_TEXT
        mostrar_boletas(boletas)
        page.update()

    def refrescar_label_y_cache():
        label_periodo.value = f"{MESES_NOMBRE[periodo_sel['mes']]} {periodo_sel['anio']}"
        cargar_desde_cache()

    def mes_anterior(e):
        periodo_sel["mes"] -= 1
        if periodo_sel["mes"] < 1:
            periodo_sel["mes"] = 12
            periodo_sel["anio"] -= 1
        refrescar_label_y_cache()

    def mes_siguiente(e):
        periodo_sel["mes"] += 1
        if periodo_sel["mes"] > 12:
            periodo_sel["mes"] = 1
            periodo_sel["anio"] += 1
        refrescar_label_y_cache()

    def al_elegir_fecha(e):
        if date_picker.value:
            periodo_sel["anio"] = date_picker.value.year
            periodo_sel["mes"] = date_picker.value.month
            refrescar_label_y_cache()

    date_picker = ft.DatePicker(
        first_date=date(2020, 1, 1),
        last_date=hoy,
        value=hoy,
        on_change=al_elegir_fecha,
    )

    def abrir_calendario(e):
        if date_picker not in page.overlay:
            page.overlay.append(date_picker)
        date_picker.open = True
        page.update()

    selector_periodo = ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        controls=[
            ft.IconButton(icon=ft.Icons.CHEVRON_LEFT, on_click=mes_anterior),
            ft.Row(
                spacing=4,
                controls=[
                    label_periodo,
                    ft.IconButton(icon=ft.Icons.CALENDAR_MONTH, icon_size=18, tooltip="Elegir mes lejano", on_click=abrir_calendario),
                ],
            ),
            ft.IconButton(icon=ft.Icons.CHEVRON_RIGHT, on_click=mes_siguiente),
        ],
    )

    def sincronizar(e):
        """Unica funcion que realmente llama al SII (gasta creditos). Guarda el
        resultado en Supabase y despues vuelve a pintar la pantalla leyendo de ahi,
        para que el resto del flujo (cambiar de mes, volver a abrir la pantalla)
        nunca tenga que volver a llamar al SII por si solo."""
        if not clave_actual():
            msg_status.value = "Ingresa tu Clave SII para sincronizar."
            msg_status.color = RED_TEXT
            page.update()
            return

        if clave_sii.value:
            state["clave_sii_temp"] = clave_sii.value.strip()
            clave_sii.visible = False

        msg_status.value = "Sincronizando con el SII, espera un momento..."
        msg_status.color = GREY_TEXT
        page.update()

        try:
            respuesta = api_client.listar_recibidas(
                rut=rut_receptor, clave=clave_actual(), receptor=rut_receptor, periodo=periodo_str()
            )
            boletas = respuesta.get("boletas", [])
            db_service.guardar_boletas_recibidas_cache(usuario_id, periodo_str(), boletas)
            cargar_desde_cache()
            msg_status.value = f"Sincronizado. {len(boletas)} boleta(s) guardadas para este mes."
            msg_status.color = GREEN
        except ApiGatewayError as api_err:
            msg_status.value = mensaje_error_api(api_err)
            msg_status.color = RED_TEXT
        page.update()

    cargar_desde_cache()

    return ft.Container(
        padding=20,
        expand=True,
        content=ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                ft.Row([
                    ft.TextButton("Volver", on_click=lambda e: navigate_to("Inicio")),
                    ft.Text("Resumen de Ingresos", size=18, weight=ft.FontWeight.BOLD, color=NAVY)
                ]),
                ft.Container(
                    bgcolor="white", border_radius=CARD_RADIUS, padding=20, width=450,
                    content=ft.Column([
                        selector_periodo,
                        ft.Divider(height=1, color="#EEF0F3"),
                        resumen_montos,
                        msg_status,
                        ft.Container(height=6),
                        clave_sii,
                        ft.OutlinedButton(
                            "Sincronizar con el SII (consume creditos)",
                            on_click=sincronizar, width=410, height=42,
                        ),
                    ])
                ),
                ft.Container(height=14),
                resultados,
            ]
        )
    )