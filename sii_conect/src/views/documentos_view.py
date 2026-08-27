import flet as ft
from src.utils.constants import NAVY, BLUE, GREEN, RED_TEXT, RED_BG, GREY_TEXT, CARD_RADIUS
from src.utils.helpers import formato_clp

def build_documentos(page: ft.Page, state: dict, navigate_to):
    bhe_list = [
        {"folio": "1204", "fecha": "28 Jul 2026", "receptor": "Tech Solutions SPA", "rut": "76.123.456-7", "bruto": 125000, "liquido": 105938, "estado": "Vigente"},
        {"folio": "1203", "fecha": "15 Jul 2026", "receptor": "Importadora Santa Cruz SpA", "rut": "77.987.654-3", "bruto": 850000, "liquido": 720375, "estado": "Vigente"},
        {"folio": "1202", "fecha": "02 Jul 2026", "receptor": "Constructora Andina Ltda", "rut": "78.456.123-9", "bruto": 450000, "liquido": 381375, "estado": "Anulada"},
        {"folio": "1201", "fecha": "20 Jun 2026", "receptor": "Servicios Norte Ltda", "rut": "76.555.444-1", "bruto": 320000, "liquido": 271200, "estado": "Vigente"},
    ]

    list_container = ft.Column(spacing=10)

    def show_toast(msg):
        page.snack_bar = ft.SnackBar(content=ft.Text(msg))
        page.snack_bar.open = True
        page.update()

    def build_bhe_card(bhe):
        es_vigente = bhe["estado"] == "Vigente"
        badge_bg = "#E6F4EA" if es_vigente else RED_BG
        badge_color = GREEN if es_vigente else RED_TEXT

        return ft.Container(
            bgcolor="white",
            border_radius=CARD_RADIUS,
            padding=16,
            width=380,
            shadow=ft.BoxShadow(blur_radius=10, color="#12000000", offset=ft.Offset(0, 2)),
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text(f"BHE N° {bhe['folio']}", weight=ft.FontWeight.BOLD, color=NAVY, size=14),
                            ft.Container(
                                bgcolor=badge_bg,
                                border_radius=10,
                                padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                                content=ft.Text(bhe["estado"], size=10, color=badge_color, weight=ft.FontWeight.BOLD),
                            ),
                        ],
                    ),
                    ft.Text(bhe["receptor"], size=13, weight=ft.FontWeight.W_500, color=NAVY),
                    ft.Text(f"RUT: {bhe['rut']} · {bhe['fecha']}", size=11, color=GREY_TEXT),
                    ft.Divider(height=1, color="#EEF0F3"),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Column(
                                spacing=0,
                                controls=[
                                    ft.Text("Monto Líquido", size=10, color=GREY_TEXT),
                                    ft.Text(formato_clp(bhe["liquido"]), size=14, weight=ft.FontWeight.BOLD, color=NAVY),
                                ],
                            ),
                            ft.OutlinedButton(
                                content=ft.Text("Ver PDF", size=12),
                                style=ft.ButtonStyle(color=BLUE, shape=ft.RoundedRectangleBorder(radius=8)),
                                on_click=lambda e, f=bhe["folio"]: show_toast(f"Descargando PDF Folio {f}..."),
                            ),
                        ],
                    ),
                ],
            ),
        )

    buscador = ft.TextField(
        hint_text="Buscar por cliente, RUT o folio...",
        prefix_icon=ft.Icons.SEARCH,
        color=NAVY,
        border_radius=10,
        border_color="#D8DCE3",
        bgcolor="white",
        height=46,
    )

    filtro_estado = ft.Dropdown(
        value="Todos",
        width=140,
        height=40,
        options=[
            ft.dropdown.Option("Todos"),
            ft.dropdown.Option("Vigente"),
            ft.dropdown.Option("Anulada"),
        ],
    )

    def render_items():
        texto = (buscador.value or "").lower()
        estado = filtro_estado.value or "Todos"

        list_container.controls.clear()
        for bhe in bhe_list:
            coincide_texto = texto in bhe["receptor"].lower() or texto in bhe["rut"].lower() or texto in bhe["folio"]
            coincide_estado = estado == "Todos" or bhe["estado"] == estado

            if coincide_texto and coincide_estado:
                list_container.controls.append(build_bhe_card(bhe))

        if not list_container.controls:
            list_container.controls.append(
                ft.Container(
                    padding=20,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Text("No se encontraron boletas", color=GREY_TEXT, size=13),
                )
            )

    def on_filter_change(e):
        render_items()
        page.update()

    # Asignación explícita de eventos para evitar incompatibilidades de versión
    buscador.on_change = on_filter_change
    filtro_estado.on_change = on_filter_change

    render_items()

    header = ft.Container(
        bgcolor="white",
        padding=ft.Padding.symmetric(horizontal=16, vertical=14),
        content=ft.Row(
            spacing=4,
            controls=[
                ft.IconButton(icon=ft.Icons.ARROW_BACK, icon_color=NAVY, on_click=lambda e: navigate_to("Inicio")),
                ft.Text("Mis Boletas de Honorarios", size=15, weight=ft.FontWeight.BOLD, color=NAVY),
            ],
        ),
    )

    controles_busqueda = ft.Container(
        width=380,
        content=ft.Column(
            spacing=10,
            controls=[
                buscador,
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text("Filtrar por estado:", size=12, color=GREY_TEXT),
                        filtro_estado,
                    ],
                ),
            ],
        ),
    )

    body = ft.Container(
        padding=ft.Padding.symmetric(horizontal=20, vertical=16),
        content=ft.Column(
            spacing=14,
            horizontal_alignment=ft.CrossAxisAlignment.START,
            controls=[
                controles_busqueda,
                ft.Container(height=4),
                list_container,
                ft.Container(height=20),
            ],
        ),
    )

    return ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO, expand=True, controls=[header, body])