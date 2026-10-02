"""Cambia la clave de un usuario existente en Supabase Auth, sin depender del
dashboard. Util cuando el cambio de clave desde el dashboard no se aplica.

Uso:
  python cambiar_clave_usuario.py
"""
import os
import getpass
from dotenv import load_dotenv
from pathlib import Path
from supabase import create_client

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SERVICE_KEY:
    raise SystemExit(
        "Falta SUPABASE_SERVICE_KEY en el .env (clave 'service_role' de Supabase)."
    )

db = create_client(SUPABASE_URL, SERVICE_KEY)

email = input("Correo del usuario: ").strip().lower()
clave_nueva = getpass.getpass("Clave nueva (no se muestra en pantalla): ").strip()

if len(clave_nueva) < 6:
    raise SystemExit("La clave debe tener al menos 6 caracteres.")

# Hay que ubicar el user_id real en auth.users antes de poder actualizarlo.
resultado = db.auth.admin.list_users()
usuario = next((u for u in resultado if u.email and u.email.lower() == email), None)

if not usuario:
    raise SystemExit(f"No existe ningun usuario de Auth con el correo '{email}'.")

db.auth.admin.update_user_by_id(usuario.id, {"password": clave_nueva})

print(f"Listo. Clave actualizada para {email}.")