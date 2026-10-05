import flet as ft
from src.utils.constants import NAVY, RED_TEXT, GREEN, GREY_TEXT, CARD_RADIUS, tasa_retencion_vigente
from src.services.supabase_service import SupabaseService
from src.utils.helpers import validar_rut, parse_monto, formato_clp, activar_formato_rut_en_vivo

db_service = SupabaseService()


def build_solicitar_bhe(page: ft.Page, state: dict, navigate_to):
    usuario_info = state.get("usuario", {})
    rol = str(usuario_info.get("rol", "")).lower()

    if rol != "receptor":
        return ft.Container(
            padding=40,
            alignment=ft.alignment.Alignment(0, 0),
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                controls=[
                    ft.Text("Acceso Denegado", size=22, weight=ft.FontWeight.BOLD, color=NAVY),
                    ft.Text("Solo los usuarios con rol Receptor pueden solicitar la emision de una BHE.", color=GREY_TEXT),
                    ft.Container(height=15),
                    ft.ElevatedButton("Volver al Inicio", on_click=lambda e: navigate_to("Inicio"))
                ]
            )
        )

    # --- Datos del receptor (quien solicita) ---
    # El RUT no se edita a mano: es el que tiene asignado el perfil (solo el admin lo
    # cambia, con registrar_rut_perfil.py), igual que el RUT Emisor en Mis BHE. Asi
    # un receptor no puede mandar una solicitud con un RUT que no es el suyo.
    rut_receptor = ft.TextField(
        label="Tu RUT", hint_text="12.345.678-9", value=usuario_info.get("rut") or "",
        disabled=True,
    )
    nombre_receptor = ft.TextField(
        label="Tu Nombre / Razon Social", value=usuario_info.get("nombre") or "",
    )
    direccion_receptor = ft.TextField(label="Tu Direccion", hint_text="Av. Principal 123")
    comuna_receptor = ft.TextField(label="Tu Comuna", hint_text="Santiago")
    email_receptor = ft.TextField(
        label="Tu Correo de contacto", value=usuario_info.get("email") or "",
    )

    # --- Datos de la empresa/emisor a quien se le solicita ---
    empresa_nombre = ft.TextField(label="Nombre de la Empresa", hint_text="Constructora Andina Ltda.")
    empresa_rut = ft.TextField(label="RUT de la Empresa", hint_text="76.111.222-3")
    activar_formato_rut_en_vivo(empresa_rut)  # solo se escriben numeros (y K)
    empresa_direccion = ft.TextField(label="Direccion de la Empresa", hint_text="Av. Principal 456")

    # --- Detalle del servicio ---
    descripcion_servicio = ft.TextField(label="Detalle del Servicio Prestado", multiline=True, min_lines=2)
    monto_bruto = ft.TextField(label="Monto Bruto ($)", keyboard_type=ft.KeyboardType.NUMBER)

    texto_monto_bruto = ft.Text("$0", size=18, weight=ft.FontWeight.BOLD, color=NAVY)
    texto_monto_neto = ft.Text("$0", size=18, weight=ft.FontWeight.BOLD, color=GREEN)
    texto_retencion = ft.Text("", size=11, color=GREY_TEXT)

    resumen_montos = ft.Container(
        bgcolor="#F1F3F6",
        border_radius=10,
        padding=ft.padding.symmetric(vertical=10, horizontal=14),
        content=ft.Column(
            spacing=2,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Column([
                            ft.Text("Monto Bruto", size=11, color=GREY_TEXT),
                            texto_monto_bruto,
                        ]),
                        ft.Column(
                            horizontal_alignment=ft.CrossAxisAlignment.END,
                            controls=[
                                ft.Text("Monto Neto", size=11, color=GREY_TEXT),
                                texto_monto_neto,
                            ],
                        ),
                    ],
                ),
                texto_retencion,
            ],
        ),
    )

    msg_status = ft.Text("", size=12)

    def actualizar_preview(e=None):
        monto_val = parse_monto(monto_bruto.value) or 0
        tasa = tasa_retencion_vigente()
        retenido = round(monto_val * tasa)
        neto = monto_val - retenido
        texto_monto_bruto.value = formato_clp(monto_val)
        texto_monto_neto.value = formato_clp(neto)
        texto_retencion.value = f"Retencion estimada ({tasa*100:.2f}%): {formato_clp(retenido)}" if monto_val else ""
        page.update()

    monto_bruto.on_change = actualizar_preview

    def enviar_solicitud(e):
        campos_receptor = [rut_receptor, nombre_receptor, direccion_receptor, comuna_receptor]
        campos_empresa = [empresa_nombre, empresa_rut, empresa_direccion]

        if any(not c.value or not c.value.strip() for c in campos_receptor + campos_empresa):
            msg_status.value = "Completa todos tus datos y los de la empresa antes de enviar."
            msg_status.color = RED_TEXT
            page.update()
            return

        if not descripcion_servicio.value or not descripcion_servicio.value.strip():
            msg_status.value = "Describe brevemente el servicio prestado."
            msg_status.color = RED_TEXT
            page.update()
            return

        if not validar_rut(rut_receptor.value.strip()):
            msg_status.value = "Tu RUT no es valido (revisa el digito verificador)."
            msg_status.color = RED_TEXT
            page.update()
            return

        if not validar_rut(empresa_rut.value.strip()):
            msg_status.value = "El RUT de la empresa no es valido (revisa el digito verificador)."
            msg_status.color = RED_TEXT
            page.update()
            return

        monto_val = parse_monto(monto_bruto.value)
        if not monto_val:
            msg_status.value = "Ingresa un monto bruto valido."
            msg_status.color = RED_TEXT
            page.update()
            return

        tasa = tasa_retencion_vigente()
        monto_liquido = monto_val - round(monto_val * tasa)

        resultado = db_service.crear_solicitud_bhe(
            receptor_usuario_id=usuario_info.get("id"),
            receptor_nombre=nombre_receptor.value.strip(),
            receptor_rut=rut_receptor.value.strip(),
            receptor_direccion=direccion_receptor.value.strip(),
            receptor_comuna=comuna_receptor.value.strip(),
            receptor_email=email_receptor.value.strip() if email_receptor.value else None,
            empresa_nombre=empresa_nombre.value.strip(),
            empresa_rut=empresa_rut.value.strip(),
            empresa_direccion=empresa_direccion.value.strip(),
            descripcion_servicio=descripcion_servicio.value.strip(),
            monto_bruto=monto_val,
            monto_liquido=monto_liquido,
        )

        if resultado is None:
            msg_status.value = "No se pudo guardar la solicitud. Intenta nuevamente."
            msg_status.color = RED_TEXT
            page.update()
            return

        msg_status.value = "Solicitud enviada. Quedara pendiente hasta que la empresa la revise y emita la boleta."
        msg_status.color = GREEN
        empresa_nombre.value = ""
        empresa_rut.value = ""
        empresa_direccion.value = ""
        descripcion_servicio.value = ""
        monto_bruto.value = ""
        actualizar_preview()
        page.update()

    # Responsive: igual patron que el resto de las pantallas (celular usa el ancho
    # disponible completo en vez de un valor fijo).
    ANCHO_MAXIMO_TARJETA = 450

    def ancho_tarjeta():
        if page.width and page.width < ANCHO_MAXIMO_TARJETA + 40:
            return page.width - 40
        return ANCHO_MAXIMO_TARJETA

    tarjeta_formulario = ft.Container(
        bgcolor="white", border_radius=CARD_RADIUS, padding=20, width=ancho_tarjeta(),
        content=ft.Column([
            ft.Text("Tus Datos (Receptor)", size=13, weight=ft.FontWeight.BOLD, color=NAVY),
            rut_receptor,
            nombre_receptor,
            direccion_receptor,
            comuna_receptor,
            email_receptor,
            ft.Divider(height=1, color="#EEF0F3"),
            ft.Text("Empresa a la que le solicitas la boleta", size=13, weight=ft.FontWeight.BOLD, color=NAVY),
            empresa_nombre,
            empresa_rut,
            empresa_direccion,
            ft.Divider(height=1, color="#EEF0F3"),
            ft.Text("Detalle del servicio", size=13, weight=ft.FontWeight.BOLD, color=NAVY),
            descripcion_servicio,
            monto_bruto,
            resumen_montos,
            msg_status,
            ft.ElevatedButton(
                "Enviar Solicitud",
                on_click=enviar_solicitud,
                width=ancho_tarjeta() - 40,
                height=46,
            ),
        ])
    )

    def on_resize(e):
        tarjeta_formulario.width = ancho_tarjeta()
        page.update()

    page.on_resized = on_resize

    return ft.Container(
        padding=20,
        expand=True,
        content=ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            controls=[
                ft.Row([
                    ft.TextButton("Volver", on_click=lambda e: navigate_to("Inicio")),
                    ft.Text("Solicitar Emision de BHE", size=20, weight=ft.FontWeight.BOLD, color=NAVY)
                ]),
                tarjeta_formulario,
            ]
        )
    )