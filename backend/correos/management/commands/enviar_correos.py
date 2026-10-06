"""python manage.py enviar_correos            -> envia los pendientes una vez
python manage.py enviar_correos --loop 60  -> revisa cada 60 segundos (dejarlo corriendo)"""
import time

from django.core.management.base import BaseCommand

from correos.services import procesar_pendientes


class Command(BaseCommand):
    help = "Envia los correos pendientes de solicitudes de BHE"

    def add_arguments(self, parser):
        parser.add_argument("--loop", type=int, default=0,
                            help="Segundos entre revisiones (0 = una sola vez)")

    def handle(self, *args, **opciones):
        while True:
            resumen = procesar_pendientes()
            self.stdout.write(
                f"Enviados: {resumen['enviados']}  Reintentar: {resumen['reintentar']}  "
                f"Error: {resumen['error']}")
            if not opciones["loop"]:
                break
            time.sleep(opciones["loop"])
