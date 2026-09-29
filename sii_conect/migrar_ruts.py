"""Migra los RUT ya guardados en 'receptores' de texto plano a rut_hash + rut_cifrado.

Uso (una sola vez, DESPUES de correr sql/001_cifrar_rut_receptores.sql pasos 1-2
y de tener RUT_ENCRYPTION_KEY / RUT_HASH_KEY en tu .env):

    python migrar_ruts.py

Es seguro correrlo mas de una vez: si una fila ya tiene rut_hash, se salta.
"""
from src.services.supabase_service import SupabaseService
from src.utils.crypto_rut import cifrar_rut, hash_rut

db = SupabaseService()

filas = db.client.table("receptores").select("id, rut, rut_hash").execute().data or []
pendientes = [f for f in filas if f.get("rut") and not f.get("rut_hash")]

print(f"{len(filas)} receptores en total, {len(pendientes)} por migrar.")

for f in pendientes:
    db.client.table("receptores").update({
        "rut_hash": hash_rut(f["rut"]),
        "rut_cifrado": cifrar_rut(f["rut"]),
    }).eq("id", f["id"]).execute()
    print(f"  Migrado id={f['id']}")

print("Listo. Verifica en el dashboard de Supabase que rut_hash y rut_cifrado")
print("esten llenos en TODAS las filas antes de seguir con los pasos 3 y 4 del SQL.")