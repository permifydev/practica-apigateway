import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Cargar variables desde el archivo .env
load_dotenv()

# Modo de prueba/simulación
MOCK_MODE = os.getenv("MOCK_MODE", "True") == "True"

# Configuración API Gateway
# La URL base de la API v2 es "https://app.apigateway.cl"
APIGATEWAY_BASE_URL = os.getenv("APIGATEWAY_BASE_URL", "https://app.apigateway.cl")
APIGATEWAY_TOKEN = os.getenv("APIGATEWAY_TOKEN", "token_de_prueba")

# Proxy Squid (AWS Lightsail) - apigateway.cl solo acepta conexiones desde esta IP fija.

PROXY_URL = os.getenv("PROXY_URL")

# Configuración Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://tu-proyecto.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "tu_anon_key_aqui")

# Inicializar y exportar el cliente de Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)




