import logging
from supabase import create_client, Client
from src.config import SUPABASE_URL, SUPABASE_KEY

logger = logging.getLogger(__name__)

class SupabaseService:
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
                logger.warning("Supabase en modo simulación (credenciales pendientes).")
        except Exception as e:
            logger.error(f"Error al conectar con Supabase: {e}")

    def validar_usuario(self, identificador: str) -> dict | None:
        """Valida si el email o RUT existe en la tabla 'perfiles' y retorna su rol."""
        if not self.client:
            # 3 Usuarios de prueba exigidos por el jefe para modo local/offline
            usuarios_mock = {
                "contador@test.com": {"id": "1", "nombre": "Contador Test", "rut": "11.111.111-1", "rol": "contador"},
                "11.111.111-1": {"id": "1", "nombre": "Contador Test", "rut": "11.111.111-1", "rol": "contador"},
                
                "emisor@test.com": {"id": "2", "nombre": "María Emisora", "rut": "22.222.222-2", "rol": "emisor"},
                "22.222.222-2": {"id": "2", "nombre": "María Emisora", "rut": "22.222.222-2", "rol": "emisor"},
                
                "cliente@test.com": {"id": "3", "nombre": "Cliente Receptor", "rut": "33.333.333-3", "rol": "cliente"},
                "33.333.333-3": {"id": "3", "nombre": "Cliente Receptor", "rut": "33.333.333-3", "rol": "cliente"},
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
                    "rol": str(usr.get("rol", "emisor")).lower()
                }
            return None
        except Exception as e:
            logger.error(f"Error al consultar perfiles: {e}")
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

    def guardar_boleta(self, boleta_data: dict) -> dict | None:
        """Inserta una boleta en la tabla principal 'boletas'."""
        if not self.client:
            logger.info(f"[MOCK] Guardando boleta en DB: {boleta_data}")
            return boleta_data

        try:
            response = self.client.table("boletas").insert(boleta_data).execute()
            return response.data
        except Exception as e:
            logger.error(f"Error al insertar boleta: {e}")
            return None

    def obtener_boletas_por_rol(self, rol: str, usuario_id: str, rut: str = "") -> list[dict]:
        """Recupera las boletas aplicando los permisos estrictos de cada rol."""
        if not self.client:
            # Datos simulados para pruebas locales
            return [
                {
                    "numero": 101,
                    "fecha_emision": "2026-08-20",
                    "contraparte_nombre": "Empresa Mock SpA",
                    "monto_total": 500000,
                    "estado": "Vigente"
                }
            ]

        try:
            if rol == "emisor":
                # El emisor solo ve lo que ha emitido él mismo
                res = self.client.table("boletas")\
                    .select("*, receptores(nombre)")\
                    .eq("usuario_id", usuario_id)\
                    .order("fecha_emision", desc=True)\
                    .execute()
                return [{"contraparte_nombre": r.get("receptores", {}).get("nombre", "Sin Nombre"), **r} for r in res.data]

            elif rol == "contador":
                # El contador ve el historial global
                res = self.client.table("boletas")\
                    .select("*, receptores(nombre)")\
                    .order("fecha_emision", desc=True)\
                    .execute()
                return [{"contraparte_nombre": r.get("receptores", {}).get("nombre", "Sin Nombre"), **r} for r in res.data]

            elif rol == "cliente":
                # El cliente solo ve boletas emitidas a su RUT
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