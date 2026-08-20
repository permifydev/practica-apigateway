"""
SII Connect - Prototipo mobile en Flet
2 pantallas: Login (sin verificación real, solo para pruebas) y Home

Correr local:
    flet run main.py

Correr como app web (para probar en el navegador o  Render):
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


def main(page: ft.Page):
    page.title = "SII Connect"
    page.bgcolor = BG
    page.window.width = 420
    page.window.height = 900
    page.padding = 0
    page.fonts = {}
    page.theme = ft.Theme(font_family="Roboto")
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    # Estado simple solo prototipo)
    state = {"nombre": "María"}

    # login
    def build_login():
        email_field = ft.TextField(
            label="Correo electrónico",
            hint_text="tu@empresa.cl",
            border_radius=10,
            border_color="#D8DCE3",
            bgcolor="white",
            height=52,
        )
        pass_field = ft.TextField(
            label="Contraseña",
            hint_text="••••••••",
            password=True,
            can_reveal_password=True,
            border_radius=10,
            border_color="#D8DCE3",
            bgcolor="white",
            height=52,
        )
        error_text = ft.Text("", color=RED_TEXT, size=12)

        def do_login(e):
            #no valida nada
            # solo exige que ambos campos tengan algo escrito
            if not email_field.value or not pass_field.value:
                error_text.value = "Ingresa correo y contraseña para continuar"
                page.update()
                return
            #la parte antes del @ como nombre si el correo
            #no trar normbre real solopara que se vea bien
            correo = email_field.value.strip()
            state["nombre"] = "María"
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
                    # Logo
                    ft.Row(
                        alignment=ft.MainAxisAlignment.CENTER,
                        controls=[
                            ft.Container(
                                width=44,
                                height=44,
                                bgcolor=NAVY,
                                border_radius=10,
                                alignment=ft.alignment.center,
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
                                    text="Ingresar",
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
                        "Prototipo de pruebas — sin verificación real de correo",
                        size=11,
                        color=GREY_TEXT,
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
            ),
        )

    #home
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
                text=text,
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
            text=text,
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
            padding=ft.padding.symmetric(vertical=10),
            border=ft.border.only(bottom=ft.BorderSide(1, "#EEF0F3")),
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
                                padding=ft.padding.symmetric(horizontal=10, vertical=3),
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
        header = ft.Container(
            bgcolor="white",
            padding=ft.padding.symmetric(horizontal=16, vertical=14),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Row(
                        spacing=10,
                        controls=[
                            ft.Icon(ft.Icons.MENU, color=NAVY),
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
            padding=ft.padding.symmetric(horizontal=20, vertical=16),
            content=ft.Column(
                spacing=14,
                horizontal_alignment=ft.CrossAxisAlignment.START,
                controls=[
                    ft.Text(f"Buenas tardes, {state['nombre']}", size=22, weight=ft.FontWeight.BOLD, color=NAVY),
                    ft.Text("Aquí tienes el resumen de tu actividad tributaria.", size=13, color=GREY_TEXT),
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
                                quick_action("+ Emitir boleta o factura", filled=True),
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

        return ft.Column(
            spacing=0,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            controls=[header, body],
        )

    # Arranca en Login
    page.add(build_login())


ft.app(target=main)