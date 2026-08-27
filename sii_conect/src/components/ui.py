import flet as ft
from src.utils.constants import NAVY, GREY_TEXT, CARD_RADIUS, RED_BG, RED_TEXT, YELLOW_BG, YELLOW_TEXT

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
    style_bg = NAVY if filled else None
    style_color = "white" if filled else NAVY
    
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