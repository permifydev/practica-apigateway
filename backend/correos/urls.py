from django.urls import path
from . import views

urlpatterns = [
    path("enviar/", views.enviar_pendientes, name="enviar_pendientes"),
    path("estado/", views.estado, name="estado"),
]
