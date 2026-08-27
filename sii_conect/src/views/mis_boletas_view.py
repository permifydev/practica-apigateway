import flet as ft
from src.utils.constants import NAVY, BLUE, GREY_TEXT, CARD_RADIUS
from src.services.supabase_service import SupabaseService

db_service = SupabaseService()

def build_mis_boletas(page: ft.Page, state: dict, navigate_to):
    usuario_info = state.get("usuario", {})
    rol = str(usuario_info.get("rol", "emisor")).lower()
    usuario_id = usuario_info.get("id")
    rut_usuario = usuario_info.get("rut")

    # Carga de boletas filtradas según el tipo de usuario
    boletas = db_service.obtener_boletas_por_rol(
        rol=rol, 
        usuario_id=usuario_id, 
        rut=rut_usuario
    )

    rows = []
    for b in boletas:
        monto = f"${b.get('monto_total', 0):,}".replace(",", ".")
        rows.append(
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(f"#{b.get('numero', '---')}")),
                    ft.DataCell(ft.Text(b.get("fecha_emision", "---"))),
                    ft.DataCell(ft.Text(b.get("contraparte_nombre", "---"))),
                    ft.DataCell(ft.Text(monto)),
                    ft.DataCell(ft.Text(b.get("estado", "Vigente"))),
                ]
            )
        )

    tabla = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("N° Boleta")),
            ft.DataColumn(ft.Text("Fecha")),
            ft.DataColumn(ft.Text("Emisor / Receptor")),
            ft.DataColumn(ft.Text("Monto Total")),
            ft.DataColumn(ft.Text("Estado")),
        ],
        rows=rows if rows else [
            ft.DataRow(cells=[ft.DataCell(ft.Text("Sin registros para este perfil"))]*5)
        ]
    )

    return ft.Container(
        padding=20,
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda e: navigate_to("Inicio")),
                        ft.Text(f"Historial de Boletas ({rol.capitalize()})", size=20, weight=ft.FontWeight.BOLD, color=NAVY)
                    ]
                ),
                ft.Text(f"Mostrando documentos bajo la regla del rol: {rol}", size=12, color=GREY_TEXT),
                ft.Container(height=10),
                ft.Container(
                    bgcolor="white", border_radius=CARD_RADIUS, padding=10,
                    content=ft.Column([tabla], scroll=ft.ScrollMode.AUTO)
                )
            ]
        )
    )