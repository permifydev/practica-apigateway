import logging
import random
from datetime import datetime
import requests
from src.config import APIGATEWAY_BASE_URL, APIGATEWAY_TOKEN, MOCK_MODE

logger = logging.getLogger(__name__)

class ApiGatewayError(Exception):
    def __init__(self, message: str, status_code: int | None = None, payload: dict | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload

class ApiGatewayClient:
    def __init__(self, token: str = APIGATEWAY_TOKEN, base_url: str = APIGATEWAY_BASE_URL, mock: bool = MOCK_MODE):
        self.token = token
        self.base_url = base_url.rstrip("/") if base_url else "https://app.apigateway.cl"
        self.mock = mock
        self.session = requests.Session()

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

    def _log_stats(self, response):
        creditos = response.headers.get("X-Stats-Credits-Remaining")
        restantes_minuto = response.headers.get("X-RateLimit-Remaining")
        if creditos is not None:
            logger.info(f"Creditos restantes en la conexion: {creditos}")
        if restantes_minuto is not None:
            logger.info(f"Peticiones restantes este minuto: {restantes_minuto}")

    # ---------------- BHE Emitidas ----------------

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
            return res_json.get("data", res_json)
        except requests.RequestException as e:
            raise ApiGatewayError(f"Error de conexión con apigateway.cl: {str(e)}")

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
            return self._parse_response(response)
        except requests.RequestException as e:
            raise ApiGatewayError(f"Error de conexión con apigateway.cl: {str(e)}")

    def descargar_pdf(self, rut: str, clave: str, codigo: str) -> dict:
        """Obtiene el PDF de una boleta emitida (código asignado por el SII, no el folio)."""
        if self.mock:
            return {
                "codigo": codigo,
                "pdf_url": f"https://apigateway.cl/mock/pdf/{codigo}.pdf",
                "mensaje": "PDF generado (Modo Mock)"
            }

        url = f"{self.base_url}/api/v2/sii/bhe/emitidas/pdf/{codigo}"
        body = self._auth_block(rut, clave)

        try:
            response = self._post_con_reintento_sesion(url, body)
            self._log_stats(response)
            if not response.ok:
                raise ApiGatewayError(
                    f"Error {response.status_code} al obtener PDF",
                    status_code=response.status_code,
                    payload=self._parse_response(response)
                )
            return self._parse_response(response)
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
        """Obtiene el PDF de una boleta recibida (código, no folio)."""
        if self.mock:
            return {
                "codigo": codigo,
                "pdf_url": f"https://apigateway.cl/mock/pdf/recibida/{codigo}.pdf",
                "mensaje": "PDF generado (Modo Mock)"
            }

        url = f"{self.base_url}/api/v2/sii/bhe/recibidas/pdf/{codigo}"
        body = self._auth_block(rut, clave)

        try:
            response = self._post_con_reintento_sesion(url, body)
            self._log_stats(response)
            if not response.ok:
                raise ApiGatewayError(
                    f"Error {response.status_code} al obtener PDF de boleta recibida",
                    status_code=response.status_code,
                    payload=self._parse_response(response)
                )
            return self._parse_response(response)
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