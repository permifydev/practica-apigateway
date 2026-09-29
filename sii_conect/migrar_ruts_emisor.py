"""Migra 'perfiles.rut' y 'boletas.rut_emisor' de texto plano a sus columnas
cifradas. Correr UNA SOLA VEZ, despues de agregar las columnas rut_cifrado y
rut_emisor_cifrado en Supabase.

IMPORTANTE: usa la clave SUPABASE_SERVICE_KEY (service_role), no la anon key
normal de la app, porque 'perfiles' y 'boletas' tienen RLS y con la anon key
sin sesion iniciada las consultas no ven ninguna fila (parecen vacias sin
dar error). La service_role key salta el RLS -- por eso nunca debe usarse
en la app en si, solo en scripts locales como este.

Uso:  python migrar_ruts_emisor.py
Es seguro correrlo mas de una vez: si una fila ya tiene la columna cifrada
llena, se salta.
"""
import os
from dotenv import load_dotenv
from pathlib import Path
from supabase import create_client

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

from src.utils.crypto_rut import cifrar_rut

SUPABASE_URL = os.getenv("SUPABASE_URL")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SERVICE_KEY:
    raise SystemExit(
        "Falta SUPABASE_SERVICE_KEY en el .env.\n"
        "Ve a Supabase -> Project Settings -> API -> copia la clave 'service_role'\n"
        "y agregala como: SUPABASE_SERVICE_KEY=... en tu .env"
    )

db = create_client(SUPABASE_URL, SERVICE_KEY)

# --- perfiles ---
perfiles = db.table("perfiles").select("id, rut, rut_cifrado").execute().data or []
pendientes = [p for p in perfiles if p.get("rut") and not p.get("rut_cifrado")]
print(f"perfiles: {len(perfiles)} en total, {len(pendientes)} por migrar.")
for p in pendientes:
    db.table("perfiles").update({"rut_cifrado": cifrar_rut(p["rut"])}).eq("id", p["id"]).execute()
    print(f"  Migrado perfil id={p['id']}")

# --- boletas ---
boletas = db.table("boletas").select("id, rut_emisor, rut_emisor_cifrado").execute().data or []
pendientes_b = [b for b in boletas if b.get("rut_emisor") and not b.get("rut_emisor_cifrado")]
print(f"boletas: {len(boletas)} en total, {len(pendientes_b)} por migrar.")
for b in pendientes_b:
    db.table("boletas").update({"rut_emisor_cifrado": cifrar_rut(b["rut_emisor"])}).eq("id", b["id"]).execute()
    print(f"  Migrada boleta id={b['id']}")

print("Listo. Verifica en el dashboard que rut_cifrado y rut_emisor_cifrado")
print("esten llenos en TODAS las filas antes de borrar las columnas viejas.")