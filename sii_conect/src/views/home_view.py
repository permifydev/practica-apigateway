import flet as ft
from src.utils.constants import NAVY, BLUE, GREEN, ORANGE, PURPLE, GREY_TEXT, CARD_RADIUS, MENU_ACTIVE_BG, MENU_HOVER_BG, RED_TEXT
from src.components.ui import stat_card, quick_action, pending_row

def build_home(page: ft.Page, state: dict, navigate_to):
    # Obtener datos del usuario logueado
    usuario_info = state.get("usuario", {})
    nombre_usuario = usuario_info.get("nombre") or state.get("nombre", "Usuario")
    rol_usuario = str(usuario_info.get("rol", "emisor")).lower()

    drawer_open = {"value": False}

    def toggle_drawer(e=None):
        drawer_open["value"] = not drawer_open["value"]
        drawer.left = 0 if drawer_open["value"] else -300
        backdrop.visible = drawer_open["value"]
        backdrop.opacity = 0.4 if drawer_open["value"] else 0
        page.update()

    def close_drawer(e=None):
        drawer_open["value"] = False
        drawer.left = -300
        backdrop.opacity = 0
        backdrop.visible = False
        page.update()

    def go_to_screen(nombre):
        def handler(e):
            close_drawer()
            if nombre in ["Inicio", "Emitir BHE", "Mis BHE"]:
                navigate_to(nombre)
            else:
                page.show_snack_bar(ft.SnackBar(content=ft.Text(f"'{nombre}' en desarrollo")))
        return handler

    def menu_section_label(text):
        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=20, vertical=8),
            content=ft.Text(text, size=11, color="#8792AC", weight=ft.FontWeight.BOLD),
        )

    def menu_item(icon, label, active=False, badge=None):
        row_controls = [
            ft.Icon(icon, color="white" if active else "#B7C0D8", size=19),
            ft.Text(
                label, color="white" if active else "#D3D9EA", size=14,
                weight=ft.FontWeight.BOLD if active else ft.FontWeight.W_500, expand=True
            ),
        ]
        if badge:
            row_controls.append(
                ft.Container(
                    bgcolor=BLUE, border_radius=8,
                    padding=ft.Padding.symmetric(horizontal=7, vertical=2),
                    content=ft.Text(badge, size=9, color="white", weight=ft.FontWeight.BOLD),
                )
            )
        
        item = ft.Container(
            on_click=go_to_screen(label),
            padding=ft.Padding.symmetric(horizontal=16, vertical=11),
            margin=ft.Margin.symmetric(horizontal=8),
            border_radius=10,
            bgcolor=MENU_ACTIVE_BG if active else None,
            animate=ft.Animation(120, ft.AnimationCurve.EASE_OUT),
            content=ft.Row(spacing=12, controls=row_controls),
        )

        if not active:
            def on_hover(e, item=item):
                is_hovering = e.data is True or str(e.data).lower() == "true"
                item.bgcolor = MENU_HOVER_BG if is_hovering else None
                item.update()
            item.on_hover = on_hover

        return item

    # Construcción de ítems de menú según ROL
    menu_controls = [
        ft.Container(height=8),
        menu_section_label("PRINCIPAL"),
        menu_item(ft.Icons.HOME_OUTLINED, "Inicio", active=True),
    ]

    if rol_usuario == "emisor":
        menu_controls.extend([
            menu_item(ft.Icons.ADD_CIRCLE_OUTLINE, "Emitir BHE"),
            menu_item(ft.Icons.DESCRIPTION_OUTLINED, "Mis BHE"),
            menu_section_label("HERRAMIENTAS"),
            menu_item(ft.Icons.SHIELD_OUTLINED, "Certificados"),
            menu_item(ft.Icons.PEOPLE_OUTLINE, "Receptores"),
        ])
    elif rol_usuario == "contador":
        menu_controls.extend([
            menu_item(ft.Icons.DESCRIPTION_OUTLINED, "Mis BHE"),
            menu_section_label("HERRAMIENTAS"),
            menu_item(ft.Icons.PEOPLE_OUTLINE, "Receptores"),
            menu_item(ft.Icons.BAR_CHART, "Auditoría"),
        ])
    elif rol_usuario == "cliente":
        menu_controls.extend([
            menu_item(ft.Icons.INBOX_OUTLINED, "Mis BHE"),
        ])

    menu_controls.extend([
        ft.Container(height=10),
        menu_section_label("CUENTA"),
        menu_item(ft.Icons.PERSON_OUTLINE, "Perfil"),
    ])

    drawer = ft.Container(
        width=260, left=-300, top=0, bottom=0, bgcolor=NAVY,
        animate_position=ft.Animation(250, ft.AnimationCurve.DECELERATE),
        content=ft.Column(
            spacing=0,
            controls=[
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=18, vertical=18),
                    border=ft.Border.only(bottom=ft.BorderSide(1, "#1C2E5C")),
                    content=ft.Row(
                        spacing=10,
                        controls=[
                            ft.Container(
                                width=34, height=34, bgcolor=BLUE, border_radius=9,
                                alignment=ft.Alignment.CENTER,
                                content=ft.Text("S", color="white", size=15, weight=ft.FontWeight.BOLD),
                            ),
                            ft.Column(
                                spacing=0,
                                controls=[
                                    ft.Text("SII Connect", color="white", size=14, weight=ft.FontWeight.BOLD),
                                    ft.Text("Dev v1.0", color="#8792AC", size=10),
                                ],
                            ),
                        ],
                    ),
                ),
                ft.Container(
                    expand=True,
                    content=ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO, controls=menu_controls),
                ),
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=16, vertical=14),
                    border=ft.Border.only(top=ft.BorderSide(1, "#1C2E5C")),
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Row(
                                spacing=10,
                                controls=[
                                    ft.Container(
                                        width=32, height=32, bgcolor=BLUE, border_radius=16,
                                        alignment=ft.Alignment.CENTER,
                                        content=ft.Text(nombre_usuario[:2].upper(), color="white", size=12, weight=ft.FontWeight.BOLD),
                                    ),
                                    ft.Column(
                                        spacing=0,
                                        controls=[
                                            ft.Text(nombre_usuario, color="white", size=12, weight=ft.FontWeight.BOLD),
                                            ft.Text(f"Rol: {rol_usuario.capitalize()}", color="#8792AC", size=10),
                                        ],
                                    ),
                                ],
                            ),
                            ft.IconButton(
                                icon=ft.Icons.LOGOUT, icon_color="#B7C0D8", icon_size=17,
                                tooltip="Cerrar sesión", on_click=lambda e: navigate_to("Login"),
                            ),
                        ],
                    ),
                ),
            ],
        ),
    )

    backdrop = ft.Container(
        left=0, top=0, right=0, bottom=0, bgcolor="black", opacity=0, visible=False,
        animate_opacity=ft.Animation(250, ft.AnimationCurve.DECELERATE),
        on_click=close_drawer,
    )

    header = ft.Container(
        bgcolor="white",
        padding=ft.Padding.symmetric(horizontal=16, vertical=14),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Row(
                    spacing=4,
                    controls=[
                        ft.IconButton(icon=ft.Icons.MENU, icon_color=NAVY, on_click=toggle_drawer),
                        ft.Text("Inicio", size=15, weight=ft.FontWeight.BOLD, color=NAVY),
                    ],
                ),
                ft.Row(
                    spacing=14,
                    controls=[
                        ft.Stack(
                            controls=[
                                ft.Icon(ft.Icons.NOTIFICATIONS_OUTLINED, color=NAVY),
                                ft.Container(width=8, height=8, bgcolor=RED_TEXT, border_radius=4, left=10, top=0),
                            ]
                        ),
                        ft.IconButton(
                            icon=ft.Icons.LOGOUT, icon_color=NAVY, icon_size=18,
                            tooltip="Cerrar sesión", on_click=lambda e: navigate_to("Login"),
                        ),
                    ],
                ),
            ],
        ),
    )

    # Configurar Widgets del Body dinámicamente según el Rol
    quick_actions_list = []
    
    if rol_usuario == "emisor":
        subtitulo_rol = "Resumen de emisión y actividad tributaria."
        quick_actions_list = [
            quick_action("+ Emitir boleta de honorario", on_click=lambda e: navigate_to("Emitir BHE")),
            quick_action("Ver mis boletas emitidas", on_click=lambda e: navigate_to("Mis BHE")),
            quick_action("Gestión de Certificado Digital"),
        ]
    elif rol_usuario == "contador":
        subtitulo_rol = "Módulo de supervisión y auditoría de documentos."
        quick_actions_list = [
            quick_action("Revisar todas las BHE", on_click=lambda e: navigate_to("Mis BHE")),
            quick_action("Exportar registros contables"),
            quick_action("Verificar receptores activos"),
        ]
    else:  # cliente
        subtitulo_rol = "Portal de consulta de boletas recibidas."
        quick_actions_list = [
            quick_action("Ver boletas de honorarios recibidas", on_click=lambda e: navigate_to("Mis BHE")),
            quick_action("Descargar certificados de retención"),
        ]

    body = ft.Container(
        padding=ft.Padding.symmetric(horizontal=20, vertical=16),
        content=ft.Column(
            spacing=14, horizontal_alignment=ft.CrossAxisAlignment.START,
            controls=[
                ft.Text(f"Buenas tardes, {nombre_usuario}", size=22, weight=ft.FontWeight.BOLD, color=NAVY),
                ft.Text(subtitulo_rol, size=13, color=GREY_TEXT),
                ft.Container(height=4),
                
                # Tarjetas de estadísticas adaptadas
                stat_card("Cobrado este mes", "$1.240.000", GREEN, "+12% vs mes anterior", GREEN),
                stat_card("Retención acumulada", "$189.100", ORANGE, "14.5% retención actual"),
                stat_card("Documentos del mes", "5", BLUE, "Boletas procesadas"),
                ft.Container(height=6),
                
                # Bloque de Acciones Rápidas según Permisos
                ft.Container(
                    bgcolor="white", border_radius=CARD_RADIUS, padding=18, width=380,
                    shadow=ft.BoxShadow(blur_radius=12, color="#12000000", offset=ft.Offset(0, 3)),
                    content=ft.Column(
                        spacing=10,
                        controls=[
                            ft.Text("Acciones permitidas", size=15, weight=ft.FontWeight.BOLD, color=NAVY),
                            *quick_actions_list
                        ],
                    ),
                ),
                ft.Container(height=6),
                
                # Lista de Registros Recientes
                ft.Container(
                    bgcolor="white", border_radius=CARD_RADIUS, padding=18, width=380,
                    shadow=ft.BoxShadow(blur_radius=12, color="#12000000", offset=ft.Offset(0, 3)),
                    content=ft.Column(
                        spacing=4,
                        controls=[
                            ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    ft.Text("Últimos movimientos", size=15, weight=ft.FontWeight.BOLD, color=NAVY),
                                    ft.Text("Ver todos →", size=12, color=BLUE),
                                ],
                            ),
                            pending_row("Importadora Santa Cruz SpA", "Boleta #1205 · $1.200.000", "$1.200.000", "Vigente", "hace 2 días"),
                            pending_row("Constructora Andina Ltda.", "Boleta #1204 · $850.000", "$850.000", "Vigente", "hace 5 días"),
                        ],
                    ),
                ),
                ft.Container(height=30),
            ],
        ),
    )

    page_content = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO, expand=True, controls=[header, body])
    return ft.Stack(expand=True, controls=[page_content, backdrop, drawer])