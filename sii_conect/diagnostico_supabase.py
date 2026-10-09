"""
Diagnostico rapido: confirma si la conexion a Supabase es real y que hay en 'perfiles'.
Ejecutar desde la carpeta sii_conect con: python diagnostico_supabase.py
"""
import logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")

from src.config import SUPABASE_URL, SUPABASE_KEY, nuevo_cliente_supabase

supabase = nuevo_cliente_supabase()

print("=" * 60)
print(f"SUPABASE_URL cargada: {SUPABASE_URL}")
print(f"SUPABASE_KEY cargada: {'SI (' + str(len(SUPABASE_KEY)) + ' caracteres)' if SUPABASE_KEY else 'NO'}")
print("=" * 60)

try:
    # El RUT esta cifrado (rut_cifrado): aca solo se muestra si existe, nunca el numero.
    res = supabase.table("perfiles").select("id, email, rut_cifrado, rol").execute()
    print(f"\nConexion real: SI. Filas en 'perfiles': {len(res.data)}\n")
    for fila in res.data:
        rut = "registrado" if fila.get("rut_cifrado") else "sin RUT"
        print(f"  - id={fila.get('id')} | email={fila.get('email')} | rut={rut} | rol={fila.get('rol')}")
    if not res.data:
        print("  (sin sesion, RLS no deja ver filas con la clave publica: lo normal es 0 filas."
              " Si ves 0 igual la conexion funciona.)")
except Exception as e:
    print(f"\nConexion real: FALLO. Error exacto:\n  {e}\n")
    print("Revisa: URL/KEY correctas, proyecto Supabase activo, y que la tabla 'perfiles' exista.")








