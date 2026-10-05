"""PASO 2 de la migracion 005 (correr UNA vez, entre 005a y 005b).

Para cada empresa que todavia tiene el RUT en texto plano:
  - lo cifra (rut_cifrado) y calcula su hash (rut_hash), igual que el resto
    de la app (src/utils/crypto_rut.py, claves del .env)
  - la liga a su fila en 'receptores' (receptor_id). Si la empresa no existe
    como receptor, la crea. Asi la empresa existe UNA sola vez en el sistema.
  - borra el RUT en texto plano (rut = null)

Uso:
  python migrar_empresas_rut.py

Usa SUPABASE_SERVICE_KEY (igual que registrar_rut_perfil.py). Se puede correr
mas de una vez: las empresas ya migradas se saltan.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

from src.utils.crypto_rut import cifrar_rut, hash_rut
from src.utils.helpers import validar_rut

SUPABASE_URL = os.getenv("SUPABASE_URL")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SERVICE_KEY:
    raise SystemExit("Falta SUPABASE_SERVICE_KEY en el .env (clave 'service_role' de Supabase).")

db = create_client(SUPABASE_URL, SERVICE_KEY)


def receptor_para(nombre: str, rut: str) -> str:
    """Devuelve el id del receptor con ese RUT; si no existe, lo crea."""
    rut_h = hash_rut(rut)
    existente = db.table("receptores").select("id, nombre").eq("rut_hash", rut_h).execute().data
    if existente:
        print(f"   - ya existia como receptor ('{existente[0]['nombre']}'), se reutiliza")
        return existente[0]["id"]
    nuevo = db.table("receptores").insert({
        "nombre": nombre,
        "rut_cifrado": cifrar_rut(rut),
        "rut_hash": rut_h,
    }).execute().data
    print("   - no existia como receptor, se creo")
    return nuevo[0]["id"]


empresas = db.table("empresas").select("id, nombre, rut, rut_hash, receptor_id").execute().data
pendientes = [e for e in empresas if not (e.get("rut_hash") and e.get("receptor_id") and not e.get("rut"))]

if not pendientes:
    print("No hay empresas pendientes. Ya puedes correr 005b_finalizar.sql.")
    raise SystemExit(0)

errores = 0
for e in pendientes:
    print(f"* {e['nombre']}")
    rut = e.get("rut")
    if not rut:
        print("   ! no tiene RUT en texto plano ni cifrado completo; revisala a mano")
        errores += 1
        continue
    if not validar_rut(rut):
        print(f"   ! el RUT guardado no es valido (digito verificador); corrigelo antes")
        errores += 1
        continue

    receptor_id = e.get("receptor_id") or receptor_para(e["nombre"], rut)
    db.table("empresas").update({
        "rut_cifrado": cifrar_rut(rut),
        "rut_hash": hash_rut(rut),
        "receptor_id": receptor_id,
        "rut": None,
    }).eq("id", e["id"]).execute()
    print("   - RUT cifrado y texto plano eliminado")

if errores:
    raise SystemExit(f"\n{errores} empresa(s) con problemas. Corrigelas y vuelve a correr el script.")
print("\nListo. Ahora corre 005b_finalizar.sql en Supabase.")
