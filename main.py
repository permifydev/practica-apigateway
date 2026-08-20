"""
SII Connect - Prototipo mobile en Flet
2 pantallas: Login (sin verificación real, solo para pruebas) y Home / Dashboard.

Correr local:
    flet run main.py

Correr como app web (para probar en el navegador o subir a Render):
    flet run --web main.py
"""

import flet as ft

#paleta de colores
NAVY = "#0A1F44"
NAVY_DARK = "#081833"
BG = "#F1F3F6"
GREEN = "#1E8E5A"
ORANGE = "#E8A33D"
BLUE = "#2F5FD6"
PURPLE = "#7C4DFF"
RED_BG = "#FDE7E7"
RED_TEXT = "#D14343"
YELLOW_BG = "#FCF0D8"
YELLOW_TEXT = "#B5790E"
GREY_TEXT = "#6B7280"
CARD_RADIUS = 16
MENU_HOVER_BG = "#1AFFFFFF"
MENU_ACTIVE_BG = "#16295C"


def main(page: ft.Page):
    page.title = "SII Connect"
    page.bgcolor = BG
    page.window.width = 420
    page.window.height = 900
    page.padding = 0
    page.fonts = {}
    page.theme = ft.Theme(font_family="Roboto")
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    state = {"nombre": "María"}

    #login
    def build_login():
        email_field = ft.TextField(
            label="Correo electrónico",
            hint_text="tu@empresa.cl",
            color=NAVY,
            label_style=ft.TextStyle(color=GREY_TEXT),
            border_radius=10,
            border_color="#D8DCE3",
            bgcolor="white",
            height=52,
        )
        pass_field = ft.TextField(
            label="Contraseña",
            hint_text="********",
            password=True,
            can_reveal_password=True,
            color=NAVY,
            label_style=ft.TextStyle(color=GREY_TEXT),
            border_radius=10,
            border_color="#D8DCE3",
            bgcolor="white",
            height=52,
        )
        error_text = ft.Text("", color=RED_TEXT, size=12)

        def do_login(e):
            # no valida solo pide que tengan algo escrito
            if not email_field.value or not pass_field.value:
                error_text.value = "Ingresa correo y contraseña para continuar"
                page.update()
                return
            correo = email_field.value.strip()
            #lo que esté antes del @ se usa como nombre
            usuario = correo.split("@")[0] if "@" in correo else correo
            usuario = usuario.replace(".", " ").replace("_", " ").strip()
            state["nombre"] = usuario.title() if usuario else "Usuario"
            page.controls.clear()
            page.add(build_home())
            page.update()

        return ft.Container(
            width=420,
            padding=24,
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=0,
                controls=[
                    ft.Container(height=60),
                    #logo
                    ft.Row(
                        alignment=ft.MainAxisAlignment.CENTER,
                        controls=[
                            ft.Container(
                                width=44,
                                height=44,
                                bgcolor=NAVY,
                                border_radius=10,
                                alignment=ft.Alignment.CENTER,
                                content=ft.Text("S", color="white", size=20, weight=ft.FontWeight.BOLD),
                            ),
                            ft.Container(width=10),
                            ft.Column(
                                spacing=0,
                                horizontal_alignment=ft.CrossAxisAlignment.START,
                                controls=[
                                    ft.Text("SII Connect", size=18, weight=ft.FontWeight.BOLD, color=NAVY),
                                    ft.Text("API Servicios Impuestos Internos", size=11, color=GREY_TEXT),
                                ],
                            ),
                        ],
                    ),
                    ft.Container(height=28),
                    # Card
                    ft.Container(
                        bgcolor="white",
                        border_radius=CARD_RADIUS,
                        padding=24,
                        shadow=ft.BoxShadow(blur_radius=20, color="#1A000000", offset=ft.Offset(0, 6)),
                        content=ft.Column(
                            spacing=14,
                            controls=[
                                ft.Text("Iniciar sesión", size=22, weight=ft.FontWeight.BOLD, color=NAVY),
                                ft.Text("Accede a tu cuenta SII Connect", size=13, color=GREY_TEXT),
                                ft.Container(height=6),
                                email_field,
                                pass_field,
                                error_text,
                                ft.Container(height=6),
                                ft.ElevatedButton(
                                    content=ft.Text("Ingresar"),
                                    width=400,
                                    height=48,
                                    style=ft.ButtonStyle(
                                        bgcolor=NAVY,
                                        color="white",
                                        shape=ft.RoundedRectangleBorder(radius=10),
                                        text_style=ft.TextStyle(weight=ft.FontWeight.BOLD, size=15),
                                    ),
                                    on_click=do_login,
                                ),
                            ],
                        ),
                    ),
                    ft.Container(height=20),
                    ft.Text(
                        "sin verificación real del correo",
                        size=11,
                        color=GREY_TEXT,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
            ),
        )

    #incio
    def stat_card(label, value, value_color, sub, sub_color=GREY_TEXT):
        return ft.Container(
            bgcolor="white",
            border_radius=CARD_RADIUS,
            padding=18,
            width=380,
            shadow=ft.BoxShadow(blur_radius=12, color="#12000000", offset=ft.Offset(0, 3)),
            content=ft.Column(
                spacing=4,
                controls=[
                    ft.Text(label, size=12, color=GREY_TEXT),
                    ft.Text(value, size=24, weight=ft.FontWeight.BOLD, color=value_color),
                    ft.Text(sub, size=12, color=sub_color),
                ],
            ),
        )

    def quick_action(text, filled=False, on_click=None):
        if filled:
            return ft.ElevatedButton(
                content=ft.Text(text),
                width=380,
                height=46,
                style=ft.ButtonStyle(
                    bgcolor=NAVY,
                    color="white",
                    shape=ft.RoundedRectangleBorder(radius=10),
                    text_style=ft.TextStyle(weight=ft.FontWeight.BOLD, size=14),
                ),
                on_click=on_click,
            )
        return ft.OutlinedButton(
            content=ft.Text(text),
            width=380,
            height=46,
            style=ft.ButtonStyle(
                color=NAVY,
                side=ft.BorderSide(1, "#D8DCE3"),
                shape=ft.RoundedRectangleBorder(radius=10),
                text_style=ft.TextStyle(weight=ft.FontWeight.W_600, size=14),
            ),
            on_click=on_click,
        )

    def pending_row(empresa, doc, monto, estado, dias):
        estado_bg = RED_BG if estado == "Vencida" else YELLOW_BG
        estado_color = RED_TEXT if estado == "Vencida" else YELLOW_TEXT
        return ft.Container(
            padding=ft.Padding.symmetric(vertical=10),
            border=ft.Border.only(bottom=ft.BorderSide(1, "#EEF0F3")),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Column(
                        spacing=2,
                        horizontal_alignment=ft.CrossAxisAlignment.START,
                        controls=[
                            ft.Text(empresa, size=13, weight=ft.FontWeight.BOLD, color=NAVY),
                            ft.Text(doc, size=12, color=GREY_TEXT),
                        ],
                    ),
                    ft.Column(
                        spacing=4,
                        horizontal_alignment=ft.CrossAxisAlignment.END,
                        controls=[
                            ft.Container(
                                bgcolor=estado_bg,
                                border_radius=12,
                                padding=ft.Padding.symmetric(horizontal=10, vertical=3),
                                content=ft.Text(estado, size=11, color=estado_color, weight=ft.FontWeight.BOLD),
                            ),
                            ft.Text(dias, size=11, color=GREY_TEXT),
                        ],
                    ),
                ],
            ),
        )

    def do_logout(e):
        page.controls.clear()
        page.add(build_login())
        page.update()

    def build_home():
        # menú lateral (abierto/cerrado)
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
                    label,
                    color="white" if active else "#D3D9EA",
                    size=14,
                    weight=ft.FontWeight.BOLD if active else ft.FontWeight.W_500,
                    expand=True,
                ),
            ]
            if badge:
                row_controls.append(
                    ft.Container(
                        bgcolor=BLUE,
                        border_radius=8,
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

        drawer = ft.Container(
            width=260,
            left=-300,
            top=0,
            bottom=0,
            bgcolor=NAVY,
            animate_position=ft.Animation(250, ft.AnimationCurve.DECELERATE),
            content=ft.Column(
                spacing=0,
                controls=[
                    #menu
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
                        content=ft.Column(
                            spacing=2,
                            scroll=ft.ScrollMode.AUTO,
                            controls=[
                                ft.Container(height=8),
                                menu_section_label("PRINCIPAL"),
                                menu_item(ft.Icons.HOME_OUTLINED, "Inicio"),
                                menu_item(ft.Icons.ADD_CIRCLE_OUTLINE, "Emitir"),
                                menu_item(ft.Icons.DESCRIPTION_OUTLINED, "Documentos"),
                                menu_item(ft.Icons.ATTACH_MONEY, "Cobros"),
                                menu_item(ft.Icons.BOLT, "Cobro activo", badge="NUEVO"),
                                menu_item(ft.Icons.SHOPPING_BAG_OUTLINED, "Órdenes de compra"),
                                menu_item(ft.Icons.BAR_CHART, "Estadísticas", badge="NUEVO"),
                                ft.Container(height=10),
                                menu_section_label("HERRAMIENTAS"),
                                menu_item(ft.Icons.SHIELD_OUTLINED, "Certificados"),
                                menu_item(ft.Icons.ACCOUNT_BALANCE_OUTLINED, "Presupuestos UF", badge="NUEVO"),
                                menu_item(ft.Icons.PEOPLE_OUTLINE, "Clientes / RUT", badge="NUEVO"),
                                ft.Container(height=10),
                                menu_section_label("CUENTA"),
                                menu_item(ft.Icons.STAR_OUTLINE, "Planes"),
                                menu_item(ft.Icons.SETTINGS_OUTLINED, "Ajustes"),
                                menu_item(ft.Icons.PERSON_OUTLINE, "Perfil"),
                            ],
                        ),
                    ),
                    #footer con usuario
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
                                            content=ft.Text(
                                                state["nombre"][:2].upper(),
                                                color="white", size=12, weight=ft.FontWeight.BOLD,
                                            ),
                                        ),
                                        ft.Column(
                                            spacing=0,
                                            controls=[
                                                ft.Text(state["nombre"], color="white", size=12, weight=ft.FontWeight.BOLD),
                                                ft.Text("Cuenta de prueba", color="#8792AC", size=10),
                                            ],
                                        ),
                                    ],
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.LOGOUT,
                                    icon_color="#B7C0D8",
                                    icon_size=17,
                                    tooltip="Cerrar sesión",
                                    on_click=do_logout,
                                ),
                            ],
                        ),
                    ),
                ],
            ),
        )

        backdrop = ft.Container(
            left=0, top=0, right=0, bottom=0,
            bgcolor="black",
            opacity=0,
            visible=False,
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
                            ft.IconButton(
                                icon=ft.Icons.MENU,
                                icon_color=NAVY,
                                on_click=toggle_drawer,
                            ),
                            ft.Text("Inicio", size=15, weight=ft.FontWeight.BOLD, color=NAVY),
                        ],
                    ),
                    ft.Row(
                        spacing=14,
                        controls=[
                            ft.Stack(
                                controls=[
                                    ft.Icon(ft.Icons.NOTIFICATIONS_OUTLINED, color=NAVY),
                                    ft.Container(
                                        width=8, height=8, bgcolor=RED_TEXT, border_radius=4,
                                        left=10, top=0,
                                    ),
                                ]
                            ),
                            ft.IconButton(
                                icon=ft.Icons.LOGOUT,
                                icon_color=NAVY,
                                icon_size=18,
                                tooltip="Cerrar sesión (demo)",
                                on_click=do_logout,
                            ),
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
                    ft.Text(f"Buenas tardes, {state['nombre']}", size=22, weight=ft.FontWeight.BOLD, color=NAVY),
                    ft.Text("Resumen de actividad tributaria.", size=13, color=GREY_TEXT),
                    ft.Container(height=4),
                    stat_card("Cobrado este mes", "$1.240.000", GREEN, "+12% vs mes anterior", GREEN),
                    stat_card("Por cobrar", "$540.000", ORANGE, "3 documentos pendientes"),
                    stat_card("Emitido hoy", "$350.000", BLUE, "2 documentos"),
                    stat_card("OCs pendientes", "2", PURPLE, "Requieren revisión"),
                    ft.Container(height=6),
                    ft.Container(
                        bgcolor="white",
                        border_radius=CARD_RADIUS,
                        padding=18,
                        width=380,
                        shadow=ft.BoxShadow(blur_radius=12, color="#12000000", offset=ft.Offset(0, 3)),
                        content=ft.Column(
                            spacing=10,
                            controls=[
                                ft.Text("Acciones rápidas", size=15, weight=ft.FontWeight.BOLD, color=NAVY),
                                quick_action("+ Emitir boleta o factura"),
                                quick_action("Registrar pago recibido"),
                                quick_action("Enviar cobro a cliente"),
                                quick_action("Ver pendientes de cobro"),
                            ],
                        ),
                    ),
                    ft.Container(height=6),
                    ft.Container(
                        bgcolor="white",
                        border_radius=CARD_RADIUS,
                        padding=18,
                        width=380,
                        shadow=ft.BoxShadow(blur_radius=12, color="#12000000", offset=ft.Offset(0, 3)),
                        content=ft.Column(
                            spacing=4,
                            controls=[
                                ft.Row(
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                    controls=[
                                        ft.Text("Pendientes de cobro", size=15, weight=ft.FontWeight.BOLD, color=NAVY),
                                        ft.Text("Ver todos →", size=12, color=BLUE),
                                    ],
                                ),
                                pending_row("Importadora Santa Cruz SpA", "Factura #891 · $2.850.000", "$2.850.000", "Vencida", "hace 12 días"),
                                pending_row("Constructora Andina Ltda.", "Factura #882 · $1.140.000", "$1.140.000", "Pendiente", "vence hoy"),
                                pending_row("Servicios Norte Ltda.", "Boleta #1204 · $820.000", "$820.000", "Pendiente", "en 3 días"),
                                pending_row("Tech Solutions SPA", "Boleta #1178 · $125.000", "$125.000", "Vencida", "hace 12 días"),
                            ],
                        ),
                    ),
                    ft.Container(height=30),
                ],
            ),
        )

        page_content = ft.Column(
            spacing=0,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            controls=[header, body],
        )

        return ft.Stack(
            expand=True,
            controls=[page_content, backdrop, drawer],
        )

    # Arranca en Login
    page.add(build_login())


ft.app(target=main)

##################
