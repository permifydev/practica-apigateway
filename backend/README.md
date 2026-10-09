# Panel de administracion (Django)

Servidor aparte de la app Flet, conectado a la MISMA base de datos de Supabase.

1. **Panel de administracion** (`/admin/`): todas las tablas del proyecto
   (usuarios, boletas emitidas con su PDF, receptores, empresas, ventas,
   solicitudes, notificaciones, correos y registros tecnicos). Casi todo es
   solo lectura; lo que viene del SII no se edita aca. Los RUT no se muestran.
2. **Envio de correos** de las solicitudes de BHE (`/correos/enviar/`).
   Render bloquea SMTP: se reemplazara por Gmail API.

Django NO cambia la estructura de las tablas de la app (`managed = False`).
Sus propias tablas (usuarios del panel, sesiones) van en el esquema `django`
de Supabase, separadas de `public`.

## Primera vez

1. En Supabase > SQL Editor: `create schema if not exists django;`
2. Variables en el `.env` de la raiz del proyecto (el mismo de la app Flet):
   `DATABASE_URL`, `DJANGO_SECRET_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`,
   `RUT_ENCRYPTION_KEY` (y las de correo).
3. En PowerShell:
   ```powershell
   cd backend
   python -m pip install -r requirements.txt
   python manage.py migrate
   python manage.py createsuperuser
   ```

## Uso diario

```powershell
cd backend
python manage.py runserver
```
Panel: http://127.0.0.1:8000/admin/

Para enviar los correos que quedaron en cola:
`python manage.py enviar_correos` (o desde el panel: Correos > accion "Enviar ahora").

## Render (servicio practica-admin)

- Root Directory: `backend`
- Build Command: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`
- Start Command: `gunicorn config.wsgi`
- Variables: las mismas del `.env`, mas `DJANGO_DEBUG=0`.
