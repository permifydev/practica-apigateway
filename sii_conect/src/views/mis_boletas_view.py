from datetime import date
import flet as ft
from src.utils.constants import NAVY, BLUE, GREEN, RED_TEXT, GREY_TEXT, CARD_RADIUS
from src.services.supabase_service import SupabaseService
from src.services.api_gateway import ApiGatewayClient, ApiGatewayError
from src.utils.helpers import mensaje_error_api

db_service = SupabaseService()
api_client = ApiGatewayClient()


def normalizar_rut(rut: str) -> str:
    """Quita puntos/espacios y pasa a mayuscula para poder comparar RUTs escritos con
    o sin formato (ej. '12.345.678-9' vs '12345678-9')."""
    if not rut:
        return ""
    return rut.replace(".", "").replace(" ", "").upper()


def build_mis_boletas(page: ft.Page, state: dict, navigate_to):
    usuario_info = state.get("usuario", {})
    rol = str(usuario_info.get("rol", "emisor")).lower()
    usuario_id = usuario_info.get("id")
    rut_usuario = usuario_info.get("rut")

    boletas = db_service.obtener_boletas_por_rol(
        rol=rol,
        usuario_id=usuario_id,
        rut=rut_usuario
    )

    def abrir_detalle(b):
        def handler(e):
            state["boleta_seleccionada"] = b
            navigate_to("Detalle Boleta")
        return handler

    def construir_filas(lista_boletas):
        filas = []
        for b in lista_boletas:
            monto = f"${b.get('monto_bruto', 0):,.0f}".replace(",", ".")
            filas.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(f"#{b.get('folio_sii', '---')}")),
                        ft.DataCell(ft.Text(str(b.get("fecha_emision", "---")))),
                        ft.DataCell(ft.Text(b.get("rut_emisor") or "---")),
                        ft.DataCell(ft.Text(b.get("contraparte_nombre", "---"))),
                        ft.DataCell(ft.Text(monto)),
                        ft.DataCell(ft.Text(str(b.get("estado", "pendiente")))),
                    ],
                    on_select_changed=abrir_detalle(b),
                )
            )
        return filas if filas else [
            ft.DataRow(cells=[ft.DataCell(ft.Text("Sin registros para este RUT"))] * 6)
        ]

    tabla = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("N Boleta")),
            ft.DataColumn(ft.Text("Fecha")),
            ft.DataColumn(ft.Text("RUT Emisor")),
            ft.DataColumn(ft.Text("Emisor / Receptor")),
            ft.DataColumn(ft.Text("Monto Bruto")),
            ft.DataColumn(ft.Text("Estado")),
        ],
        rows=construir_filas(boletas),
    )

    # --- Reconciliar con el SII (mes actual) ---
    # El RUT ya no se escribe a mano: siempre es el del usuario logueado (tabla
    # 'perfiles'). Cada cuenta de prueba debe tener su propio RUT asociado; si
    # se necesita reconciliar con otro RUT, se inicia sesion con esa cuenta.
    rut_reconciliar = ft.TextField(
        label="RUT Emisor", hint_text="12.345.678-9",
        value=rut_usuario or "", width=200,
        disabled=True,
    )
    clave_reconciliar = ft.TextField(
        label="Clave SII para reconciliar", password=True, can_reveal_password=True,
        width=260,
    )
    msg_reconciliar = ft.Text("", size=12)

    def clave_actual():
        return clave_reconciliar.value.strip() if clave_reconciliar.value else state.get("clave_sii_temp")

    def estado_real_desde_sii(b_sii: dict) -> str:
        """El SII marca una boleta anulada con fecha en el campo 'anulada' (vacio si
        sigue vigente). Usamos ese campo como fuente de verdad en vez de 'estado'
        (S/N), que no esta documentado con certeza."""
        return "anulada" if (b_sii.get("anulada") or "").strip() else "emitida"

    def accion_reconciliar(e):
        rut_objetivo = rut_reconciliar.value.strip() if rut_reconciliar.value else None
        if not rut_objetivo:
            msg_reconciliar.value = "Ingresa el RUT Emisor."
            msg_reconciliar.color = RED_TEXT
            page.update()
            return
        if not clave_actual():
            msg_reconciliar.value = "Ingresa tu Clave SII para reconciliar."
            msg_reconciliar.color = RED_TEXT
            page.update()
            return

        state["clave_sii_temp"] = clave_actual()

        rut_filtro = normalizar_rut(rut_objetivo)
        boletas_del_emisor = [b for b in boletas if normalizar_rut(b.get("rut_emisor") or "") == rut_filtro]
        tabla.rows = construir_filas(boletas_del_emisor)

        msg_reconciliar.value = "Consultando al SII..."
        msg_reconciliar.color = GREY_TEXT
        page.update()

        try:
            periodo_actual = date.today().strftime("%Y%m")
            respuesta = api_client.listar_emitidas(
                rut=rut_objetivo, clave=clave_actual(), emisor=rut_objetivo, periodo=periodo_actual
            )
            boletas_sii = respuesta.get("boletas", [])
            folios_sii = {str(b.get("folio") or b.get("numero")): b for b in boletas_sii}
            folios_locales = {str(b.get("folio_sii")): b for b in boletas_del_emisor}

            creadas, actualizadas, con_error = 0, 0, 0

            for folio_str, b_sii in folios_sii.items():
                estado_sii = estado_real_desde_sii(b_sii)

                if folio_str in folios_locales:
                    # Ya existe local: solo sincronizamos el estado si cambio
                    # (ej. se anulo directo en el portal del SII).
                    boleta_local = folios_locales[folio_str]
                    if boleta_local.get("estado") != estado_sii:
                        resultado_update = db_service.actualizar_estado_boleta(
                            boleta_id=boleta_local.get("id"), nuevo_estado=estado_sii
                        )
                        if resultado_update:
                            boleta_local["estado"] = estado_sii
                            actualizadas += 1
                        else:
                            con_error += 1
                    continue

                # No existe local: la creamos con los datos reales del SII.
                rut_receptor = f"{b_sii.get('rut', '')}-{str(b_sii.get('dv', '')).lower()}"
                nombre_receptor = b_sii.get("nombre") or "Receptor Sin Nombre"

                receptor = db_service.obtener_o_crear_receptor(
                    rut=rut_receptor, nombre=nombre_receptor, usuario_id=usuario_id,
                )
                receptor_id = receptor.get("id") if isinstance(receptor, dict) else receptor
                if not receptor_id:
                    con_error += 1
                    continue

                monto_bruto = b_sii.get("total_honorarios") or b_sii.get("monto_bruto") or 0
                monto_retenido = b_sii.get("retencion_receptor") or 0
                monto_liquido = b_sii.get("total_liquido") or (monto_bruto - monto_retenido)

                boleta_payload = {
                    "usuario_id": usuario_id,
                    "receptor_id": receptor_id,
                    "folio_sii": folio_str,
                    "estado": estado_sii,
                    "descripcion": "Importada automaticamente desde reconciliacion con el SII",
                    "monto_bruto": monto_bruto,
                    "tasa_retencion": (monto_retenido / monto_bruto) if monto_bruto else 0,
                    "monto_retenido": monto_retenido,
                    "monto_liquido": monto_liquido,
                    "modo_retencion": 1 if monto_retenido else 0,
                    "fecha_emision": b_sii.get("fecha_emision") or b_sii.get("fecha") or date.today().isoformat(),
                    "rut_emisor": rut_objetivo,
                    "respuesta_sii": {
                        "folio": b_sii.get("folio") or b_sii.get("numero"),
                        "codigo": b_sii.get("codigo"),
                        "estado": b_sii.get("estado"),
                    },
                }

                guardada = db_service.guardar_boleta(boleta_payload, contraparte_nombre=nombre_receptor)
                if guardada:
                    boletas.append(guardada)
                    creadas += 1
                else:
                    con_error += 1

            # Refresca la tabla con el estado final (incluye lo recien creado/actualizado).
            boletas_del_emisor = [b for b in boletas if normalizar_rut(b.get("rut_emisor") or "") == rut_filtro]
            tabla.rows = construir_filas(boletas_del_emisor)

            if creadas == 0 and actualizadas == 0 and con_error == 0:
                msg_reconciliar.value = f"Todo coincide con el SII ({len(folios_sii)} boleta(s) este periodo)."
                msg_reconciliar.color = GREEN
            else:
                partes = []
                if creadas:
                    partes.append(f"{creadas} boleta(s) importada(s) desde el SII")
                if actualizadas:
                    partes.append(f"{actualizadas} estado(s) actualizado(s)")
                if con_error:
                    partes.append(f"{con_error} con error al guardar (revisa los logs)")
                msg_reconciliar.value = " | ".join(partes) + "."
                msg_reconciliar.color = GREEN if not con_error else RED_TEXT
        except ApiGatewayError as api_err:
            msg_reconciliar.value = mensaje_error_api(api_err)
            msg_reconciliar.color = RED_TEXT
        page.update()

    panel_reconciliacion = ft.Container(
        visible=rol in ("emisor", "contador"),
        bgcolor="white", border_radius=CARD_RADIUS, padding=14,
        content=ft.Column([
            ft.Text("Reconciliar con el SII (mes actual)", size=13, weight=ft.FontWeight.BOLD, color=NAVY),
            ft.Text(
                "Compara tu registro local contra el listado oficial de boletas emitidas, "
                "y filtra la tabla para mostrar solo las boletas de este RUT.",
                size=11, color=GREY_TEXT,
            ),
            ft.Row([rut_reconciliar, clave_reconciliar, ft.ElevatedButton("Reconciliar", on_click=accion_reconciliar, height=42)], wrap=True),
            msg_reconciliar,
        ])
    )

    return ft.Container(
        padding=20,
        expand=True,
        content=ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                ft.Row(
                    controls=[
                        ft.TextButton("Volver", on_click=lambda e: navigate_to("Inicio")),
                        ft.Text(f"Historial de Boletas ({rol.capitalize()})", size=20, weight=ft.FontWeight.BOLD, color=NAVY)
                    ]
                ),
                ft.Text(f"Mostrando documentos bajo la regla del rol: {rol}", size=12, color=GREY_TEXT),
                ft.Text("Toca una fila para ver el detalle.", size=11, color=BLUE),
                ft.Container(height=10),
                panel_reconciliacion,
                ft.Container(height=10),
                ft.Container(
                    bgcolor="white", border_radius=CARD_RADIUS, padding=10,
                    content=ft.Row([tabla], scroll=ft.ScrollMode.AUTO)
                )
            ]
        )
    )