from datetime import date
import flet as ft
from src.utils.constants import NAVY, CARD_RADIUS
from src.services.supabase_service import db_de_sesion
from src.services.correo_service import pedir_envio_correos
from src.utils.helpers import formato_clp, formato_rut_puntos


# El jefe pidio TODOS los textos en negro (los grises no se leian bien).
NEGRO = "#000000"
ROJO = "#B00020"
VERDE = "#0B6B3A"

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


def _txt(texto, size=13, bold=False, color=NEGRO, **kw):
    return ft.Text(texto, size=size, color=color,
                   weight=ft.FontWeight.BOLD if bold else ft.FontWeight.NORMAL, **kw)


def _pantalla_mensaje(titulo: str, texto: str, navigate_to):
    return ft.Container(
        padding=40,
        alignment=ft.alignment.Alignment(0, 0),
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                _txt(titulo, size=22, bold=True),
                _txt(texto, text_align=ft.TextAlign.CENTER),
                ft.Container(height=15),
                ft.ElevatedButton("Volver al Inicio", on_click=lambda e: navigate_to("Inicio")),
            ],
        ),
    )


def build_resumen_ingresos(page: ft.Page, state: dict, navigate_to):
    db_service = db_de_sesion(state)  # cliente de ESTA persona (su sesion)
    """Pantalla unica "Resumen ventas y comisiones" (dibujo del jefe):

        Usuario | Ventas | Comision plataforma | A pagar a usuarios | Solicitar BHE

    ENVIAR SOLICITUD le pide al usuario que emita una BHE por "A pagar a usuarios".
    La BD calcula los montos, crea la notificacion en la app y deja el correo en
    cola (migracion 007). Todo sale de Supabase: no consulta al SII ni gasta creditos."""
    usuario_info = state.get("usuario", {})
    rol = str(usuario_info.get("rol", "")).lower()

    if rol not in ROLES_PERMITIDOS:
        return _pantalla_mensaje("Acceso Denegado",
                                 "Esta pantalla es solo para cuentas de empresa.", navigate_to)

    empresa = db_service.obtener_mi_empresa(usuario_info.get("id"))
    if not empresa:
        return _pantalla_mensaje(
            "Falta tu empresa",
            "Tu cuenta todavia no esta asociada a una empresa. Pidele al administrador que te la asigne.",
            navigate_to,
        )

    comision_pct = _num(empresa.get("comision_pct"))

    # Por defecto el mes anterior (el mes ya cerrado): en octubre se pagan las ventas de septiembre.
    hoy = date.today()
    periodo_sel = {"anio": hoy.year if hoy.month > 1 else hoy.year - 1,
                   "mes": hoy.month - 1 if hoy.month > 1 else 12}

    titulo_mes = _txt("", size=15, bold=True)
    msg_status = _txt("")

    tabla = ft.DataTable(
        heading_row_height=44,
        data_row_min_height=52,
        data_row_max_height=60,
        column_spacing=28,
        horizontal_lines=ft.BorderSide(1, "#D0D4DC"),
        heading_text_style=ft.TextStyle(color=NEGRO, size=13, weight=ft.FontWeight.BOLD),
        data_text_style=ft.TextStyle(color=NEGRO, size=13),
        columns=[
            ft.DataColumn(_txt("Usuario", bold=True)),
            ft.DataColumn(_txt("Ventas", bold=True), numeric=True),
            ft.DataColumn(_txt(f"Comision plataforma: {comision_pct:g}%", bold=True), numeric=True),
            ft.DataColumn(_txt("A pagar a usuarios", bold=True), numeric=True),
            ft.DataColumn(_txt("Solicitar BHE", bold=True)),
        ],
        rows=[],
    )

    # ---------- Confirmacion antes de enviar ----------
    pendiente = {"fila": None}
    texto_confirmacion = _txt("")

    def cerrar_confirmacion(e=None):
        dialog_confirmar.open = False
        page.update()

    def confirmar_envio(e):
        cerrar_confirmacion()
        d = pendiente["fila"]
        if not d:
            return
        ok, mensaje = db_service.enviar_solicitud_bhe(
            empresa["id"], d["emisor_id"], periodo_sel["anio"], periodo_sel["mes"])
        if ok:
            # El correo ya quedo en cola en Supabase; se le pide a Django que lo
            # envie ahora. Si Django no responde, se envia en la siguiente pasada.
            msg_status.value = "Enviando correo..."
            msg_status.color = NEGRO
            page.update()
            if pedir_envio_correos():
                mensaje = "Solicitud enviada. El usuario recibio la notificacion en la app y el correo."
            else:
                mensaje = ("Solicitud enviada. El usuario ya la ve en sus notificaciones; "
                           "el correo quedo en cola y se enviara en unos minutos.")
        msg_status.value = mensaje
        msg_status.color = VERDE if ok else ROJO
        cargar()

    dialog_confirmar = ft.AlertDialog(
        modal=True,
        title=_txt("Enviar solicitud de BHE", size=17, bold=True),
        content=texto_confirmacion,
        actions=[
            ft.TextButton("Cancelar", on_click=cerrar_confirmacion,
                          style=ft.ButtonStyle(color=NEGRO)),
            ft.ElevatedButton("Enviar", on_click=confirmar_envio,
                              style=ft.ButtonStyle(bgcolor=NAVY, color="white")),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    def abrir_confirmacion(d):
        def handler(e):
            pendiente["fila"] = d
            nombre = d.get("usuario_nombre") or d.get("usuario_email") or "el usuario"
            texto_confirmacion.value = (
                f"Se le pedira a {nombre} emitir una boleta de honorarios por "
                f"{formato_clp(_num(d.get('monto_usuario')))} "
                f"(ventas de {MESES_NOMBRE[periodo_sel['mes']].lower()} {periodo_sel['anio']}).\n\n"
                "Le llegara una notificacion en la app y un correo con el detalle."
            )
            # page.open()/page.close() no existen en esta version de Flet:
            # overlay + open=True/False + update().
            if dialog_confirmar not in page.overlay:
                page.overlay.append(dialog_confirmar)
            dialog_confirmar.open = True
            page.update()
        return handler

    # ---------- Tabla ----------
    def celda_solicitud(d):
        if d.get("estado_solicitud"):
            fecha = str(d.get("solicitud_fecha") or "")[:10]
            if len(fecha) == 10:
                fecha = f"{fecha[8:10]}/{fecha[5:7]}"
            estado = {"pendiente": "Enviada", "emitida": "Emitida", "anulada": "Anulada"}.get(
                d["estado_solicitud"], d["estado_solicitud"])
            return _txt(f"{estado} {fecha}".strip(), bold=True,
                        color=VERDE if d["estado_solicitud"] != "anulada" else ROJO)
        return ft.ElevatedButton(
            "ENVIAR SOLICITUD",
            on_click=abrir_confirmacion(d),
            style=ft.ButtonStyle(bgcolor=NAVY, color="white",
                                 text_style=ft.TextStyle(size=12, weight=ft.FontWeight.BOLD)),
        )

    def cargar():
        anio, mes = periodo_sel["anio"], periodo_sel["mes"]
        titulo_mes.value = f"Ingresos mes {MESES_NOMBRE[mes]} {anio}"

        datos = db_service.resumen_ingresos_mes(empresa["id"], anio, mes)
        tabla.rows.clear()

        for d in datos:
            tabla.rows.append(ft.DataRow(cells=[
                ft.DataCell(_txt(d.get("usuario_nombre") or d.get("usuario_email") or "---")),
                ft.DataCell(_txt(formato_clp(_num(d.get("total_ventas"))))),
                ft.DataCell(_txt(formato_clp(_num(d.get("comision"))))),
                ft.DataCell(_txt(formato_clp(_num(d.get("monto_usuario"))), bold=True)),
                ft.DataCell(celda_solicitud(d)),
            ]))

        if datos:
            tabla.rows.append(ft.DataRow(cells=[
                ft.DataCell(_txt("Total", bold=True)),
                ft.DataCell(_txt(formato_clp(sum(_num(d.get("total_ventas")) for d in datos)), bold=True)),
                ft.DataCell(_txt(formato_clp(sum(_num(d.get("comision")) for d in datos)), bold=True)),
                ft.DataCell(_txt(formato_clp(sum(_num(d.get("monto_usuario")) for d in datos)), bold=True)),
                ft.DataCell(_txt("")),
            ]))
            sin_datos.visible = False
            tabla.visible = True
        else:
            sin_datos.visible = True
            tabla.visible = False
        page.update()

    sin_datos = _txt("No hay ventas registradas para este mes.", visible=False)

    # ---------- Selector de mes ----------
    def mover_mes(delta):
        def handler(e):
            m = periodo_sel["mes"] + delta
            a = periodo_sel["anio"]
            if m < 1:
                m, a = 12, a - 1
            elif m > 12:
                m, a = 1, a + 1
            periodo_sel["mes"], periodo_sel["anio"] = m, a
            msg_status.value = ""
            cargar()
        return handler

    def al_elegir_fecha(e):
        if date_picker.value:
            periodo_sel["anio"] = date_picker.value.year
            periodo_sel["mes"] = date_picker.value.month
            msg_status.value = ""
            cargar()

    date_picker = ft.DatePicker(first_date=date(2020, 1, 1), last_date=hoy, value=hoy,
                                on_change=al_elegir_fecha)

    def abrir_calendario(e):
        if date_picker not in page.overlay:
            page.overlay.append(date_picker)
        date_picker.open = True
        page.update()

    selector_periodo = ft.Row(
        spacing=4,
        controls=[
            ft.IconButton(icon=ft.Icons.CHEVRON_LEFT, icon_color=NEGRO, on_click=mover_mes(-1)),
            titulo_mes,
            ft.IconButton(icon=ft.Icons.CALENDAR_MONTH, icon_color=NEGRO, icon_size=18,
                          tooltip="Elegir otro mes", on_click=abrir_calendario),
            ft.IconButton(icon=ft.Icons.CHEVRON_RIGHT, icon_color=NEGRO, on_click=mover_mes(1)),
        ],
    )

    tarjeta = ft.Container(
        bgcolor="white", border_radius=CARD_RADIUS, padding=20,
        content=ft.Column(
            spacing=6,
            controls=[
                _txt("Resumen ventas y comisiones", size=18, bold=True),
                _txt(empresa.get("nombre", ""), size=14, bold=True),
                _txt(f"RUT {formato_rut_puntos(empresa.get('rut') or '') or '---'}"),
                ft.Container(height=4),
                selector_periodo,
                ft.Divider(height=1, color="#D0D4DC"),
                # La tabla es ancha: en pantallas angostas se desplaza hacia el lado
                ft.Row(controls=[tabla, sin_datos], scroll=ft.ScrollMode.AUTO),
                ft.Container(height=4),
                msg_status,
            ],
        ),
    )

    cargar()

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
                ]),
                tarjeta,
            ],
        ),
    )
