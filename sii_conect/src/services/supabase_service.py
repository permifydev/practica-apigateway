import logging
from datetime import datetime, date
from supabase import create_client, Client
from src.config import SUPABASE_URL, SUPABASE_KEY

logger = logging.getLogger(__name__)

class SupabaseService:
    # Almacenamiento en memoria usado solo cuando no hay conexion real a Supabase.
    _mock_boletas = [
        {
            "id": "mock-101",
            "folio_sii": "101",
            "fecha_emision": "2026-08-20",
            "contraparte_nombre": "Empresa Mock SpA",
            "monto_bruto": 500000,
            "monto_liquido": 423750,
            "estado": "pendiente",
        }
    ]
    _mock_folio_counter = {"value": 1204}
    _mock_historial = []
    _mock_receptores = [
        {"id": "mock-r1", "rut": "76.111.222-3", "nombre": "Tech Solutions SPA", "email": "contacto@tech.cl"},
    ]

    def __init__(self, url: str = SUPABASE_URL, key: str = SUPABASE_KEY):
        self.url = url
        self.key = key
        self.client: Client | None = None
        self._conectar()

    def _conectar(self):
        try:
            if self.url and self.key and "tu-proyecto" not in self.url:
                self.client = create_client(self.url, self.key)
            else:
                logger.warning("Supabase en modo simulacion (credenciales pendientes).")
        except Exception as e:
            logger.error(f"Error al conectar con Supabase: {e}")

    def validar_usuario(self, identificador: str) -> dict | None:
        """Valida si el email o RUT existe en la tabla 'perfiles' y retorna su rol."""
        if not self.client:
            usuarios_mock = {
                "contador@test.com": {"id": "1", "nombre": "Contador Test", "rut": "11.111.111-1", "rol": "contador", "email": "contador@test.com"},
                "11.111.111-1": {"id": "1", "nombre": "Contador Test", "rut": "11.111.111-1", "rol": "contador", "email": "contador@test.com"},

                "emisor@test.com": {"id": "2", "nombre": "Maria Emisora", "rut": "22.222.222-2", "rol": "emisor", "email": "emisor@test.com"},
                "22.222.222-2": {"id": "2", "nombre": "Maria Emisora", "rut": "22.222.222-2", "rol": "emisor", "email": "emisor@test.com"},

                "cliente@test.com": {"id": "3", "nombre": "Cliente Receptor", "rut": "33.333.333-3", "rol": "cliente", "email": "cliente@test.com"},
                "33.333.333-3": {"id": "3", "nombre": "Cliente Receptor", "rut": "33.333.333-3", "rol": "cliente", "email": "cliente@test.com"},
            }
            return usuarios_mock.get(identificador.strip().lower())

        try:
            res = self.client.table("perfiles")\
                .select("id, nombre_completo, rut, rol, email")\
                .or_(f"email.eq.{identificador},rut.eq.{identificador}")\
                .execute()

            if res.data:
                usr = res.data[0]
                return {
                    "id": usr["id"],
                    "nombre": usr.get("nombre_completo", "Usuario"),
                    "rut": usr.get("rut"),
                    "rol": str(usr.get("rol", "emisor")).lower(),
                    "email": usr.get("email"),
                }
            return None
        except Exception as e:
            logger.error(f"Error al consultar perfiles: {e}")
            return None

    def actualizar_perfil(self, usuario_id: str, email: str) -> dict | None:
        """Actualiza el correo de contacto del perfil. RUT y rol no son editables desde la app."""
        if not self.client:
            logger.info(f"[MOCK] Actualizando perfil {usuario_id} con email {email}")
            return {"id": usuario_id, "email": email}

        try:
            response = self.client.table("perfiles").update({"email": email}).eq("id", usuario_id).execute()
            return response.data
        except Exception as e:
            logger.error(f"Error al actualizar perfil: {e}")
            return None

    def obtener_o_crear_receptor(self, rut: str, nombre: str, email: str = "") -> dict | str | None:
        """Busca un receptor por RUT o lo crea si no existe."""
        if not self.client:
            return {"id": "mock-uuid-receptor", "nombre": nombre, "rut": rut}

        try:
            res = self.client.table("receptores").select("id, nombre, rut").eq("rut", rut).execute()
            if res.data:
                return res.data[0]

            nuevo = self.client.table("receptores").insert({
                "rut": rut,
                "nombre": nombre,
                "email": email
            }).execute()
            return nuevo.data[0] if nuevo.data else None
        except Exception as e:
            logger.error(f"Error en receptor: {e}")
            return None

    def listar_receptores(self) -> list[dict]:
        """Devuelve todos los receptores registrados (contrapartes usadas al emitir BHE)."""
        if not self.client:
            return list(SupabaseService._mock_receptores)

        try:
            res = self.client.table("receptores").select("id, rut, nombre, email").order("nombre").execute()
            return res.data
        except Exception as e:
            logger.error(f"Error al listar receptores: {e}")
            return []

    def crear_receptor(self, rut: str, nombre: str, email: str = "") -> dict | None:
        """Crea un receptor nuevo (sin buscar duplicados primero, a diferencia de obtener_o_crear_receptor)."""
        if not self.client:
            nuevo = {"id": f"mock-r{len(SupabaseService._mock_receptores) + 1}", "rut": rut, "nombre": nombre, "email": email}
            SupabaseService._mock_receptores.append(nuevo)
            return nuevo

        try:
            response = self.client.table("receptores").insert({"rut": rut, "nombre": nombre, "email": email}).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error al crear receptor: {e}")
            return None

    def actualizar_receptor(self, receptor_id: str, nombre: str, email: str = "") -> dict | None:
        """Actualiza nombre y correo de un receptor existente."""
        if not self.client:
            for r in SupabaseService._mock_receptores:
                if r.get("id") == receptor_id:
                    r["nombre"] = nombre
                    r["email"] = email
                    return r
            return None

        try:
            response = self.client.table("receptores").update({"nombre": nombre, "email": email}).eq("id", receptor_id).execute()
            return response.data
        except Exception as e:
            logger.error(f"Error al actualizar receptor: {e}")
            return None

    def obtener_certificado_activo(self, usuario_id: str) -> dict | None:
        """Devuelve el certificado digital vigente del usuario, si tiene uno. No incluye credenciales SII: esas no se persisten."""
        if not self.client:
            return {
                "id": "mock-uuid-certificado",
                "alias": "Certificado de prueba",
                "archivo_path": None,
                "fecha_vencimiento": None,
                "estado": "activo",
            }

        try:
            res = self.client.table("certificados_digitales")\
                .select("id, alias, archivo_path, fecha_carga, fecha_vencimiento, estado")\
                .eq("usuario_id", usuario_id)\
                .eq("estado", "activo")\
                .order("fecha_vencimiento", desc=True)\
                .limit(1)\
                .execute()
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error(f"Error al consultar certificado activo: {e}")
            return None

    def guardar_certificado(self, certificado_data: dict) -> dict | None:
        """Inserta un registro de certificado (metadatos, no credenciales)."""
        if not self.client:
            logger.info(f"[MOCK] Guardando certificado en DB: {certificado_data}")
            return certificado_data

        try:
            usuario_id = certificado_data.get("usuario_id")

            self.client.table("certificados_digitales")\
                .update({"estado": "vencido"})\
                .eq("usuario_id", usuario_id)\
                .eq("estado", "activo")\
                .execute()

            response = self.client.table("certificados_digitales").insert(certificado_data).execute()
            return response.data
        except Exception as e:
            logger.error(f"Error al guardar certificado: {e}")
            return None

    def listar_certificados(self, usuario_id: str) -> list[dict]:
        """Devuelve el historial de certificados cargados por el usuario."""
        if not self.client:
            return [{"id": "mock-uuid-certificado", "alias": "Certificado de prueba", "estado": "activo"}]

        try:
            res = self.client.table("certificados_digitales")\
                .select("id, alias, estado, fecha_vencimiento, fecha_carga")\
                .eq("usuario_id", usuario_id)\
                .order("fecha_carga", desc=True)\
                .execute()
            return res.data
        except Exception as e:
            logger.error(f"Error al listar certificados: {e}")
            return []

    def guardar_boleta(self, boleta_data: dict, contraparte_nombre: str = "") -> dict | None:
        """Inserta una boleta en la tabla principal 'boletas'."""
        if not self.client:
            SupabaseService._mock_folio_counter["value"] += 1
            folio_generado = boleta_data.get("folio_sii") or SupabaseService._mock_folio_counter["value"]

            boleta_mock = {
                **boleta_data,
                "id": f"mock-{folio_generado}",
                "folio_sii": folio_generado,
                "contraparte_nombre": contraparte_nombre or "Receptor sin nombre",
            }
            logger.info(f"[MOCK] Guardando boleta en DB: {boleta_mock}")
            SupabaseService._mock_boletas.insert(0, boleta_mock)
            return boleta_mock

        try:
            response = self.client.table("boletas").insert(boleta_data).execute()
            return response.data
        except Exception as e:
            logger.error(f"Error al insertar boleta: {e}")
            return None

    def actualizar_estado_boleta(self, boleta_id: str, nuevo_estado: str) -> dict | None:
        """Actualiza el estado de una boleta (debe ser un valor valido del enum estado_boleta)."""
        if not self.client:
            for b in SupabaseService._mock_boletas:
                if b.get("id") == boleta_id:
                    b["estado"] = nuevo_estado
                    logger.info(f"[MOCK] Actualizando boleta {boleta_id} a estado {nuevo_estado}")
                    return b
            return None

        try:
            response = self.client.table("boletas").update({"estado": nuevo_estado}).eq("id", boleta_id).execute()
            return response.data
        except Exception as e:
            logger.error(f"Error al actualizar estado de boleta: {e}")
            return None

    def registrar_evento_historial(self, boleta_id: str, usuario_id: str, tipo_evento: str, detalle: str = "") -> dict | None:
        """Registra un evento (emision, pago, anulacion, consulta_sii) en historial_bhe."""
        if not self.client:
            evento_mock = {
                "id": f"mock-evento-{len(SupabaseService._mock_historial) + 1}",
                "boleta_id": boleta_id,
                "usuario_id": usuario_id,
                "tipo_evento": tipo_evento,
                "detalle": detalle,
                "fecha": datetime.now().isoformat(),
            }
            SupabaseService._mock_historial.append(evento_mock)
            logger.info(f"[MOCK] Evento historial registrado: {evento_mock}")
            return evento_mock

        try:
            payload = {
                "boleta_id": boleta_id,
                "usuario_id": usuario_id,
                "tipo_evento": tipo_evento,
                "detalle": detalle,
            }
            response = self.client.table("historial_bhe").insert(payload).execute()
            return response.data
        except Exception as e:
            logger.error(f"Error al registrar evento de historial: {e}")
            return None

    def obtener_boletas_por_rol(self, rol: str, usuario_id: str, rut: str = "") -> list[dict]:
        """Recupera las boletas aplicando los permisos estrictos de cada rol."""
        if not self.client:
            return list(SupabaseService._mock_boletas)

        try:
            if rol == "emisor":
                res = self.client.table("boletas")\
                    .select("*, receptores(nombre)")\
                    .eq("usuario_id", usuario_id)\
                    .order("fecha_emision", desc=True)\
                    .execute()
                return [{"contraparte_nombre": r.get("receptores", {}).get("nombre", "Sin Nombre"), **r} for r in res.data]

            elif rol == "contador":
                res = self.client.table("boletas")\
                    .select("*, receptores(nombre)")\
                    .order("fecha_emision", desc=True)\
                    .execute()
                return [{"contraparte_nombre": r.get("receptores", {}).get("nombre", "Sin Nombre"), **r} for r in res.data]

            elif rol == "cliente":
                res = self.client.table("boletas")\
                    .select("*, receptores!inner(rut, nombre)")\
                    .eq("receptores.rut", rut)\
                    .order("fecha_emision", desc=True)\
                    .execute()
                return [{"contraparte_nombre": "Mi Empresa / Emisor", **r} for r in res.data]

            return []
        except Exception as e:
            logger.error(f"Error al consultar boletas por rol: {e}")
            return []