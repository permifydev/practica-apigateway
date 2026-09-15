import logging
import random
from datetime import datetime
import requests
from src.config import APIGATEWAY_BASE_URL, APIGATEWAY_TOKEN, MOCK_MODE, PROXY_URL

logger = logging.getLogger(__name__)

class ApiGatewayError(Exception):
    def __init__(self, message: str, status_code: int | None = None, payload: dict | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload

class ApiGatewayClient:
    def __init__(self, token: str = APIGATEWAY_TOKEN, base_url: str = APIGATEWAY_BASE_URL,
                 mock: bool = MOCK_MODE, proxy_url: str | None = PROXY_URL):
        self.token = token
        self.base_url = base_url.rstrip("/") if base_url else "https://app.apigateway.cl"
        self.mock = mock
        self.proxy_url = proxy_url
        self.session = requests.Session()

        # apigateway.cl solo permite consultas desde la IP fija del proxy Squid (Lightsail).
        # Sin esto, las peticiones salen con la IP real de la maquina/servidor (ej. la IP
        # dinamica de Render), que no esta registrada ni tiene creditos asociados, y
        # apigateway.cl responde con "Creditos insuficientes ... la IP de origen esta en
        # uso por otra conexion sin creditos". No se aplica en modo mock porque ahi no
        # se hace ninguna llamada de red real.
        if self.proxy_url and not self.mock:
            self.session.proxies = {"http": self.proxy_url, "https": self.proxy_url}
            logger.info("Proxy Squid configurado para las llamadas a apigateway.cl")
        elif not self.mock:
            logger.warning(
                "MOCK_MODE=False pero no hay PROXY_URL configurado: las llamadas a "
                "apigateway.cl saldran con la IP directa de este servidor, lo que "
                "probablemente sea rechazado si esa IP no esta registrada."
            )

    def _headers(self) -> dict:
        return {
            "Authorization": f"Token {self.token}",
            "Content-Type": "application/json",
        }

    def _auth_block(self, rut: str, clave: str) -> dict:
        return {"auth": {"pass": {"rut": rut, "clave": clave}}}

    def _parse_response(self, response):
        try:
            return response.json()
        except ValueError:
            raise ApiGatewayError(
                f"Respuesta no-JSON de API Gateway (status {response.status_code})",
                status_code=response.status_code,
            )

    def _post_con_reintento_sesion(self, url: str, body: dict, params: dict | None = None):
        params = dict(params or {})
        response = self.session.post(url, params=params, json=body, headers=self._headers(), timeout=20)

        if response.headers.get("X-Auth-Session-Problem") == "1":
            logger.info("X-Auth-Session-Problem=1 recibido, reintentando con auth_cache=0")
            params_reintento = dict(params)
            params_reintento["auth_cache"] = 0
            response = self.session.post(url, params=params_reintento, json=body, headers=self._headers(), timeout=20)

        return response

    def _handle_pdf_response(self, response) -> dict:
        """Los recursos de PDF del SII no siempre devuelven el mismo formato: puede venir
        el binario directo (Content-Type application/pdf) o un JSON con datos/errores.
        Normaliza ambos casos a {"pdf_bytes": bytes|None, "data": dict|None} para que
        la interfaz no tenga que asumir un formato fijo."""
        if not response.ok:
            try:
                payload = self._parse_response(response)
            except ApiGatewayError:
                payload = None
            raise ApiGatewayError(
                f"Error {response.status_code} al obtener PDF",
                status_code=response.status_code,
                payload=payload,
            )

        content_type = response.headers.get("Content-Type", "")
        if "application/pdf" in content_type:
            return {"pdf_bytes": response.content, "data": None}
        return {"pdf_bytes": None, "data": self._parse_response(response)}

    def _log_stats(self, response):
        creditos = response.headers.get("X-Stats-Credits-Remaining")
        restantes_minuto = response.headers.get("X-RateLimit-Remaining")
        if creditos is not None:
            logger.info(f"Creditos restantes en la conexion: {creditos}")
        if restantes_minuto is not None:
            logger.info(f"Peticiones restantes este minuto: {restantes_minuto}")

    # ---------------- BHE Emitidas ----------------

    def _normalizar_respuesta_emision(self, data: dict) -> dict:
        """La API real devuelve la boleta en el formato oficial del SII, anidado en
        Encabezado/IdDoc/Detalle (confirmado con la prueba en Postman). Esta funcion
        lo aplana a las mismas claves que ya usa el resto de la app en modo mock
        (folio, estado, fecha_emision, etc.) para no tener que tocar las vistas.

        OJO: 'codigo' se usa despues para pedir el PDF (descargar_pdf) y enviar el
        email (enviar_email); en la respuesta real no vino un campo 'codigo' plano,
        se esta usando CodigoInferior como mejor candidato. Hay que confirmar con la
        documentacion o con una prueba real de descargar_pdf/enviar_email si es el
        valor correcto, o si en realidad corresponde a CodigoBarras.
        """
        encabezado = data.get("Encabezado", {}) or {}
        id_doc = encabezado.get("IdDoc", {}) or {}
        emisor = encabezado.get("Emisor", {}) or {}
        receptor = encabezado.get("Receptor", {}) or {}
        detalle = data.get("Detalle", []) or []
        monto_bruto = sum(item.get("MontoItem", 0) for item in detalle)

        return {
            "folio": id_doc.get("Folio"),
            "codigo": id_doc.get("CodigoInferior") or id_doc.get("CodigoBarras"),
            "estado": "EMITIDA",  # la API real no devuelve un campo de estado al emitir;
                                  # si la respuesta llego OK (sin excepcion), se asume emitida
            "fecha_emision": id_doc.get("FchEmis"),
            "rut_emisor": emisor.get("RUTEmisor"),
            "rut_receptor": receptor.get("RUTRecep"),
            "monto_bruto": monto_bruto,
            "pdf_url": None,  # no viene en la respuesta de emision, se pide aparte con descargar_pdf
            "codigo_verificacion": id_doc.get("CodigoBarras"),
            "raw": data,  # respuesta completa del SII por si se necesita mas adelante
        }

    def emitir_boleta(self, rut: str, clave: str, boleta_payload: dict) -> dict:
        """Emite boleta. En modo simulación (mock=True), genera un folio ficticio sin llamar a la red."""
        if self.mock:
            folio_falso = random.randint(100, 9999)
            logger.info(f"[MODO MOCK] Simulando emisión de boleta Folio {folio_falso}")

            monto_bruto = sum(item.get("MontoItem", 0) for item in boleta_payload.get("Detalle", []))

            return {
                "folio": folio_falso,
                "codigo": f"COD-{folio_falso}",
                "estado": "EMITIDA",
                "fecha_emision": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "rut_emisor": rut,
                "rut_receptor": boleta_payload.get("Encabezado", {}).get("Receptor", {}).get("RUTRecep", ""),
                "monto_bruto": monto_bruto,
                "pdf_url": f"https://apigateway.cl/mock/pdf/{folio_falso}.pdf",
                "codigo_verificacion": f"MOCK-{folio_falso}-TEST"
            }

        url = f"{self.base_url}/api/v2/sii/bhe/emitidas/emitir"
        body = self._auth_block(rut, clave)
        body["boleta"] = boleta_payload

        try:
            response = self._post_con_reintento_sesion(url, body)
            self._log_stats(response)
            if not response.ok:
                raise ApiGatewayError(
                    f"Error {response.status_code} de API Gateway",
                    status_code=response.status_code,
                    payload=self._parse_response(response)
                )
            res_json = self._parse_response(response)
            data = res_json.get("data", res_json)
            return self._normalizar_respuesta_emision(data)
        except requests.RequestException as e:
            raise ApiGatewayError(f"Error de conexión con apigateway.cl: {str(e)}")

    def _normalizar_respuesta_listado(self, data: dict, pagina_solicitada: int) -> dict:
        """La API real devuelve las boletas dentro de 'data' con nombres de campo propios
        del SII (numero, total_honorarios) en vez de los que usa el resto de la app
        (folio, monto_bruto), confirmado con la prueba real en Postman. Se agregan
        alias con los nombres esperados sin perder los campos originales, para no
        romper nada que ya lea los nombres crudos del SII (ej. 'estado': 'S').

        OJO: 'n_paginas' en la respuesta real es el TOTAL de paginas disponibles, no la
        pagina actual (a diferencia del mock, que devolvia 'pagina' como la pagina
        pedida). Se devuelven ambos valores por separado para no confundirlos.
        """
        boletas_raw = data.get("boletas", []) or []
        boletas = [
            {
                **b,
                "folio": b.get("numero"),
                "monto_bruto": b.get("total_honorarios"),
            }
            for b in boletas_raw
        ]
        return {
            "boletas": boletas,
            "n_boletas": data.get("n_boletas"),
            "n_paginas": data.get("n_paginas"),
            "pagina": pagina_solicitada,
            "raw": data,
        }

    def listar_emitidas(self, rut: str, clave: str, emisor: str, periodo: str, pagina: int = 1) -> dict:
        """Lista boletas emitidas por el RUT emisor en un periodo (YYYYMM o YYYYMMDD).
        Util para reconciliar el registro local (Supabase) contra el estado oficial en el SII:
        por ejemplo detectar boletas anuladas directamente en el portal del SII, o folios
        emitidos que no llegaron a guardarse localmente por un error de red."""
        if self.mock:
            return {
                "boletas": [
                    {
                        "folio": 1204, "codigo": "COD-1204", "fecha": "2026-08-20",
                        "receptor": "76192083-9", "razon_social_receptor": "Consultora Mock SpA",
                        "monto_bruto": 500000, "monto_retencion": 76250, "monto_liquido": 423750,
                        "estado": "N",
                    },
                ],
                "pagina": pagina,
            }

        url = f"{self.base_url}/api/v2/sii/bhe/emitidas/documentos/{emisor}/{periodo}"
        body = self._auth_block(rut, clave)

        try:
            response = self._post_con_reintento_sesion(url, body, params={"pagina": pagina})
            self._log_stats(response)
            if not response.ok:
                raise ApiGatewayError(
                    f"Error {response.status_code} al listar boletas emitidas",
                    status_code=response.status_code,
                    payload=self._parse_response(response)
                )
            res_json = self._parse_response(response)
            data = res_json.get("data", res_json)
            return self._normalizar_respuesta_listado(data, pagina_solicitada=pagina)
        except requests.RequestException as e:
            raise ApiGatewayError(f"Error de conexión con apigateway.cl: {str(e)}")

    def _normalizar_respuesta_anulacion(self, data: dict, folio: str) -> dict:
        """La API real no devuelve un campo 'estado' plano ni 'folio' al anular (confirmado
        con la prueba real en Postman): trae 'boleta_anulada' con un codigo de SII
        ('E' en la prueba realizada) y 'fecha_cgi' como fecha del tramite. Se traduce a
        las mismas claves que ya usa el resto de la app (estado, folio, mensaje).

        OJO: solo se confirmo el codigo 'E' (anulacion exitosa). Si en el futuro el SII
        devuelve otro codigo en 'boleta_anulada' para casos borde, hay que agregarlo al
        mapa de abajo; por ahora, cualquier respuesta con response.ok=True que no sea 'E'
        se sigue marcando como ANULADA (la llamada ya se valido como exitosa antes de
        llegar aca) pero queda registrada en 'raw' por si hay que revisarla.
        """
        codigo_anulacion = data.get("boleta_anulada")
        return {
            "folio": folio,
            "estado": "ANULADA",
            "mensaje": f"Boleta anulada correctamente (SII, {data.get('fecha_cgi', 'fecha no informada')})",
            "codigo_anulacion_sii": codigo_anulacion,
            "raw": data,
        }

    def anular_boleta(self, rut: str, clave: str, emisor: str, folio: str, causa: int = 3) -> dict:
        """Anula una boleta previamente emitida.
        causa: 1 = no se efectuó el pago, 2 = no se prestó el servicio, 3 = error de digitación
        """
        if self.mock:
            return {"folio": folio, "estado": "ANULADA", "mensaje": "Boleta anulada exitosamente (Modo Mock)"}

        url = f"{self.base_url}/api/v2/sii/bhe/emitidas/anular/{emisor}/{folio}"
        body = self._auth_block(rut, clave)

        try:
            response = self._post_con_reintento_sesion(url, body, params={"causa": causa})
            self._log_stats(response)
            if not response.ok:
                raise ApiGatewayError(
                    f"Error {response.status_code} al anular boleta",
                    status_code=response.status_code,
                    payload=self._parse_response(response)
                )
            res_json = self._parse_response(response)
            data = res_json.get("data", res_json)
            return self._normalizar_respuesta_anulacion(data, folio=folio)
        except requests.RequestException as e:
            raise ApiGatewayError(f"Error de conexión con apigateway.cl: {str(e)}")

    def descargar_pdf(self, rut: str, clave: str, codigo: str) -> dict:
        """Obtiene el PDF de una boleta emitida (código asignado por el SII, no el folio).
        Devuelve {"pdf_bytes": bytes|None, "data": dict|None} - ver _handle_pdf_response."""
        if self.mock:
            return {
                "pdf_bytes": None,
                "data": {
                    "codigo": codigo,
                    "pdf_url": f"https://apigateway.cl/mock/pdf/{codigo}.pdf",
                    "mensaje": "PDF generado (Modo Mock)"
                }
            }

        url = f"{self.base_url}/api/v2/sii/bhe/emitidas/pdf/{codigo}"
        body = self._auth_block(rut, clave)

        try:
            response = self._post_con_reintento_sesion(url, body)
            self._log_stats(response)
            return self._handle_pdf_response(response)
        except requests.RequestException as e:
            raise ApiGatewayError(f"Error de conexión con apigateway.cl: {str(e)}")

    def enviar_email(self, rut: str, clave: str, codigo: str, email_destino: str | None = None) -> dict:
        """Envía la boleta emitida por correo. Si no se indica email_destino, usa el correo
        que el SII tenga registrado por defecto para el receptor."""
        if self.mock:
            return {
                "codigo": codigo,
                "mensaje": f"Correo enviado a {email_destino or 'receptor registrado en el SII'} (Modo Mock)"
            }

        url = f"{self.base_url}/api/v2/sii/bhe/emitidas/email/{codigo}"
        body = self._auth_block(rut, clave)
        if email_destino:
            body["destinatario"] = {"email": email_destino}

        try:
            response = self._post_con_reintento_sesion(url, body)
            self._log_stats(response)
            if not response.ok:
                raise ApiGatewayError(
                    f"Error {response.status_code} al enviar email",
                    status_code=response.status_code,
                    payload=self._parse_response(response)
                )
            return self._parse_response(response)
        except requests.RequestException as e:
            raise ApiGatewayError(f"Error de conexión con apigateway.cl: {str(e)}")

    # ---------------- BHE Recibidas ----------------

    def listar_recibidas(self, rut: str, clave: str, receptor: str, periodo: str, pagina: int = 1) -> dict:
        """Lista boletas recibidas por el RUT receptor en un periodo (YYYYMM o YYYYMMDD)."""
        if self.mock:
            return {
                "boletas": [
                    {
                        "folio": 5001, "codigo": "COD-5001", "emisor": "76192083-9",
                        "razon_social_emisor": "Consultora Mock SpA", "fecha": "2026-08-15",
                        "monto_bruto": 300000, "estado": "N",
                    },
                    {
                        "folio": 5002, "codigo": "COD-5002", "emisor": "77654321-0",
                        "razon_social_emisor": "Servicios Mock Ltda", "fecha": "2026-08-20",
                        "monto_bruto": 150000, "estado": "R",
                    },
                ],
                "pagina": pagina,
            }

        url = f"{self.base_url}/api/v2/sii/bhe/recibidas/documentos/{receptor}/{periodo}"
        body = self._auth_block(rut, clave)

        try:
            response = self._post_con_reintento_sesion(url, body, params={"pagina": pagina})
            self._log_stats(response)
            if not response.ok:
                raise ApiGatewayError(
                    f"Error {response.status_code} al listar boletas recibidas",
                    status_code=response.status_code,
                    payload=self._parse_response(response)
                )
            return self._parse_response(response)
        except requests.RequestException as e:
            raise ApiGatewayError(f"Error de conexión con apigateway.cl: {str(e)}")

    def descargar_pdf_recibida(self, rut: str, clave: str, codigo: str) -> dict:
        """Obtiene el PDF de una boleta recibida (código, no folio).
        Devuelve {"pdf_bytes": bytes|None, "data": dict|None} - ver _handle_pdf_response."""
        if self.mock:
            return {
                "pdf_bytes": None,
                "data": {
                    "codigo": codigo,
                    "pdf_url": f"https://apigateway.cl/mock/pdf/recibida/{codigo}.pdf",
                    "mensaje": "PDF generado (Modo Mock)"
                }
            }

        url = f"{self.base_url}/api/v2/sii/bhe/recibidas/pdf/{codigo}"
        body = self._auth_block(rut, clave)

        try:
            response = self._post_con_reintento_sesion(url, body)
            self._log_stats(response)
            return self._handle_pdf_response(response)
        except requests.RequestException as e:
            raise ApiGatewayError(f"Error de conexión con apigateway.cl: {str(e)}")

    def observar_recibida(self, rut: str, clave: str, emisor: str, folio: str, causa: int) -> dict:
        """Observa una boleta recibida. causa: 1 = no reconoce relacion comercial, 2 = no reconoce al emisor."""
        if self.mock:
            return {"folio": folio, "estado": "OBSERVADA", "mensaje": "Boleta observada correctamente (Modo Mock)"}

        url = f"{self.base_url}/api/v2/sii/bhe/recibidas/observar/{emisor}/{folio}"
        body = self._auth_block(rut, clave)

        try:
            response = self._post_con_reintento_sesion(url, body, params={"causa": causa})
            self._log_stats(response)
            if not response.ok:
                raise ApiGatewayError(
                    f"Error {response.status_code} al observar boleta",
                    status_code=response.status_code,
                    payload=self._parse_response(response)
                )
            return self._parse_response(response)
        except requests.RequestException as e:
            raise ApiGatewayError(f"Error de conexión con apigateway.cl: {str(e)}")

    # ---------------- Autenticidad de terceros ----------------

    def verificar_autenticidad(self, rut: str, clave: str, codigo_barras: str | None = None,
                                emisor: str | None = None, receptor: str | None = None,
                                periodo: str | None = None, folio: str | None = None) -> dict:
        """Verifica la autenticidad de una BHE. Modo excluyente: o codigo_barras, o
        (emisor, receptor, periodo YYYY-MM-DD, folio)."""
        if self.mock:
            return {
                "valido": True,
                "emisor": emisor or "76192083-9",
                "folio": folio or "9001",
                "pdf_url": "https://apigateway.cl/mock/pdf/autenticidad.pdf",
                "mensaje": "Boleta encontrada y coincide con los datos consultados (Modo Mock)",
            }

        url = f"{self.base_url}/api/v2/sii/bhe/consultas_por_terceros"
        body = self._auth_block(rut, clave)
        if codigo_barras:
            body["codigo_barras"] = codigo_barras
        else:
            body["emisor"] = emisor
            body["receptor"] = receptor
            body["periodo"] = periodo
            body["folio"] = folio

        try:
            response = self._post_con_reintento_sesion(url, body)
            self._log_stats(response)
            if not response.ok:
                raise ApiGatewayError(
                    f"Error {response.status_code} al verificar autenticidad",
                    status_code=response.status_code,
                    payload=self._parse_response(response)
                )
            return self._parse_response(response)
        except requests.RequestException as e:
            raise ApiGatewayError(f"Error de conexión con apigateway.cl: {str(e)}")





