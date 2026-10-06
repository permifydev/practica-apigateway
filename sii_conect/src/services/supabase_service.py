import logging
from datetime import datetime, date
from supabase import Client
from src.config import supabase as _shared_client
from src.utils.crypto_rut import cifrar_rut, descifrar_rut, hash_rut

logger = logging.getLogger(__name__)

def _periodo_a_fecha(periodo) -> str:
    """'YYYYMM' (o 'YYYYMMDD', o una date) -> 'YYYY-MM-01'. Desde la migracion 005
    todas las columnas 'periodo' son date (primer dia del mes)."""
    if isinstance(periodo, date):
        return periodo.replace(day=1).isoformat()
    txt = str(periodo).replace("-", "").strip()
    return f"{txt[0:4]}-{txt[4:6]}-01"


def _fecha_a_iso(valor) -> str | None:
    """Fecha del SII -> 'YYYY-MM-DD' (columna date). Acepta '2026-07-28',
    '28/07/2026', '28-07-2026' o '28 jul 2026'. None si no se reconoce."""
    if not valor:
        return None
    if isinstance(valor, date):
        return valor.isoformat()
    txt = str(valor).strip()
    for formato in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(txt[:10], formato).date().isoformat()
        except ValueError:
            pass
    from src.utils.helpers import parse_fecha_bhe
    f = parse_fecha_bhe(txt)
    return None if f == date.min else f.isoformat()


class SupabaseService:
    def __init__(self):
        # Un solo cliente compartido para toda la app (definido una vez en config.py).
        self.client: Client = _shared_client

    def iniciar_sesion(self, email: str, password: str) -> dict | None:
        """Inicia sesion real contra Supabase Auth. Devuelve {'id', 'email'} del usuario autenticado o None si fallan las credenciales."""
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
        """Trae el perfil del usuario ya autenticado. Requiere sesion activa (RLS: id = auth.uid())."""
        if not self.client:
            return None
        try:
            res = self.client.table("perfiles")\
                .select("id, nombre_completo, rut_cifrado, rol, email")\
                .eq("id", usuario_id)\
                .execute()
            if res.data:
                usr = res.data[0]
                return {
                    "id": usr["id"],
                    "nombre": usr.get("nombre_completo", "Usuario"),
                    "rut": descifrar_rut(usr.get("rut_cifrado")),
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
        """Busca un receptor por RUT (via rut_hash, sin descifrar nada) o lo crea si no
        existe. Garantiza devolver un dict con clave 'id' y 'rut' en texto plano."""
        try:
            rut_clean = rut.strip()
            rut_h = hash_rut(rut_clean)
            res = self.client.table("receptores").select("id, nombre, rut_cifrado").eq("rut_hash", rut_h).execute()
            if res.data:
                fila = res.data[0]
                return {"id": fila["id"], "nombre": fila["nombre"], "rut": descifrar_rut(fila.get("rut_cifrado")) or rut_clean}

            payload = {
                "rut_hash": rut_h,
                "rut_cifrado": cifrar_rut(rut_clean),
                "nombre": nombre.strip(),
            }
            if email:
                payload["email"] = email.strip()
            if usuario_id:
                payload["usuario_id"] = usuario_id

            nuevo = self.client.table("receptores").insert(payload).execute()
            if nuevo and nuevo.data:
                fila = nuevo.data[0]
                return {"id": fila["id"], "nombre": fila.get("nombre"), "rut": rut_clean}
            return None
        except Exception as e:
            logger.error(f"Error en obtener_o_crear_receptor: {e}")
            return None

    def listar_receptores(self, usuario_id: str) -> list[dict]:
        """Receptores DEL USUARIO, con el RUT ya descifrado.

        La tabla 'receptores' es un directorio global (cada RUT se guarda una sola
        vez y lo comparten todos, para no duplicar). Pero cada usuario solo debe
        ver los suyos: los que registro el mismo (usuario_id) y aquellos a los que
        ya les emitio alguna boleta (boletas.receptor_id). Antes se mostraba el
        directorio completo y un usuario veia los receptores de otro."""
        try:
            propios = self.client.table("receptores").select("id")\
                .eq("usuario_id", usuario_id).execute().data or []
            usados = self.client.table("boletas").select("receptor_id")\
                .eq("usuario_id", usuario_id).execute().data or []
            ids = {r["id"] for r in propios} | {b["receptor_id"] for b in usados if b.get("receptor_id")}
            if not ids:
                return []
            res = self.client.table("receptores").select("id, rut_cifrado, nombre, email")\
                .in_("id", list(ids)).order("nombre").execute()
            receptores = []
            for r in (res.data or []):
                fila = dict(r)
                fila["rut"] = descifrar_rut(fila.pop("rut_cifrado", None)) or "---"
                receptores.append(fila)
            return receptores
        except Exception as e:
            logger.error(f"Error al listar receptores: {e}")
            return []

    def crear_receptor(self, rut: str, nombre: str, email: str = "", usuario_id: str | None = None) -> dict | None:
        """Crea un receptor nuevo, guardando el RUT cifrado (mas su hash para buscarlo).
        Si ese RUT ya existe en el directorio global (lo registro otro usuario), no
        lo duplica: devuelve el existente."""
        try:
            rut_clean = rut.strip()
            existente = self.client.table("receptores").select("id, nombre, email")\
                .eq("rut_hash", hash_rut(rut_clean)).execute().data
            if existente:
                fila = dict(existente[0])
                fila["rut"] = rut_clean
                return fila
            payload = {"rut_hash": hash_rut(rut_clean), "rut_cifrado": cifrar_rut(rut_clean), "nombre": nombre.strip()}
            if email:
                payload["email"] = email.strip()
            if usuario_id:
                payload["usuario_id"] = usuario_id

            response = self.client.table("receptores").insert(payload).execute()
            if response and response.data:
                fila = dict(response.data[0])
                fila["rut"] = rut_clean
                return fila
            return None
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

            # Sanitizacion 1: Si receptor_id vino como diccionario completo, extraer solo el string ID
            if isinstance(payload.get("receptor_id"), dict):
                payload["receptor_id"] = payload["receptor_id"].get("id")

            # Sanitizacion 2: Asegurar que folio_sii sea string
            if payload.get("folio_sii") is not None:
                payload["folio_sii"] = str(payload["folio_sii"])

            # Sanitizacion 3: Si certificado_id es None o vacio, eliminarlo para no violar constraints NULL en Postgres
            if not payload.get("certificado_id"):
                payload.pop("certificado_id", None)

            # Sanitizacion 4: el RUT emisor se guarda cifrado, nunca en texto plano
            if payload.get("rut_emisor"):
                payload["rut_emisor_cifrado"] = cifrar_rut(payload.pop("rut_emisor"))

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

    def subir_pdf_boleta(self, usuario_id: str, folio: str, pdf_bytes: bytes) -> str | None:
        """Sube el PDF de una boleta al bucket privado 'pdf_boletas', dentro de una
        carpeta por usuario (asi las politicas de RLS pueden restringir cada quien
        a lo suyo), y devuelve una URL firmada (valida 1 hora) para abrirlo.
        Si algo falla (bucket sin politicas, sin sesion, etc.) devuelve None y
        quien llama puede recurrir al guardado local como respaldo."""
        try:
            ruta = f"{usuario_id}/{folio}.pdf"
            self.client.storage.from_("pdf_boletas").upload(
                path=ruta,
                file=pdf_bytes,
                file_options={"content-type": "application/pdf", "upsert": "true"},
            )
            firmada = self.client.storage.from_("pdf_boletas").create_signed_url(
                ruta, 3600, {"download": f"boleta_{folio}.pdf"}
            )
            return firmada.get("signedURL") or firmada.get("signedUrl") or firmada.get("signed_url")
        except Exception as e:
            logger.error(f"Error al subir PDF a Supabase Storage: {e}")
            return None

    def _firmar_urls_pdf(self, usuario_id: str, folio: str) -> dict | None:
        """Devuelve dos URLs firmadas (1 hora) del mismo PDF: 'ver' (se abre en el
        navegador) y 'descarga' (fuerza la descarga con nombre boleta_<folio>.pdf)."""
        bucket = self.client.storage.from_("pdf_boletas")
        ruta = f"{usuario_id}/{folio}.pdf"

        def extraer(r):
            return r.get("signedURL") or r.get("signedUrl") or r.get("signed_url")

        ver = extraer(bucket.create_signed_url(ruta, 3600))
        descarga = extraer(bucket.create_signed_url(ruta, 3600, {"download": f"boleta_{folio}.pdf"}))
        return {"ver": ver, "descarga": descarga} if (ver and descarga) else None

    def subir_pdf_boleta_urls(self, usuario_id: str, folio: str, pdf_bytes: bytes) -> dict | None:
        """Igual que subir_pdf_boleta, pero devuelve {'ver': url, 'descarga': url}."""
        try:
            self.client.storage.from_("pdf_boletas").upload(
                path=f"{usuario_id}/{folio}.pdf",
                file=pdf_bytes,
                file_options={"content-type": "application/pdf", "upsert": "true"},
            )
            return self._firmar_urls_pdf(usuario_id, folio)
        except Exception as e:
            logger.error(f"Error al subir PDF a Supabase Storage: {e}")
            return None

    def urls_pdf_boleta(self, usuario_id: str, folio: str) -> dict | None:
        """Si el PDF de este folio YA esta guardado en Supabase, devuelve sus URLs
        firmadas sin volver a llamar al SII (ahorra creditos). Si no existe, None."""
        try:
            archivos = self.client.storage.from_("pdf_boletas").list(
                usuario_id, {"search": f"{folio}.pdf"}
            )
            if not any(a.get("name") == f"{folio}.pdf" for a in (archivos or [])):
                return None
            return self._firmar_urls_pdf(usuario_id, folio)
        except Exception as e:
            logger.warning(f"No se pudo consultar el PDF en Supabase Storage: {e}")
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

    # ------------------------------------------------------------------
    # Solicitudes de BHE (migracion 007): la EMPRESA le pide al USUARIO
    # (emisor) que emita una BHE por lo que le corresponde de sus ventas.
    # Los montos los calcula la BD (trigger calcular_solicitud_bhe) y la
    # notificacion + el correo en cola los crea otro trigger
    # (avisar_solicitud_bhe). Aca solo se indica empresa, usuario y mes.
    # ------------------------------------------------------------------
    def enviar_solicitud_bhe(self, empresa_id: str, emisor_id: str, anio: int, mes: int) -> tuple[bool, str]:
        """Crea la solicitud. Devuelve (ok, mensaje para mostrar)."""
        try:
            self.client.table("solicitudes_bhe").insert({
                "empresa_id": empresa_id,
                "emisor_id": emisor_id,
                "periodo": date(anio, mes, 1).isoformat(),
            }).execute()
            return True, "Solicitud enviada."
        except Exception as e:
            texto = str(e)
            logger.error(f"Error al enviar solicitud de BHE: {texto}")
            if "duplicate key" in texto or "23505" in texto:
                return False, "Ya se envio una solicitud a este usuario para este mes."
            if "no tiene ventas" in texto:
                return False, "El usuario no tiene ventas registradas en este mes."
            return False, "No se pudo enviar la solicitud. Intenta nuevamente."

    # ------------------------------------------------------------------
    # Notificaciones en la app (migracion 007)
    # ------------------------------------------------------------------
    def contar_notificaciones_no_leidas(self, usuario_id: str) -> int:
        try:
            res = self.client.table("notificaciones")\
                .select("id", count="exact")\
                .eq("usuario_id", usuario_id)\
                .eq("leida", False)\
                .execute()
            return res.count or 0
        except Exception as e:
            logger.warning(f"No se pudieron contar las notificaciones: {e}")
            return 0

    def listar_notificaciones(self, usuario_id: str) -> list[dict]:
        """Notificaciones del usuario, mas recientes primero, con el detalle de la
        solicitud y de la empresa (RUT ya descifrado) para poder emitir la BHE."""
        try:
            res = self.client.table("notificaciones")\
                .select("id, titulo, mensaje, leida, created_at, "
                        "solicitudes_bhe(periodo, monto_ventas, comision_pct, monto_comision, "
                        "monto_a_pagar, estado, empresas(nombre, rut_cifrado, direccion))")\
                .eq("usuario_id", usuario_id)\
                .order("created_at", desc=True)\
                .execute()
            salida = []
            for r in (res.data or []):
                fila = dict(r)
                sol = fila.pop("solicitudes_bhe", None) or {}
                if isinstance(sol, list):
                    sol = sol[0] if sol else {}
                emp = sol.pop("empresas", None) or {}
                if isinstance(emp, list):
                    emp = emp[0] if emp else {}
                fila["solicitud"] = sol
                fila["empresa"] = {
                    "nombre": emp.get("nombre"),
                    "rut": descifrar_rut(emp.get("rut_cifrado")),
                    "direccion": emp.get("direccion"),
                }
                salida.append(fila)
            return salida
        except Exception as e:
            logger.error(f"Error al listar notificaciones: {e}")
            return []

    def marcar_notificacion_leida(self, notificacion_id: str) -> bool:
        try:
            self.client.table("notificaciones").update({"leida": True}).eq("id", notificacion_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error al marcar notificacion como leida: {e}")
            return False



    def obtener_mi_empresa(self, usuario_id: str) -> dict | None:
        """Empresa a la que pertenece el usuario logueado (perfiles.empresa_id ->
        empresas). Devuelve {'id','nombre','rut','direccion','comision_pct'} o None
        si el perfil todavia no tiene empresa asignada. Requiere la migracion 004."""
        try:
            res = self.client.table("perfiles")\
                .select("empresa_id, empresas(id, nombre, rut_cifrado, direccion, comision_pct)")\
                .eq("id", usuario_id)\
                .execute()
            if not res.data:
                return None
            emp = res.data[0].get("empresas")
            if isinstance(emp, list):
                emp = emp[0] if emp else None
            if not emp:
                return None
            emp = dict(emp)
            emp["rut"] = descifrar_rut(emp.pop("rut_cifrado", None))
            return emp
        except Exception as e:
            logger.error(f"Error al obtener empresa del usuario: {e}")
            return None

    def resumen_ingresos_mes(self, empresa_id: str, anio: int, mes: int) -> list[dict]:
        """Ventas del mes por usuario para la empresa, con comision y monto para el
        usuario ya calculados (vista v_resumen_ingresos). Solo lee Supabase: NO
        llama al SII y no gasta creditos."""
        try:
            periodo = date(anio, mes, 1).isoformat()
            res = self.client.table("v_resumen_ingresos")\
                .select("emisor_id, usuario_nombre, usuario_email, total_ventas, comision_pct, comision, "
                        "monto_usuario, estado_solicitud, solicitud_fecha")\
                .eq("empresa_id", empresa_id)\
                .eq("periodo", periodo)\
                .order("usuario_nombre")\
                .execute()
            return res.data or []
        except Exception as e:
            logger.error(f"Error al obtener resumen de ingresos: {e}")
            return []


    def obtener_boletas_por_rol(self, rol: str, usuario_id: str, rut: str = "") -> list[dict]:
        """Recupera las boletas aplicando los permisos estrictos de cada rol."""
        def _preparar(filas):
            salida = []
            for r in filas:
                fila = dict(r)
                fila["rut_emisor"] = descifrar_rut(fila.pop("rut_emisor_cifrado", None))
                salida.append(fila)
            return salida

        try:
            if rol == "emisor":
                res = self.client.table("boletas")\
                    .select("*, receptores(nombre)")\
                    .eq("usuario_id", usuario_id)\
                    .order("fecha_emision", desc=True)\
                    .execute()
                return _preparar([{"contraparte_nombre": r.get("receptores", {}).get("nombre", "Sin Nombre") if r.get("receptores") else "Sin Nombre", **r} for r in (res.data or [])])

            elif rol == "contador":
                res = self.client.table("boletas")\
                    .select("*, receptores(nombre)")\
                    .order("fecha_emision", desc=True)\
                    .execute()
                return _preparar([{"contraparte_nombre": r.get("receptores", {}).get("nombre", "Sin Nombre") if r.get("receptores") else "Sin Nombre", **r} for r in (res.data or [])])

            elif rol == "cliente":
                res = self.client.table("boletas")\
                    .select("*, receptores!inner(rut_hash, nombre)")\
                    .eq("receptores.rut_hash", hash_rut(rut))\
                    .order("fecha_emision", desc=True)\
                    .execute()
                return _preparar([{"contraparte_nombre": "Mi Empresa / Emisor", **r} for r in (res.data or [])])

            return []
        except Exception as e:
            logger.error(f"Error al consultar boletas por rol: {e}")
            return []