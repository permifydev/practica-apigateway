import logging
from datetime import datetime
import flet as ft
from src.utils.constants import NAVY, RED_TEXT, GREEN, CARD_RADIUS, GREY_TEXT, tasa_retencion_vigente
from src.services.supabase_service import SupabaseService
from src.services.api_gateway import ApiGatewayClient, ApiGatewayError
from src.utils.helpers import mapear_estado_boleta, mensaje_error_api, validar_rut

logger = logging.getLogger(__name__)

db_service = SupabaseService()
api_client = ApiGatewayClient()


def construir_payload_boleta(rut_receptor, nombre_receptor, direccion_receptor, comuna_receptor,
                             descripcion_servicio, monto_val, modo_retencion, rut_emisor):
    return {
        "Encabezado": {
            "IdDoc": {
                "FchEmis": datetime.now().strftime("%Y-%m-%d"),
                "TipoRetencion": modo_retencion,
            },
            "Emisor": {
                "RUTEmisor": rut_emisor,
            },
            "Receptor": {
                "RUTRecep": rut_receptor,
                "RznSocRecep": nombre_receptor,
                "DirRecep": direccion_receptor,
                "CmnaRecep": comuna_receptor,
            },
        },
        "Detalle": [
            {
                "NmbItem": descripcion_servicio or "Servicios profesionales",
                "MontoItem": monto_val,
            }
        ],
    }


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
                    ft.Text("Acceso Denegado", size=22, weight=ft.FontWeight.BOLD, color=NAVY),
                    ft.Text("Tu rol actual no tiene atribucion legal para emitir boletas.", color=GREY_TEXT),
                    ft.Container(height=15),
                    ft.ElevatedButton("Volver al Inicio", on_click=lambda e: navigate_to("Inicio"))
                ]
            )
        )

    # El RUT Emisor no se escribe a mano: siempre es el del usuario logueado
    rut_emisor_display = ft.TextField(
        label="RUT Emisor",
        value=usuario_info.get("rut", ""),
        hint_text="Ingrese RUT",
        border_color="#DDE1E6",
        disabled=True,
    )
    clave_sii = ft.TextField(label="Clave SII (tuya, no se guarda)", password=True, can_reveal_password=True)
    rut_receptor = ft.TextField(label="RUT Receptor", hint_text="76.111.222-3")
    nombre_receptor = ft.TextField(label="Nombre / Razon Social")
    direccion_receptor = ft.TextField(label="Direccion Receptor", hint_text="Av. Principal 123")
    comuna_receptor = ft.TextField(label="Comuna Receptor", hint_text="Santiago")
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
        if not clave_sii.value:
            msg_status.value = "Ingresa tu Clave SII para autenticar la emision."
            msg_status.color = RED_TEXT
            page.update()
            return

        if not rut_receptor.value or not monto_bruto.value:
            msg_status.value = "Completa el RUT y el Monto Bruto."
            msg_status.color = RED_TEXT
            page.update()
            return

        if not direccion_receptor.value or not comuna_receptor.value:
            msg_status.value = "Completa la Direccion y la Comuna del receptor."
            msg_status.color = RED_TEXT
            page.update()
            return

        rut_emisor = rut_emisor_display.value.strip() if rut_emisor_display.value else ""
        if not rut_emisor:
            msg_status.value = "El perfil del usuario no posee un RUT registrado."
            msg_status.color = RED_TEXT
            page.update()
            return

        if not validar_rut(rut_emisor):
            msg_status.value = "El RUT Emisor no es válido (revisa el dígito verificador)."
            msg_status.color = RED_TEXT
            page.update()
            return

        if not validar_rut(rut_receptor.value.strip()):
            msg_status.value = "El RUT Receptor no es válido (revisa el dígito verificador)."
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

        msg_status.value = "Emitiendo boleta, espera un momento..."
        msg_status.color = GREY_TEXT
        page.update()

        try:
            payload = construir_payload_boleta(
                rut_receptor=rut_receptor.value.strip(),
                nombre_receptor=nombre_receptor.value.strip() or "Receptor Sin Nombre",
                direccion_receptor=direccion_receptor.value.strip(),
                comuna_receptor=comuna_receptor.value.strip(),
                descripcion_servicio=descripcion_servicio.value.strip(),
                monto_val=monto_val,
                modo_retencion=int(modo_retencion.value),
                rut_emisor=rut_emisor,
            )

            resultado_api = api_client.emitir_boleta(
                rut=rut_emisor,
                clave=clave_sii.value.strip(),
                boleta_payload=payload,
            )
        except ApiGatewayError as api_err:
            logger.error(f"[Emitir View] Error de API Gateway ({api_err.status_code}): {api_err.payload}")
            msg_status.value = mensaje_error_api(api_err)
            msg_status.color = RED_TEXT
            page.update()
            return

        except Exception as err:
            logger.error(f"[Emitir View] Excepcion inesperada al emitir: {err}")
            msg_status.value = f"Error inesperado al emitir: {err}"
            msg_status.color = RED_TEXT
            page.update()
            return

        # Registro en la BD tras emision exitosa en SII
        certificado = db_service.obtener_certificado_activo(usuario_info.get("id"))

        try:
            receptor = db_service.obtener_o_crear_receptor(
                rut=rut_receptor.value.strip(),
                nombre=nombre_receptor.value.strip() or "Receptor Sin Nombre",
                usuario_id=usuario_info.get("id"),
            )

            receptor_id = receptor.get("id") if isinstance(receptor, dict) else receptor

            modo = int(modo_retencion.value)
            tasa_vigente = tasa_retencion_vigente()
            retenido = round(monto_val * tasa_vigente) if modo != 0 else 0
            fecha_emis = resultado_api.get("fecha_emision") or datetime.now().strftime("%Y-%m-%d")

            boleta_payload = {
                "usuario_id": usuario_info.get("id"),
                "certificado_id": certificado.get("id") if certificado else None,
                "receptor_id": receptor_id,
                "folio_sii": str(resultado_api.get("folio", "")),
                "estado": mapear_estado_boleta(resultado_api.get("estado")),
                "descripcion": descripcion_servicio.value.strip() or "Servicios profesionales",
                "monto_bruto": monto_val,
                "tasa_retencion": tasa_vigente if modo != 0 else 0,
                "monto_retenido": retenido,
                "monto_liquido": monto_val - retenido,
                "modo_retencion": modo,
                "fecha_emision": fecha_emis,
                "rut_emisor": rut_emisor,
                "respuesta_sii": {
                    "folio": resultado_api.get("folio"),
                    "codigo": resultado_api.get("codigo"),
                    "estado": resultado_api.get("estado"),
                },
            }

            resultado_db = db_service.guardar_boleta(
                boleta_payload,
                contraparte_nombre=nombre_receptor.value.strip() or "Receptor Sin Nombre",
            )

            if resultado_db is not None:
                state["boleta_seleccionada"] = resultado_db
                navigate_to("Detalle Boleta")
            else:
                msg_status.value = "La boleta se emitio en el SII pero fallo el registro local. Anota el folio: " + str(resultado_api.get("folio"))
                msg_status.color = RED_TEXT
                page.update()

        except Exception as err:
            logger.error(f"[Emitir View] Error al guardar en base de datos: {err}")
            msg_status.value = f"La boleta se emitio (folio {resultado_api.get('folio')}) pero hubo un error al guardar localmente: {err}"
            msg_status.color = RED_TEXT
            page.update()

    def cerrar_confirmacion():
        dialog_confirmar.open = False
        page.update()

    def confirmar_emision(e):
        cerrar_confirmacion()
        procesar_emision(e)

    dialog_confirmar = ft.AlertDialog(
        modal=True,
        title=ft.Text("Confirmar emisión"),
        content=ft.Text("¿Quieres emitir esta boleta?"),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda e: cerrar_confirmacion()),
            ft.ElevatedButton("Confirmar", on_click=confirmar_emision),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    def abrir_confirmacion(e):
        # page.open()/page.close() no existen en esta version de Flet (usa ft.app,
        # no ft.run); se usa la forma clasica: overlay + open=True/False + update().
        if dialog_confirmar not in page.overlay:
            page.overlay.append(dialog_confirmar)
        dialog_confirmar.open = True
        page.update()

    ANCHO_MAXIMO_TARJETA = 450

    def ancho_tarjeta():
        if page.width and page.width < ANCHO_MAXIMO_TARJETA + 40:
            return page.width - 40
        return ANCHO_MAXIMO_TARJETA

    tarjeta = ft.Container(
        bgcolor="white",
        border_radius=CARD_RADIUS,
        padding=20,
        width=ancho_tarjeta(),
        content=ft.Column([
            ft.Text("Emisor", size=13, weight=ft.FontWeight.BOLD, color=NAVY),
            rut_emisor_display,
            clave_sii,
            ft.Divider(height=1, color="#EEF0F3"),
            ft.Text("Receptor", size=13, weight=ft.FontWeight.BOLD, color=NAVY),
            rut_receptor,
            nombre_receptor,
            direccion_receptor,
            comuna_receptor,
            ft.Divider(height=1, color="#EEF0F3"),
            descripcion_servicio,
            monto_bruto,
            ft.Text("Retencion", size=13, weight=ft.FontWeight.BOLD, color=NAVY),
            modo_retencion,
            msg_status,
            ft.Row(
                controls=[
                    ft.OutlinedButton(
                        "Cancelar",
                        on_click=lambda e: navigate_to("Inicio"),
                        expand=True,
                        height=45,
                        style=ft.ButtonStyle(
                            color=RED_TEXT,
                            side=ft.BorderSide(1, RED_TEXT),
                        ),
                    ),
                    ft.Container(width=10),
                    ft.ElevatedButton(
                        "Emitir Boleta",
                        on_click=abrir_confirmacion,
                        expand=True,
                        height=45,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
        ])
    )

    def on_resize(e):
        tarjeta.width = ancho_tarjeta()
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
                    ft.TextButton("Volver", on_click=lambda e: navigate_to("Inicio")),
                    ft.Text("Emitir Boleta de Honorarios", size=20, weight=ft.FontWeight.BOLD, color=NAVY)
                ]),
                tarjeta,
            ]
        )
    )

build_emitir = build_emitir_bhe