"""Setea (o actualiza) el RUT cifrado de un perfil puntual, por correo.
Uso administrativo: el campo RUT en Perfil esta deshabilitado a proposito
(solo el admin lo asigna), asi que este script es la forma de hacerlo.

Uso:
  python registrar_rut_perfil.py

Pide el correo y el RUT por teclado (asi no queda el RUT escrito en texto
plano en el historial de la terminal si compartes pantalla).
"""
import os
import getpass
from dotenv import load_dotenv
from pathlib import Path
from supabase import create_client

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

from src.utils.crypto_rut import cifrar_rut
from src.utils.helpers import validar_rut, formato_rut_puntos

SUPABASE_URL = os.getenv("SUPABASE_URL")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SERVICE_KEY:
    raise SystemExit(
        "Falta SUPABASE_SERVICE_KEY en el .env (clave 'service_role' de Supabase)."
    )

db = create_client(SUPABASE_URL, SERVICE_KEY)

email = input("Correo del perfil a actualizar: ").strip().lower()
rut = formato_rut_puntos(getpass.getpass("RUT (solo numeros, ej. 123456789; no se muestra en pantalla): "))

if not validar_rut(rut):
    raise SystemExit("Ese RUT no es valido (revisa el digito verificador).")

perfil = db.table("perfiles").select("id, email, rol").eq("email", email).execute().data
if not perfil:
    raise SystemExit(f"No existe ningun perfil con el correo '{email}'.")

perfil = perfil[0]
db.table("perfiles").update({"rut_cifrado": cifrar_rut(rut)}).eq("id", perfil["id"]).execute()

print(f"Listo. RUT guardado (cifrado) para {perfil['email']} (rol: {perfil['rol']}).")