import logging
from datetime import datetime, date
from supabase import Client
from src.config import supabase as _shared_client

logger = logging.getLogger(__name__)


class SupabaseService:
    def __init__(self):
        self.client: Client = _shared_client

    def iniciar_sesion(self, email: str, password: str) -> dict | None:
        """Inicia sesión real contra Supabase Auth."""
        if not self.client:
            return None
        try:
            res = self.client.auth.sign_in_with_password({"email": email.strip().lower(), "password": password})
            if res and res.user:
                logger.info(f"[Supabase Auth] Sesion iniciada: {res.user.email}")
                return {"id": res.user.id, "email": res.user.email}
            return None
        except Exception as e:
            logger.warning(f"[Supabase Auth] Login rechazado para '{email}': {e}")
            return None

    def cerrar_sesion(self):
        if self.client:
            try:
                self.client.auth.sign_out()
            except Exception as e:
                logger.error(f"Error al cerrar sesion: {e}")

    def obtener_perfil_propio(self, usuario_id: str) -> dict | None:
        """Trae el perfil del usuario ya autenticado."""
        if not self.client:
            return None
        try:
            res = self.client.table("perfiles")\
                .select("id, nombre_completo, rut, rol, email")\
                .eq("id", usuario_id)\
                .execute()
            if res.data:
                usr = res.data[0]
                return {
                    "id": usr["id"],
                    "nombre": usr.get("nombre_completo", "Usuario"),
                    "rut": usr.get("rut"),
                    "rol": str(usr.get("rol", "usuario")).lower(),
                    "email": usr.get("email"),
                }
            logger.warning(f"[Supabase REAL] Sesion valida pero sin fila en 'perfiles' para id={usuario_id}")
            return None
        except Exception as e:
            logger.error(f"Error al obtener perfil propio: {e}")
            return None

    def validar_usuario(self, identificador: str) -> dict | None:
        """Valida usuario contra Supabase Auth."""
        if not self.client:
            logger.warning("validar_usuario() fue llamado con cliente Supabase sin inicializar.")
            return None
        logger.warning("validar_usuario() fue llamado con un cliente Supabase real: usa iniciar_sesion().")
        return None

    def actualizar_perfil(self, usuario_id: str, email: str) -> dict | None:
        """Actualiza el correo de contacto del perfil."""
        try:
            response = self.client.table("perfiles").update({"email": email}).eq("id", usuario_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error al actualizar perfil: {e}")
            return None

    def obtener_o_crear_receptor(self, rut: str, nombre: str, email: str = "", usuario_id: str | None = None) -> dict | None:
        """Busca un receptor por RUT o lo crea si no existe."""
        try:
            rut_clean = rut.strip()
            res = self.client.table("receptores").select("id, nombre, rut").eq("rut", rut_clean).execute()
            if res.data:
                return res.data[0]

            payload = {
                "rut": rut_clean,
                "nombre": nombre.strip(),
            }
            if email:
                payload["email"] = email.strip()
            if usuario_id:
                payload["usuario_id"] = usuario_id

            nuevo = self.client.table("receptores").insert(payload).execute()
            return nuevo.data[0] if (nuevo and nuevo.data) else None
        except Exception as e:
            logger.error(f"Error en obtener_o_crear_receptor: {e}")
            return None

    def listar_receptores(self) -> list[dict]:
        """Devuelve todos los receptores registrados."""
        try:
            res = self.client.table("receptores").select("id, rut, nombre, email").order("nombre").execute()
            return res.data or []
        except Exception as e:
            logger.error(f"Error al listar receptores: {e}")
            return []

    def crear_receptor(self, rut: str, nombre: str, email: str = "", usuario_id: str | None = None) -> dict | None:
        """Crea un receptor nuevo."""
        try:
            payload = {"rut": rut.strip(), "nombre": nombre.strip()}
            if email:
                payload["email"] = email.strip()
            if usuario_id:
                payload["usuario_id"] = usuario_id

            response = self.client.table("receptores").insert(payload).execute()
            return response.data[0] if (response and response.data) else None
        except Exception as e:
            logger.error(f"Error al crear receptor: {e}")
            return None

    def actualizar_receptor(self, receptor_id: str, nombre: str, email: str = "") -> dict | None:
        """Actualiza nombre y correo de un receptor existente."""
        try:
            response = self.client.table("receptores").update({"nombre": nombre, "email": email}).eq("id", receptor_id).execute()
            return response.data[0] if (response and response.data) else None
        except Exception as e:
            logger.error(f"Error al actualizar receptor: {e}")
            return None

    def obtener_certificado_activo(self, usuario_id: str) -> dict | None:
        """Devuelve el certificado digital vigente del usuario."""
        try:
            res = self.client.table("certificados_digitales")\
                .select("id, alias, archivo_path, fecha_carga, fecha_vencimiento, estado")\
                .eq("usuario_id", usuario_id)\
                .eq("estado", "activo")\
                .order("fecha_vencimiento", desc=True)\
                .limit(1)\
                .execute()
            return res.data[0] if (res and res.data) else None
        except Exception as e:
            logger.error(f"Error al consultar certificado activo: {e}")
            return None

    def guardar_certificado(self, certificado_data: dict) -> dict | None:
        """Inserta un registro de certificado."""
        try:
            usuario_id = certificado_data.get("usuario_id")

            self.client.table("certificados_digitales")\
                .update({"estado": "vencido"})\
                .eq("usuario_id", usuario_id)\
                .eq("estado", "activo")\
                .execute()

            response = self.client.table("certificados_digitales").insert(certificado_data).execute()
            return response.data[0] if (response and response.data) else None
        except Exception as e:
            logger.error(f"Error al guardar certificado: {e}")
            return None

    def listar_certificados(self, usuario_id: str) -> list[dict]:
        """Devuelve el historial de certificados cargados por el usuario."""
        try:
            res = self.client.table("certificados_digitales")\
                .select("id, alias, estado, fecha_vencimiento, fecha_carga")\
                .eq("usuario_id", usuario_id)\
                .order("fecha_carga", desc=True)\
                .execute()
            return res.data or []
        except Exception as e:
            logger.error(f"Error al listar certificados: {e}")
            return []

    def guardar_boleta(self, boleta_data: dict, contraparte_nombre: str = "") -> dict | None:
        """Inserta una boleta en la tabla principal 'boletas' sanitizando tipos de datos."""
        try:
            payload = dict(boleta_data)

            if isinstance(payload.get("receptor_id"), dict):
                payload["receptor_id"] = payload["receptor_id"].get("id")

            if payload.get("folio_sii") is not None:
                payload["folio_sii"] = str(payload["folio_sii"])

            if not payload.get("certificado_id"):
                payload.pop("certificado_id", None)

            response = self.client.table("boletas").insert(payload).execute()

            if response and response.data:
                boleta_guardada = response.data[0]
                if contraparte_nombre:
                    boleta_guardada["contraparte_nombre"] = contraparte_nombre
                return boleta_guardada

            logger.error(f"[Supabase] Error al insertar boleta. Respuesta vacia con payload: {payload}")
            return None
        except Exception as e:
            logger.error(f"[Supabase] Excepcion critica al insertar boleta: {e}", exc_info=True)
            return None

    def actualizar_estado_boleta(self, boleta_id: str, nuevo_estado: str) -> dict | None:
        """Actualiza el estado de una boleta."""
        try:
            response = self.client.table("boletas").update({"estado": nuevo_estado}).eq("id", boleta_id).execute()
            return response.data[0] if (response and response.data) else None
        except Exception as e:
            logger.error(f"Error al actualizar estado de boleta: {e}")
            return None

    def registrar_evento_historial(self, boleta_id: str, usuario_id: str, tipo_evento: str, detalle: str = "") -> dict | None:
        """Registra un evento en historial_bhe."""
        try:
            payload = {
                "boleta_id": boleta_id,
                "usuario_id": usuario_id,
                "tipo_evento": tipo_evento,
                "detalle": detalle,
            }
            response = self.client.table("historial_bhe").insert(payload).execute()
            return response.data[0] if (response and response.data) else None
        except Exception as e:
            logger.error(f"Error al registrar evento de historial: {e}")
            return None

    def obtener_boletas_por_rol(self, rol: str, usuario_id: str, rut: str = "") -> list[dict]:
        """Recupera las boletas aplicando los permisos estrictos de cada rol."""
        try:
            if rol == "emisor":
                res = self.client.table("boletas")\
                    .select("*, receptores(nombre)")\
                    .eq("usuario_id", usuario_id)\
                    .order("created_at", desc=True)\
                    .execute()
                return [{"contraparte_nombre": r.get("receptores", {}).get("nombre", "Sin Nombre") if r.get("receptores") else "Sin Nombre", **r} for r in (res.data or [])]

            elif rol == "contador":
                res = self.client.table("boletas")\
                    .select("*, receptores(nombre)")\
                    .order("created_at", desc=True)\
                    .execute()
                return [{"contraparte_nombre": r.get("receptores", {}).get("nombre", "Sin Nombre") if r.get("receptores") else "Sin Nombre", **r} for r in (res.data or [])]

            elif rol == "cliente":
                res = self.client.table("boletas")\
                    .select("*, receptores!inner(rut, nombre)")\
                    .eq("receptores.rut", rut)\
                    .order("created_at", desc=True)\
                    .execute()
                return [{"contraparte_nombre": "Mi Empresa / Emisor", **r} for r in (res.data or [])]

            return []
        except Exception as e:
            logger.error(f"Error al consultar boletas por rol: {e}")
            return []

    # --- FUNCIONES DE SUPABASE STORAGE DENTRO DE LA CLASE ---

    def guardar_o_actualizar_pdf_storage(self, folio: int, pdf_bytes: bytes) -> bool:
        """Sube o sobrescribe (upsert) el PDF de una boleta en Supabase Storage."""
        try:
            nombre_archivo = f"boleta_{folio}.pdf"
            self.client.storage.from_("pdf_boletas").upload(
                path=nombre_archivo,
                file=pdf_bytes,
                file_options={"content-type": "application/pdf", "upsert": "true"}
            )
            return True
        except Exception as e:
            logger.error(f"Error al guardar PDF en Storage: {e}")
            return False

    def obtener_url_descarga_segura(self, folio: int) -> str:
        """Genera una URL temporal firmada (3600 seg = 1 hora) para descargar el PDF privado."""
        try:
            nombre_archivo = f"boleta_{folio}.pdf"
            res = self.client.storage.from_("pdf_boletas").create_signed_url(
                path=nombre_archivo, 
                expires_in=3600
            )
            return res.get("signedUrl") if isinstance(res, dict) else res
        except Exception as e:
            logger.error(f"Error al obtener URL firmada: {e}")
            return ""