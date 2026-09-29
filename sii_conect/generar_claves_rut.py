"""Ejecutar UNA SOLA VEZ: python generar_claves_rut.py
Copia las dos lineas que imprime dentro de tu archivo .env """
import secrets
from cryptography.fernet import Fernet

print(f"RUT_ENCRYPTION_KEY={Fernet.generate_key().decode()}")
print(f"RUT_HASH_KEY={secrets.token_hex(32)}")