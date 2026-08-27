import os

# Modo de prueba/simulación
MOCK_MODE = True

# Configuración API Gateway
APIGATEWAY_BASE_URL = os.getenv("APIGATEWAY_BASE_URL", "https://apigateway.cl")
APIGATEWAY_TOKEN = os.getenv("APIGATEWAY_TOKEN", "token_de_prueba")

# Configuración Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://tu-proyecto.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "tu_anon_key_aqui")