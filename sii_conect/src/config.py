import os

# Modo de prueba/simulación
MOCK_MODE = os.getenv("MOCK_MODE", "True") == "True"

# Configuración API Gateway
# La URL base de la API v2 es "https://app.apigateway.cl" (confirmado en la Academia
# de API Gateway y en la documentación oficial del cliente). El dominio corto
# "apigateway.cl" que aparece en algunos ejemplos de marketing NO es el correcto
# para las llamadas reales a la API.
APIGATEWAY_BASE_URL = os.getenv("APIGATEWAY_BASE_URL", "https://app.apigateway.cl")
APIGATEWAY_TOKEN = os.getenv("APIGATEWAY_TOKEN", "token_de_prueba")

# Configuración Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://tu-proyecto.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "tu_anon_key_aqui")