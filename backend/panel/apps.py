from django.apps import AppConfig
from django.db.backends.signals import connection_created


def _usar_esquema_django(sender, connection, **kwargs):
    """Cada conexion busca primero en el esquema 'django' (tablas del panel)
    y despues en 'public' (tablas de la app)."""
    if connection.vendor == "postgresql":
        with connection.cursor() as cur:
            cur.execute("SET search_path TO django, public")


class PanelConfig(AppConfig):
    name = "panel"
    verbose_name = "SII Connect"

    def ready(self):
        connection_created.connect(_usar_esquema_django)
