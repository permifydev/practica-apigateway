import flet as ft
from src.utils.constants import NAVY, RED_TEXT, GREEN, GREY_TEXT, CARD_RADIUS
from src.services.supabase_service import SupabaseService

db_service = SupabaseService()

def build_certificados(page: ft.Page, state: dict, navigate_to):
    usuario_info = state.get("usuario", {})
    rol = str(usuario_info.get("rol", "emisor")).lower()
    usuario_id = usuario_info.get("id")

    if rol != "emisor":
        return ft.Container(
            padding=40,
            alignment=ft.Alignment.CENTER,
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text("Acceso Denegado", size=22, weight=ft.FontWeight.BOLD, color=NAVY),
                    ft.Text("Solo el perfil emisor administra certificados.", color=GREY_TEXT),
                    ft.Container(height=15),
                    ft.ElevatedButton("Volver al Inicio", on_click=lambda e: navigate_to("Inicio"))
                ]
            )
        )

    certificado_actual = db_service.obtener_certificado_activo(usuario_id)

    estado_texto = ft.Text("", size=13, weight=ft.FontWeight.BOLD)
    estado_sub = ft.Text("", size=12, color=GREY_TEXT)

    def refrescar_estado():
        if certificado_actual:
            estado_texto.value = "Certificado activo"
            estado_texto.color = GREEN
            alias = certificado_actual.get("alias", "Sin alias")
            venc = certificado_actual.get("fecha_vencimiento", "No informada")
            estado_sub.value = f"{alias} · Vence: {venc}"
        else:
            estado_texto.value = "Sin certificado activo"
            estado_texto.color = RED_TEXT
            estado_sub.value = "Registra un certificado para llevar el control de vencimiento."

    refrescar_estado()

    alias_certificado = ft.TextField(label="Alias / Descripcion", hint_text="Ej: Certificado principal")
    fecha_vencimiento = ft.TextField(label="Fecha de vencimiento", hint_text="AAAA-MM-DD")
    referencia_archivo = ft.TextField(label="Referencia de archivo (opcional)", hint_text="Ej: certificado_2026.pfx")
    msg_status = ft.Text("", size=12)

    aviso = ft.Text(
        "Nota: la Clave SII no se guarda aqui. Se solicita directamente al emitir o anular una boleta, "
        "porque la API Gateway la requiere en cada llamada y no la conserva entre solicitudes.",
        size=11, color=GREY_TEXT
    )

    def guardar_registro(e):
        if not alias_certificado.value or not fecha_vencimiento.value:
            msg_status.value = "Completa el alias y la fecha de vencimiento."
            msg_status.color = RED_TEXT
            page.update()
            return

        payload = {
            "usuario_id": usuario_id,
            "alias": alias_certificado.value.strip(),
            "fecha_vencimiento": fecha_vencimiento.value.strip(),
            "archivo_path": referencia_archivo.value.strip() or None,
            "estado": "activo",
        }

        resultado = db_service.guardar_certificado(payload)

        if resultado is not None:
            msg_status.value = "Certificado registrado correctamente."
            msg_status.color = GREEN
            alias_certificado.value = ""
            fecha_vencimiento.value = ""
            referencia_archivo.value = ""
            nonlocal certificado_actual
            certificado_actual = db_service.obtener_certificado_activo(usuario_id)
            refrescar_estado()
            page.update()
        else:
            msg_status.value = "Error al guardar el certificado."
            msg_status.color = RED_TEXT
            page.update()

    return ft.Container(
        padding=20,
        content=ft.Column(
            controls=[
                ft.Row([
                    ft.TextButton("Volver", on_click=lambda e: navigate_to("Inicio")),
                    ft.Text("Certificado Digital", size=20, weight=ft.FontWeight.BOLD, color=NAVY)
                ]),
                ft.Container(
                    bgcolor="white", border_radius=CARD_RADIUS, padding=20, width=450,
                    content=ft.Column([
                        ft.Text("Estado actual", size=13, weight=ft.FontWeight.BOLD, color=NAVY),
                        estado_texto,
                        estado_sub,
                    ])
                ),
                ft.Container(height=14),
                ft.Container(
                    bgcolor="white", border_radius=CARD_RADIUS, padding=20, width=450,
                    content=ft.Column([
                        ft.Text("Registrar / Renovar certificado", size=13, weight=ft.FontWeight.BOLD, color=NAVY),
                        aviso,
                        ft.Container(height=8),
                        alias_certificado,
                        fecha_vencimiento,
                        referencia_archivo,
                        msg_status,
                        ft.ElevatedButton("Guardar Registro", on_click=guardar_registro, width=400, height=45)
                    ])
                )
            ]
        )
    )