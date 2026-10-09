from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

admin.site.site_header = "SII Connect: Administración"
admin.site.site_title = "SII Connect"
admin.site.index_title = "Panel de administración"

urlpatterns = [
    path("", RedirectView.as_view(url="/admin/", permanent=False)),
    path("admin/", admin.site.urls),
    path("correos/", include("correos.urls")),
]
