# Panel de administracion (Django)

Corre junto a la app Flet en un solo servicio (`servidor.py` en la raiz) y usa la
misma base de datos de Supabase, con su propio usuario `panel_admin`.

1. **Panel de administracion** (`/admin/`): todas las tablas del proyecto
   (usuarios, boletas emitidas con su PDF, receptores, empresas, ventas,
   solicitudes, notificaciones, correos y registros tecnicos). Casi todo es
   solo lectura; lo que viene del SII no se edita aca. Los RUT no se muestran.
2. **Envio de correos** de las solicitudes de BHE (`/correos/enviar/`).
   Render bloquea SMTP, por eso el envio se va a cambiar a Gmail API.

Django NO cambia la estructura de las tablas de la app (`managed = False`).
Sus propias tablas (usuarios del panel, sesiones) van en el esquema `django`
de Supabase, separadas de `public`.

## Primera vez

1. En Supabase > SQL Editor: `create schema if not exists django;`
2. Variables en el `.env` de la raiz del proyecto (el mismo de la app Flet):
   `DATABASE_URL`, `DJANGO_SECRET_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`,
   `RUT_ENCRYPTION_KEY` (y las de correo). La lista completa esta en el README de la raiz.
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

## Render

El panel ya no es un servicio aparte: se publica junto con la app desde
`servidor.py`. Ver el README de la raiz.
