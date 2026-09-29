"""Cifrado reversible del RUT para las columnas 'rut_cifrado' en Supabase, mas un
hash determinista ('rut_hash') que permite buscar por RUT sin descifrar nada.

Requiere dos variables de entorno (ver .env):
  RUT_ENCRYPTION_KEY  -> clave Fernet (cifrado AES reversible)
  RUT_HASH_KEY        -> clave para el HMAC-SHA256 (busqueda determinista)

Generalas UNA SOLA VEZ con generar_claves_rut.py y jamas las subas al repo.
Si se pierden o cambian, los RUT ya cifrados quedan ilegibles para siempre.
"""
import hashlib
import hmac
import os

from cryptography.fernet import Fernet

_fernet = None


def _clave_env(nombre: str) -> str:
    valor = os.getenv(nombre)
    if not valor:
        raise RuntimeError(
            f"Falta {nombre} en el .env. Generala con: python generar_claves_rut.py"
        )
    return valor


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(_clave_env("RUT_ENCRYPTION_KEY").encode())
    return _fernet


def normalizar_rut(rut: str) -> str:
    """Quita puntos/espacios y pasa a mayuscula, para que el mismo RUT siempre
    produzca el mismo hash/cifrado sin importar como se haya escrito."""
    if not rut:
        return ""
    return rut.replace(".", "").replace(" ", "").upper()


def cifrar_rut(rut: str) -> str:
    """Cifrado reversible (AES via Fernet). Devuelve texto ilegible sin la clave."""
    return _get_fernet().encrypt(normalizar_rut(rut).encode()).decode()


def descifrar_rut(rut_cifrado: str | None) -> str | None:
    """Devuelve el RUT en texto plano, o None si esta vacio o no se pudo descifrar
    (ej. clave incorrecta o dato corrupto) para no reventar la pantalla."""
    if not rut_cifrado:
        return None
    try:
        return _get_fernet().decrypt(rut_cifrado.encode()).decode()
    except Exception:
        return None


def hash_rut(rut: str) -> str:
    """HMAC-SHA256 determinista: mismo RUT -> mismo hash siempre, pero no reversible.
    Se usa solo para poder hacer `WHERE rut_hash = ...` sin descifrar toda la tabla."""
    clave = _clave_env("RUT_HASH_KEY").encode()
    return hmac.new(clave, normalizar_rut(rut).encode(), hashlib.sha256).hexdigest()