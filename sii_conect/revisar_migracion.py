"""Chequeo de solo lectura: dice si 'boletas' y 'perfiles' ya quedaron
migradas al RUT cifrado, o si todavia faltan filas.

Usa SUPABASE_SERVICE_KEY (service_role) para saltarse RLS y ver TODAS las
filas, no solo las del usuario logueado. Ver migrar_ruts_emisor.py para
como conseguir esa clave.

Uso: python revisar_migracion.py
"""
import os
from dotenv import load_dotenv
from pathlib import Path
from supabase import create_client

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SERVICE_KEY:
    raise SystemExit(
        "Falta SUPABASE_SERVICE_KEY en el .env (clave 'service_role' de Supabase).\n"
        "Sin ella, este chequeo con RLS activo siempre muestra 0 filas, aunque existan."
    )

db = create_client(SUPABASE_URL, SERVICE_KEY)

boletas = db.table("boletas").select("id, folio_sii, rut_emisor_cifrado").execute().data or []
pendientes_b = [b for b in boletas if not b.get("rut_emisor_cifrado")]
print(f"Boletas: {len(boletas)} en total, {len(pendientes_b)} SIN migrar.")
for b in pendientes_b[:10]:
    print(f"  falta migrar folio: {b.get('folio_sii')}")

perfiles = db.table("perfiles").select("id, rut_cifrado").execute().data or []
pendientes_p = [p for p in perfiles if not p.get("rut_cifrado")]
print(f"Perfiles: {len(perfiles)} en total, {len(pendientes_p)} SIN migrar.")
for p in pendientes_p[:10]:
    print(f"  falta migrar perfil id: {p.get('id')}")

if not pendientes_b and not pendientes_p and (boletas or perfiles):
    print("\nTodo migrado. Ya puedes borrar las columnas viejas 'rut' y 'rut_emisor' en Supabase.")
elif not boletas and not perfiles:
    print("\nSigue mostrando 0 filas -- revisa que SUPABASE_SERVICE_KEY sea la clave")
    print("correcta ('service_role', no 'anon') copiada del dashboard de Supabase.")
else:
    print("\nTodavia falta migrar. Corre: python migrar_ruts_emisor.py")