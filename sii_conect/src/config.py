import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Cargar variables desde el archivo .env
load_dotenv()

# Modo de prueba/simulación (False = pruebas reales contra API Gateway y Supabase)
MOCK_MODE = os.getenv("MOCK_MODE", "False") == "True"

# Configuración API Gateway
# La URL base de la API v2 es "https://app.apigateway.cl"
APIGATEWAY_BASE_URL = os.getenv("APIGATEWAY_BASE_URL", "https://app.apigateway.cl")
APIGATEWAY_TOKEN = os.getenv("APIGATEWAY_TOKEN", "token_de_prueba")

# Proxy Squid (AWS Lightsail) - apigateway.cl solo acepta conexiones desde esta IP fija.

PROXY_URL = os.getenv("PROXY_URL")

# Configuración Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://tu-proyecto.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "tu_anon_key_aqui")

def nuevo_cliente_supabase() -> Client:
    """Crea un cliente de Supabase NUEVO. Cada persona conectada debe tener el
    suyo (se guarda en su 'state' al iniciar sesion): el cliente guarda el token
    de quien inicio sesion y lo manda en cada consulta, asi que si fuera uno solo
    para todos, las consultas de una persona viajarian con la sesion de otra."""
    return create_client(SUPABASE_URL, SUPABASE_KEY)








