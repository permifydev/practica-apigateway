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
        self.base_url = base_url.rstrip("/") if base_url else "https://apigateway.cl"
        self.mock = mock
        self.session = requests.Session()

    def _headers(self) -> dict:
        return {
            "Authorization": f"Token {self.token}",
            "Content-Type": "application/json",
        }

    def _auth_block(self, rut: str, clave: str) -> dict:
        return {"auth": {"pass": {"rut": rut, "clave": clave}}}

    def emitir_boleta(self, rut: str, clave: str, boleta_payload: dict) -> dict:
        """Emite boleta. En modo simulación (mock=True), genera un folio ficticio sin llamar a la red."""
        if self.mock:
            folio_falso = random.randint(100, 9999)
            logger.info(f"[MODO MOCK] Simulando emisión de boleta Folio {folio_falso}")
            
            # Suma de items del detalle
            monto_bruto = sum(item.get("MontoItem", 0) for item in boleta_payload.get("Detalle", []))
            
            return {
                "folio": folio_falso,
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
            response = self.session.post(url, json=body, headers=self._headers(), timeout=20)
            if not response.ok:
                raise ApiGatewayError(
                    f"Error {response.status_code} de API Gateway",
                    status_code=response.status_code,
                    payload=response.json()
                )
            res_json = response.json()
            return res_json.get("data", res_json)
        except requests.RequestException as e:
            raise ApiGatewayError(f"Error de conexión con apigateway.cl: {str(e)}")

    def anular_boleta(self, rut: str, clave: str, emisor: str, folio: str, motivo: str | None = None) -> dict:
        """Anula una boleta previamente emitida."""
        if self.mock:
            return {"folio": folio, "estado": "ANULADA", "mensaje": "Boleta anulada exitosamente (Modo Mock)"}

        url = f"{self.base_url}/api/v2/sii/bhe/emitidas/anular/{emisor}/{folio}"
        body = self._auth_block(rut, clave)
        if motivo:
            body["motivo"] = motivo

        response = self.session.post(url, json=body, headers=self._headers(), timeout=20)
        return response.json()