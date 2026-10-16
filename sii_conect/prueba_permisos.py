from getpass import getpass
from src.config import nuevo_cliente_supabase

db = nuevo_cliente_supabase()
db.auth.sign_in_with_password({
    "email": "emisor@test.com",
    "password": getpass("Clave de emisor@test.com: "),
})

b = db.table("boletas").select("id, monto_bruto").eq("folio_sii", "90001").single().execute().data
original = b["monto_bruto"]

try:
    r = db.table("boletas").update({"monto_bruto": 999999}).eq("id", b["id"]).execute()
    if r.data:
        print("PROBLEMA: se pudo cambiar el monto. Revirtiendo...")
        db.table("boletas").update({"monto_bruto": original}).eq("id", b["id"]).execute()
    else:
        print("OK: la base de datos rechazo el cambio")
except Exception as e:
    print("OK: la base de datos rechazo el cambio:", e)

db.auth.sign_out()