"""Crea (o borra) BOLETAS DEMO con PDF maqueta, para mostrar la app sin gastar
creditos de apigateway.cl.

Crea, para las cuentas de prueba existentes (no crea usuarios):
  - 3 receptores ficticios: RECEPTOR DEMO 1, 2 y 3 (RUT inventados, cifrados)
  - emisor@test.com   -> BOLETA DEMO 1 y BOLETA DEMO 2
  - usuario1@test.com -> BOLETA DEMO 3 y BOLETA DEMO 4
  - por cada boleta, un PDF MAQUETA en Storage ({usuario_id}/{boleta_id}.pdf)
    anotado en boletas.pdf_path, asi VER PDF / DESCARGAR lo leen desde la base
    de datos.

Las boletas demo usan folios 90001 a 90004 (no chocan con los reales) y la
descripcion empieza con "BOLETA DEMO". No existen en el SII: Anular, Enviar
por email (SII) y Reconciliar no aplican para ellas.

Uso (desde la carpeta sii_conect):
  python crear_boletas_demo.py           -> crea lo que falte (se puede repetir)
  python crear_boletas_demo.py --borrar  -> borra todo lo demo (boletas, PDF y receptores)
"""
import os
import sys
import uuid
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

from src.utils.crypto_rut import cifrar_rut, hash_rut
from src.utils.pdf_maqueta import pdf_maqueta_boleta

SUPABASE_URL = os.getenv("SUPABASE_URL")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
if not SERVICE_KEY:
    raise SystemExit("Falta SUPABASE_SERVICE_KEY en el .env (clave 'service_role' de Supabase).")

db = create_client(SUPABASE_URL, SERVICE_KEY)
BUCKET = "pdf_boletas"
TASA = 0.1525  # retencion BHE 2026


def rut_ficticio(cuerpo: int) -> str:
    """RUT inventado pero con digito verificador valido."""
    suma, mult = 0, 2
    for d in reversed(str(cuerpo)):
        suma += int(d) * mult
        mult = mult + 1 if mult < 7 else 2
    resto = 11 - (suma % 11)
    dv = {11: "0", 10: "K"}.get(resto, str(resto))
    return f"{cuerpo}-{dv}"


RECEPTORES = {  # clave -> (nombre, RUT inventado, cuenta duena)
    1: ("RECEPTOR DEMO 1", rut_ficticio(70000001), "emisor@test.com"),
    2: ("RECEPTOR DEMO 2", rut_ficticio(70000002), "emisor@test.com"),
    3: ("RECEPTOR DEMO 3", rut_ficticio(70000003), "usuario1@test.com"),
}

BOLETAS = [  # (titulo, cuenta, receptor, folio, bruto, fecha, estado)
    ("BOLETA DEMO 1", "emisor@test.com",   1, "90001", 100000, "2026-10-01", "emitida"),
    ("BOLETA DEMO 2", "emisor@test.com",   2, "90002", 250000, "2026-10-05", "emitida"),
    ("BOLETA DEMO 3", "usuario1@test.com", 3, "90003",  80000, "2026-10-02", "emitida"),
    ("BOLETA DEMO 4", "usuario1@test.com", 3, "90004", 150000, "2026-10-06", "emitida"),
]


def perfil(email: str) -> dict:
    filas = db.table("perfiles").select("id, email, nombre_completo, rut_cifrado").eq("email", email).execute().data
    if not filas:
        raise SystemExit(f"No existe el perfil {email}.")
    return filas[0]


def crear():
    perfiles = {email: perfil(email) for email in {b[1] for b in BOLETAS} | {r[2] for r in RECEPTORES.values()}}

    # 1. Receptores demo (se buscan por rut_hash; si no existen se crean)
    receptores = {}
    for clave, (nombre, rut, duena) in RECEPTORES.items():
        h = hash_rut(rut)
        filas = db.table("receptores").select("id, nombre").eq("rut_hash", h).execute().data
        if filas:
            receptores[clave] = filas[0]
            print(f"Receptor ya existia: {nombre}")
        else:
            nuevo = db.table("receptores").insert({
                "nombre": nombre, "rut_hash": h, "rut_cifrado": cifrar_rut(rut),
                "usuario_id": perfiles[duena]["id"],
            }).execute().data[0]
            receptores[clave] = nuevo
            print(f"Receptor creado: {nombre}")

    # 2. Boletas demo con su PDF maqueta
    for titulo, email, rec, folio, bruto, fecha, estado in BOLETAS:
        p = perfiles[email]
        existe = db.table("boletas").select("id").eq("usuario_id", p["id"]).eq("folio_sii", folio).execute().data
        if existe:
            print(f"Ya existia: {titulo} (folio {folio})")
            continue

        retenido = round(bruto * TASA)
        boleta = {
            "id": str(uuid.uuid4()),
            "usuario_id": p["id"],
            "receptor_id": receptores[rec]["id"],
            "folio_sii": folio,
            "monto_bruto": bruto,
            "tasa_retencion": TASA,
            "monto_retenido": retenido,
            "monto_liquido": bruto - retenido,
            "estado": estado,
            "fecha_emision": f"{fecha}T00:00:00+00:00",
            "descripcion": f"{titulo} - Servicios profesionales de prueba",
            "es_test": True,
            "respuesta_sii": {"demo": True},
        }
        if p.get("rut_cifrado"):
            boleta["rut_emisor_cifrado"] = p["rut_cifrado"]

        ruta = f"{p['id']}/{boleta['id']}.pdf"
        pdf = pdf_maqueta_boleta(titulo, boleta, p.get("nombre_completo") or email,
                                 receptores[rec]["nombre"])
        db.storage.from_(BUCKET).upload(path=ruta, file=pdf,
                                        file_options={"content-type": "application/pdf", "upsert": "true"})
        boleta["pdf_path"] = ruta
        try:
            db.table("boletas").insert(boleta).execute()
        except Exception:
            db.storage.from_(BUCKET).remove([ruta])  # no dejar el PDF huerfano
            raise
        print(f"Creada: {titulo} (folio {folio}, {email}) con PDF maqueta")

    print("Listo.")


def borrar():
    ids_perfiles = [perfil(e)["id"] for e in {b[1] for b in BOLETAS}]
    folios = [b[3] for b in BOLETAS]
    boletas = db.table("boletas").select("id, folio_sii, pdf_path, descripcion") \
        .in_("usuario_id", ids_perfiles).in_("folio_sii", folios).execute().data or []
    boletas = [b for b in boletas if str(b.get("descripcion") or "").startswith("BOLETA DEMO")]

    rutas = [b["pdf_path"] for b in boletas if b.get("pdf_path")]
    if rutas:
        db.storage.from_(BUCKET).remove(rutas)
    for b in boletas:
        db.table("historial_bhe").delete().eq("boleta_id", b["id"]).execute()
        db.table("boletas").delete().eq("id", b["id"]).execute()
        print(f"Borrada: folio {b['folio_sii']}")

    for nombre, rut, _ in RECEPTORES.values():
        h = hash_rut(rut)
        ids = [r["id"] for r in db.table("receptores").select("id").eq("rut_hash", h).execute().data or []]
        if not ids:
            continue
        if db.table("boletas").select("id").in_("receptor_id", ids).execute().data:
            print(f"No se borro {nombre}: todavia tiene boletas.")
            continue
        db.table("receptores").delete().in_("id", ids).execute()
        print(f"Receptor borrado: {nombre}")
    print("Listo.")


if __name__ == "__main__":
    borrar() if "--borrar" in sys.argv else crear()
