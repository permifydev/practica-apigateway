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
                    on_select_change=abrir_detalle(b),
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

        # Filtra la tabla de abajo para que muestre solo las boletas de este RUT,
        # que son las que le corresponden a la persona que esta reconciliando.
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
            folios_sii = {str(b.get("folio")): b for b in boletas_sii}
            folios_locales = {str(b.get("folio_sii")): b for b in boletas_del_emisor}

            faltantes_local = [f for f in folios_sii if f not in folios_locales]
            solo_local = [f for f in folios_locales if f not in folios_sii and folios_locales[f].get("estado") != "anulada"]

            if not faltantes_local and not solo_local:
                msg_reconciliar.value = f"Todo coincide con el SII ({len(folios_sii)} boleta(s) este periodo)."
                msg_reconciliar.color = GREEN
            else:
                partes = []
                if faltantes_local:
                    partes.append(f"{len(faltantes_local)} folio(s) en el SII que no estan en tu registro local: {', '.join(faltantes_local)}")
                if solo_local:
                    partes.append(f"{len(solo_local)} folio(s) locales que el SII no reporta este periodo: {', '.join(solo_local)}")
                msg_reconciliar.value = " | ".join(partes)
                msg_reconciliar.color = RED_TEXT
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
