# SII Connect

Aplicacion web para emitir y administrar Boletas de Honorarios Electronicas (BHE)
del SII, a traves de la API de API Gateway (apigateway.cl). Proyecto de practica
desarrollado en la Unidad de Innovacion de Permify.

Tiene dos partes que se publican juntas en una sola URL:

- `/` : app para usuarios (Flet). Emisores: emitir, ver, descargar, enviar y anular
  boletas. Empresas: resumen de ventas y comisiones y solicitudes de BHE.
- `/admin/` : panel de administracion (Django) para revisar todas las tablas.

## Estructura

```
servidor.py        reparte las rutas entre Flet y Django (una sola URL)
requirements.txt   dependencias de todo el proyecto
sii_conect/        app Flet (main.py, src/views, src/services, src/utils)
backend/           panel Django y envio de correos (ver backend/README.md)
```

Scripts de apoyo en `sii_conect/` (se corren a mano desde esa carpeta):

- `generar_claves_rut.py`: genera RUT_ENCRYPTION_KEY y RUT_HASH_KEY.
- `registrar_empresa.py` / `registrar_rut_perfil.py`: cargan una empresa o el RUT de un usuario.
- `cambiar_clave_usuario.py`: cambia la clave de una cuenta de la app.
- `crear_boletas_demo.py`: crea boletas de demostracion (sin gastar creditos). `--borrar` las elimina.
- `diagnostico_supabase.py`: revisa la conexion y los datos basicos.
- `prueba_permisos.py`: comprueba que un usuario comun no puede modificar el monto de una boleta.

## Servicios externos

- **API Gateway**: conexion con el SII. Cobra por consulta (creditos) y solo acepta
  pedidos desde una IP registrada.
- **Proxy Squid en AWS Lightsail**: IP fija por la que pasan todas las consultas a API Gateway.
- **Supabase**: base de datos PostgreSQL con RLS, inicio de sesion y Storage
  (bucket `pdf_boletas` para los PDF).
- **Render**: publicacion de la app y el panel.

## Variables de entorno

Van en un archivo `.env` en la raiz (no se sube a GitHub) y en Render:

| Variable | Para que |
|---|---|
| `APIGATEWAY_BASE_URL`, `APIGATEWAY_TOKEN` | Conexion con API Gateway |
| `PROXY_URL` | Proxy con IP fija |
| `SUPABASE_URL`, `SUPABASE_KEY` | Supabase para la app (clave publica) |
| `SUPABASE_SERVICE_KEY` | Supabase para el panel (Storage) |
| `DATABASE_URL` | Conexion del panel con el usuario `panel_admin` |
| `RUT_ENCRYPTION_KEY`, `RUT_HASH_KEY` | Cifrado y busqueda de RUT |
| `DJANGO_SECRET_KEY`, `DJANGO_DEBUG` | Django (`DJANGO_DEBUG=0` en Render) |
| `CORREOS_API_TOKEN`, `EMAIL_*` | Envio de correos de solicitudes |

## Correr en local

```powershell
python -m pip install -r requirements.txt
uvicorn servidor:app --reload
```

App: http://127.0.0.1:8000/  
Panel: http://127.0.0.1:8000/admin/

## Render

- Start Command: `uvicorn servidor:app --host 0.0.0.0 --port $PORT`
- Variables: las mismas del `.env`.

## Seguridad

- Los RUT se guardan cifrados (Fernet) y se buscan con un hash HMAC; nunca en texto plano.
- Permisos por perfil en la base de datos: sin sesion no se ve nada, los usuarios no
  pueden borrar ni cambiar montos, cada uno ve solo sus receptores, y el panel usa
  su propio usuario `panel_admin` con permisos limitados.
- La Clave SII no se guarda: se pide en cada accion que llega al SII.

## Pendiente

- Cambiar el envio de correos a Gmail API (Render bloquea SMTP).
