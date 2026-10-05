"""Crea (o actualiza) una empresa y opcionalmente le asocia un usuario.
Uso administrativo, igual que registrar_rut_perfil.py: el RUT queda cifrado
y la empresa queda ligada a su fila en 'receptores' (se crea si no existe).

Uso:
  python registrar_empresa.py

Requiere haber corrido 005a + migrar_empresas_rut.py + 005b.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

from src.utils.crypto_rut import cifrar_rut, hash_rut
from src.utils.helpers import validar_rut, formato_rut_puntos

SUPABASE_URL = os.getenv("SUPABASE_URL")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SERVICE_KEY:
    raise SystemExit("Falta SUPABASE_SERVICE_KEY en el .env (clave 'service_role' de Supabase).")

db = create_client(SUPABASE_URL, SERVICE_KEY)

nombre = input("Nombre de la empresa: ").strip()
rut = formato_rut_puntos(input("RUT de la empresa (solo numeros, ej. 761234560): "))
direccion = input("Direccion: ").strip()
comision_txt = input("Comision plataforma en % [15]: ").strip() or "15"
email_usuario = input("Correo del usuario que la administra (Enter para omitir): ").strip().lower()

if not nombre:
    raise SystemExit("El nombre es obligatorio.")
if not validar_rut(rut):
    raise SystemExit("Ese RUT no es valido (revisa el digito verificador).")
try:
    comision = float(comision_txt.replace(",", "."))
    assert 0 <= comision < 100
except (ValueError, AssertionError):
    raise SystemExit("La comision debe ser un numero entre 0 y 99.99.")

rut_h = hash_rut(rut)

# 1. Receptor (la misma empresa vista como receptora de boletas)
receptor = db.table("receptores").select("id").eq("rut_hash", rut_h).execute().data
if receptor:
    receptor_id = receptor[0]["id"]
    db.table("receptores").update({"nombre": nombre}).eq("id", receptor_id).execute()
else:
    receptor_id = db.table("receptores").insert({
        "nombre": nombre, "rut_cifrado": cifrar_rut(rut), "rut_hash": rut_h,
    }).execute().data[0]["id"]

# 2. Empresa
datos = {
    "nombre": nombre,
    "rut_cifrado": cifrar_rut(rut),
    "rut_hash": rut_h,
    "direccion": direccion or None,
    "comision_pct": comision,
    "receptor_id": receptor_id,
}
existente = db.table("empresas").select("id").eq("rut_hash", rut_h).execute().data
if existente:
    empresa_id = existente[0]["id"]
    db.table("empresas").update(datos).eq("id", empresa_id).execute()
    print(f"Empresa actualizada: {nombre}")
else:
    empresa_id = db.table("empresas").insert(datos).execute().data[0]["id"]
    print(f"Empresa creada: {nombre}")

# 3. Usuario asociado (opcional)
if email_usuario:
    perfil = db.table("perfiles").select("id, rol").eq("email", email_usuario).execute().data
    if not perfil:
        print(f"Aviso: no existe ningun perfil con el correo '{email_usuario}'. No se asocio.")
    else:
        db.table("perfiles").update({"empresa_id": empresa_id}).eq("id", perfil[0]["id"]).execute()
        print(f"{email_usuario} (rol: {perfil[0]['rol']}) asociado a {nombre}.")
