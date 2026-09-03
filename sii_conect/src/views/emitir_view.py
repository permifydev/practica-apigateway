from datetime import datetime
import flet as ft
from src.utils.constants import NAVY, RED_TEXT, GREEN, CARD_RADIUS, GREY_TEXT, tasa_retencion_vigente
from src.services.supabase_service import SupabaseService
from src.services.api_gateway import ApiGatewayClient, ApiGatewayError
from src.utils.helpers import mapear_estado_boleta, mensaje_error_api

db_service = SupabaseService()
api_client = ApiGatewayClient()


def construir_payload_boleta(rut_receptor, nombre_receptor, descripcion_servicio, monto_val, modo_retencion, rut_emisor):
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

    clave_sii = ft.TextField(label="Clave SII (tuya, no se guarda)", password=True, can_reveal_password=True)
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

        rut_emisor = usuario_info.get("rut")
        if not rut_emisor:
            msg_status.value = "Tu perfil no tiene un RUT registrado. Contacta al administrador."
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
            msg_status.value = mensaje_error_api(api_err)
            msg_status.color = RED_TEXT
            page.update()
            return
        except Exception as err:
            msg_status.value = f"Error inesperado al emitir: {err}"
            msg_status.color = RED_TEXT
            page.update()
            return

        certificado = db_service.obtener_certificado_activo(usuario_info.get("id"))

        try:
            receptor = db_service.obtener_o_crear_receptor(
                rut=rut_receptor.value.strip(),
                nombre=nombre_receptor.value.strip() or "Receptor Sin Nombre"
            )

            receptor_id = receptor.get("id") if isinstance(receptor, dict) else receptor

            modo = int(modo_retencion.value)
            tasa_vigente = tasa_retencion_vigente()
            retenido = round(monto_val * tasa_vigente) if modo != 0 else 0

            boleta_payload = {
                "usuario_id": usuario_info.get("id"),
                "certificado_id": certificado.get("id") if certificado else None,
                "receptor_id": receptor_id,
                "folio_sii": str(resultado_api.get("folio", "")),
                "codigo_sii": str(resultado_api.get("codigo", "")),
                "estado": mapear_estado_boleta(resultado_api.get("estado")),
                "descripcion": descripcion_servicio.value.strip() or "Servicios profesionales",
                "monto_bruto": monto_val,
                "tasa_retencion": tasa_vigente if modo != 0 else 0,
                "monto_retenido": retenido,
                "monto_liquido": monto_val - retenido,
                "modo_retencion": modo,
                "fecha_emision": resultado_api.get("fecha_emision") or None,
            }

            resultado_db = db_service.guardar_boleta(
                boleta_payload,
                contraparte_nombre=nombre_receptor.value.strip() or "Receptor Sin Nombre",
            )

            if resultado_db is not None:
                navigate_to("Mis BHE")
            else:
                msg_status.value = "La boleta se emitio en el SII pero fallo el registro local. Anota el folio: " + str(resultado_api.get("folio"))
                msg_status.color = RED_TEXT
                page.update()

        except Exception as err:
            msg_status.value = f"La boleta se emitio (folio {resultado_api.get('folio')}) pero hubo un error al guardar localmente: {err}"
            msg_status.color = RED_TEXT
            page.update()

    return ft.Container(
        padding=20,
        content=ft.Column(
            controls=[
                ft.Row([
                    ft.TextButton("Volver", on_click=lambda e: navigate_to("Inicio")),
                    ft.Text("Emitir Boleta de Honorarios", size=20, weight=ft.FontWeight.BOLD, color=NAVY)
                ]),
                ft.Container(
                    bgcolor="white", border_radius=CARD_RADIUS, padding=20, width=450,
                    content=ft.Column([
                        clave_sii,
                        ft.Divider(height=1, color="#EEF0F3"),
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