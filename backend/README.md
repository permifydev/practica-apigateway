# correo_backend (Django)

Servidor aparte de la app Flet, conectado a la MISMA base de datos de Supabase.

1. **Panel de administracion** (`/admin/`): se ven todas las tablas del proyecto
   (usuarios, empresas, ventas, solicitudes, notificaciones, correos, boletas...)
   y se gestionan los usuarios del panel y sus permisos.
2. **Envio de correos** de las solicitudes de BHE (`/correos/enviar/`).

Django NO cambia la estructura de las tablas de la app (`managed = False`).
Sus propias tablas (usuarios del panel, sesiones) van en el esquema `django`
de Supabase, separadas de `public`.

## Primera vez

1. En Supabase > SQL Editor: `create schema if not exists django;`
2. Agregar al `.env` las variables de `.env.example`.
3. En PowerShell:
   ```powershell
   cd correo_backend
   python -m pip install -r requirements.txt
   python manage.py migrate
   python manage.py createsuperuser
   ```

## Uso diario

```powershell
python manage.py runserver
```
Panel: http://127.0.0.1:8000/admin/

Para enviar los correos que quedaron en cola:
`python manage.py enviar_correos` (o desde el panel: Correos > accion "Enviar ahora").

## Render

- Root Directory: `correo_backend`
- Build Command: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`
- Start Command: `gunicorn config.wsgi`
- Variables: las mismas del `.env`, mas `DJANGO_DEBUG=0`.
