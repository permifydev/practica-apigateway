from datetime import date
import flet as ft
from src.utils.constants import NAVY, GREEN, ORANGE, GREY_TEXT, CARD_RADIUS
from src.services.supabase_service import SupabaseService
from src.utils.helpers import formato_clp

db_service = SupabaseService()

MESES_NOMBRE = [
    "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]

ROLES_PERMITIDOS = ("receptor", "empresa")


def _num(valor) -> float:
    """PostgREST puede devolver numeric como numero o como texto."""
    try:
        return float(valor or 0)
    except (TypeError, ValueError):
        return 0.0


def _pantalla_mensaje(titulo: str, texto: str, navigate_to):
    return ft.Container(
        padding=40,
        alignment=ft.alignment.Alignment(0, 0),
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                ft.Text(titulo, size=22, weight=ft.FontWeight.BOLD, color=NAVY),
                ft.Text(texto, color=GREY_TEXT, text_align=ft.TextAlign.CENTER),
                ft.Container(height=15),
                ft.ElevatedButton("Volver al Inicio", on_click=lambda e: navigate_to("Inicio")),
            ],
        ),
    )


def build_resumen_ingresos(page: ft.Page, state: dict, navigate_to):
    """Resumen de ingresos de la EMPRESA (segun el dibujo del jefe):
    cuanto vendio cada usuario en el mes a traves de la empresa, el total, la
    comision de la plataforma (15%) y lo que le corresponde a los usuarios.
    Todo sale de Supabase (tabla ventas / vista v_resumen_ingresos):
    NO consulta al SII, NO pide Clave SII y NO gasta creditos."""
    usuario_info = state.get("usuario", {})
    rol = str(usuario_info.get("rol", "")).lower()

    if rol not in ROLES_PERMITIDOS:
        return _pantalla_mensaje(
            "Acceso Denegado",
            "El resumen de ingresos es solo para cuentas de empresa.",
            navigate_to,
        )

    empresa = db_service.obtener_mi_empresa(usuario_info.get("id"))
    if not empresa:
        return _pantalla_mensaje(
            "Falta tu empresa",
            "Tu cuenta todavia no esta asociada a una empresa. "
            "Pidele al administrador que te la asigne.",
            navigate_to,
        )

    comision_pct = _num(empresa.get("comision_pct"))

    # Por defecto se muestra el mes ANTERIOR (el mes ya cerrado), igual que en
    # el ejemplo del jefe: en octubre se revisan los ingresos de septiembre.
    hoy = date.today()
    periodo_sel = {"anio": hoy.year if hoy.month > 1 else hoy.year - 1,
                   "mes": hoy.month - 1 if hoy.month > 1 else 12}

    titulo_mes = ft.Text("", size=16, weight=ft.FontWeight.BOLD, color=NAVY)
    filas_usuarios = ft.Column(spacing=0)
    msg_status = ft.Text("", size=12, color=GREY_TEXT)

    texto_total = ft.Text("$0", size=15, weight=ft.FontWeight.BOLD, color=NAVY)
    texto_comision = ft.Text("$0", size=15, weight=ft.FontWeight.BOLD, color=ORANGE)
    texto_usuarios = ft.Text("$0", size=15, weight=ft.FontWeight.BOLD, color=GREEN)

    def fila(izq: str, der: str, negrita=False, color=NAVY, borde=True):
        return ft.Container(
            padding=ft.padding.symmetric(vertical=9),
            border=ft.border.only(bottom=ft.BorderSide(1, "#EEF0F3")) if borde else None,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text(izq, size=13, color=color,
                            weight=ft.FontWeight.BOLD if negrita else ft.FontWeight.NORMAL,
                            expand=True),
                    ft.Text(der, size=13, color=color,
                            weight=ft.FontWeight.BOLD if negrita else ft.FontWeight.NORMAL),
                ],
            ),
        )

    def cargar():
        anio, mes = periodo_sel["anio"], periodo_sel["mes"]
        titulo_mes.value = f"Ingresos mes {MESES_NOMBRE[mes]} {anio}"

        datos = db_service.resumen_ingresos_mes(empresa["id"], anio, mes)
        filas_usuarios.controls.clear()

        if not datos:
            msg_status.value = "No hay ventas registradas para este mes."
            msg_status.color = GREY_TEXT
            total = 0.0
        else:
            msg_status.value = f"{len(datos)} usuario(s) con ventas este mes."
            msg_status.color = GREY_TEXT
            filas_usuarios.controls.append(
                fila("Usuario", "Ventas", negrita=True, color=GREY_TEXT)
            )
            for d in datos:
                nombre = d.get("usuario_nombre") or d.get("usuario_email") or "---"
                filas_usuarios.controls.append(
                    fila(f"Ventas {nombre}", formato_clp(_num(d.get("total_ventas"))))
                )
            total = sum(_num(d.get("total_ventas")) for d in datos)

        comision = round(total * comision_pct / 100)
        texto_total.value = formato_clp(total)
        texto_comision.value = formato_clp(comision)
        texto_usuarios.value = formato_clp(total - comision)
        page.update()

    def mes_anterior(e):
        periodo_sel["mes"] -= 1
        if periodo_sel["mes"] < 1:
            periodo_sel["mes"] = 12
            periodo_sel["anio"] -= 1
        cargar()

    def mes_siguiente(e):
        periodo_sel["mes"] += 1
        if periodo_sel["mes"] > 12:
            periodo_sel["mes"] = 1
            periodo_sel["anio"] += 1
        cargar()

    def al_elegir_fecha(e):
        if date_picker.value:
            periodo_sel["anio"] = date_picker.value.year
            periodo_sel["mes"] = date_picker.value.month
            cargar()

    date_picker = ft.DatePicker(
        first_date=date(2020, 1, 1),
        last_date=hoy,
        value=hoy,
        on_change=al_elegir_fecha,
    )

    def abrir_calendario(e):
        if date_picker not in page.overlay:
            page.overlay.append(date_picker)
        date_picker.open = True
        page.update()

    selector_periodo = ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        controls=[
            ft.IconButton(icon=ft.Icons.CHEVRON_LEFT, on_click=mes_anterior),
            ft.Row(
                spacing=4,
                controls=[
                    titulo_mes,
                    ft.IconButton(icon=ft.Icons.CALENDAR_MONTH, icon_size=18,
                                  tooltip="Elegir otro mes", on_click=abrir_calendario),
                ],
            ),
            ft.IconButton(icon=ft.Icons.CHEVRON_RIGHT, on_click=mes_siguiente),
        ],
    )

    bloque_totales = ft.Container(
        bgcolor="#F1F3F6", border_radius=10,
        padding=ft.padding.symmetric(vertical=6, horizontal=14),
        content=ft.Column(
            spacing=0,
            controls=[
                ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                    ft.Text("Total ventas", size=13, color=GREY_TEXT), texto_total]),
                ft.Divider(height=10, color="#E2E5EA"),
                ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                    ft.Text(f"Comision plataforma: {comision_pct:g}%", size=13, color=GREY_TEXT),
                    texto_comision]),
                ft.Divider(height=10, color="#E2E5EA"),
                ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                    ft.Text("A pagar a usuarios", size=13, color=GREY_TEXT), texto_usuarios]),
            ],
        ),
    )

    # Responsive: mismo patron que solicitar_bhe_view
    ANCHO_MAXIMO_TARJETA = 450

    def ancho_tarjeta():
        if page.width and page.width < ANCHO_MAXIMO_TARJETA + 40:
            return page.width - 40
        return ANCHO_MAXIMO_TARJETA

    tarjeta = ft.Container(
        bgcolor="white", border_radius=CARD_RADIUS, padding=20, width=ancho_tarjeta(),
        content=ft.Column([
            ft.Text(empresa.get("nombre", ""), size=13, weight=ft.FontWeight.BOLD, color=NAVY),
            ft.Text(f"RUT {empresa.get('rut', '---')}", size=11, color=GREY_TEXT),
            selector_periodo,
            ft.Divider(height=1, color="#EEF0F3"),
            filas_usuarios,
            msg_status,
            ft.Container(height=6),
            bloque_totales,
        ]),
    )

    def on_resize(e):
        tarjeta.width = ancho_tarjeta()
        page.update()

    page.on_resized = on_resize

    cargar()

    return ft.Container(
        padding=20,
        expand=True,
        content=ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                ft.Row([
                    ft.TextButton("Volver", on_click=lambda e: navigate_to("Inicio")),
                    ft.Text("Resumen de Ingresos", size=18, weight=ft.FontWeight.BOLD, color=NAVY),
                ]),
                tarjeta,
            ],
        ),
    )
