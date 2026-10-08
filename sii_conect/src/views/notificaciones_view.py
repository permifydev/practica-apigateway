import flet as ft
from src.utils.constants import NAVY, CARD_RADIUS
from src.services.supabase_service import db_de_sesion
from src.utils.helpers import formato_clp, formato_rut_puntos


NEGRO = "#000000"

MESES_NOMBRE = [
    "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]


def _txt(texto, size=13, bold=False, color=NEGRO, **kw):
    return ft.Text(texto, size=size, color=color,
                   weight=ft.FontWeight.BOLD if bold else ft.FontWeight.NORMAL, **kw)


def _num(valor) -> float:
    try:
        return float(valor or 0)
    except (TypeError, ValueError):
        return 0.0


def _mes_texto(periodo: str | None) -> str:
    """'2026-09-01' -> 'Septiembre 2026'."""
    try:
        anio, mes = int(periodo[0:4]), int(periodo[5:7])
        return f"{MESES_NOMBRE[mes]} {anio}"
    except Exception:
        return "---"


def build_notificaciones(page: ft.Page, state: dict, navigate_to):
    db_service = db_de_sesion(state)  # cliente de ESTA persona (su sesion)
    """Notificaciones del usuario (emisor). Hoy el unico tipo es la solicitud de
    emision de BHE que le envia una empresa desde "Resumen ventas y comisiones":
    se muestra el detalle completo (empresa, RUT, direccion, mes y monto) para
    que pueda emitir la boleta desde "Emitir BHE"."""
    usuario_info = state.get("usuario", {})
    usuario_id = usuario_info.get("id")

    lista = ft.Column(spacing=12)

    def fila_dato(etiqueta, valor, bold=False):
        return ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[_txt(etiqueta), _txt(valor, bold=bold)],
        )

    def tarjeta(n):
        sol = n.get("solicitud") or {}
        emp = n.get("empresa") or {}
        btn_leida = ft.TextButton(
            "Marcar como leida",
            visible=not n.get("leida"),
            style=ft.ButtonStyle(color=NEGRO),
        )
        etiqueta_nueva = ft.Container(
            visible=not n.get("leida"),
            bgcolor=NAVY, border_radius=10,
            padding=ft.padding.symmetric(horizontal=8, vertical=2),
            content=ft.Text("NUEVA", size=10, color="white", weight=ft.FontWeight.BOLD),
        )

        def marcar(e):
            if db_service.marcar_notificacion_leida(n["id"]):
                btn_leida.visible = False
                etiqueta_nueva.visible = False
                page.update()

        btn_leida.on_click = marcar

        detalle = []
        if sol:
            detalle = [
                ft.Divider(height=1, color="#D0D4DC"),
                fila_dato("Empresa", emp.get("nombre") or "---"),
                fila_dato("RUT empresa", formato_rut_puntos(emp.get("rut") or "") or "---"),
                fila_dato("Direccion", emp.get("direccion") or "---"),
                fila_dato("Mes", _mes_texto(sol.get("periodo"))),
                fila_dato("Tus ventas", formato_clp(_num(sol.get("monto_ventas")))),
                fila_dato(f"Comision plataforma ({_num(sol.get('comision_pct')):g}%)",
                          formato_clp(_num(sol.get("monto_comision")))),
                fila_dato("Monto de la boleta a emitir", formato_clp(_num(sol.get("monto_a_pagar"))), bold=True),
            ]

        fecha = str(n.get("created_at") or "")[:16].replace("T", " ")

        return ft.Container(
            bgcolor="white", border_radius=CARD_RADIUS, padding=18, width=450,
            content=ft.Column(
                spacing=6,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[_txt(n.get("titulo", ""), size=15, bold=True), etiqueta_nueva],
                    ),
                    _txt(fecha, size=11),
                    _txt(n.get("mensaje", "")),
                    *detalle,
                    ft.Row(
                        alignment=ft.MainAxisAlignment.END,
                        controls=[
                            btn_leida,
                            ft.ElevatedButton(
                                "Emitir BHE",
                                on_click=lambda e: navigate_to("Emitir BHE"),
                                style=ft.ButtonStyle(bgcolor=NAVY, color="white"),
                            ),
                        ],
                    ),
                ],
            ),
        )

    notificaciones = db_service.listar_notificaciones(usuario_id)
    if notificaciones:
        lista.controls = [tarjeta(n) for n in notificaciones]
    else:
        lista.controls = [_txt("No tienes notificaciones.")]

    return ft.Container(
        padding=20,
        expand=True,
        content=ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                ft.Row([
                    ft.TextButton("Volver", on_click=lambda e: navigate_to("Inicio"),
                                  style=ft.ButtonStyle(color=NEGRO)),
                    _txt("Notificaciones", size=18, bold=True),
                ]),
                lista,
            ],
        ),
    )
