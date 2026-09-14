# Inventario 2026

Aplicación Django preparada para una **prueba gratuita temporal** en Render. En Render usa PostgreSQL; en desarrollo local sigue usando `db.sqlite3`. El despliegue crea una base nueva y vacía. Los datos y archivos locales no se publican.

## Publicar

1. Crea un repositorio privado y vacío en GitHub. Desde esta carpeta, enlázalo y sube el código:

   ```powershell
   git remote add origin https://github.com/TU_USUARIO/TU_REPOSITORIO.git
   git branch -M main
   git push -u origin main
   ```

2. En [Render Blueprints](https://dashboard.render.com/blueprints), elige **New Blueprint Instance**, conecta ese repositorio y aplica el archivo `render.yaml`. Esto crea el servicio web y PostgreSQL gratuitos, genera `SECRET_KEY`, conecta `DATABASE_URL` internamente, instala dependencias, recoge archivos estáticos y aplica migraciones al arrancar.
3. Espera a que Render muestre el despliegue como **Live**. Abre la URL `https://inventario-2026.onrender.com/login/` que Render asigne al servicio. El nombre final puede variar si ya está ocupado.
4. Crea el primer administrador desde esta computadora. En el panel de la base de datos de Render, copia la **External Database URL** (no la URL interna) y ejecuta en PowerShell desde esta carpeta:

   ```powershell
   $env:DATABASE_URL = Read-Host 'External Database URL de Render'
   .\venv\Scripts\python.exe manage.py createsuperuser
   Remove-Item Env:DATABASE_URL
   ```

   El usuario y la contraseña que crees permitirán entrar en `/login/`. Asegúrate de usar la URL de la misma base creada por el Blueprint. Si todavía no tienes el entorno virtual local, créalo con `python -m venv venv` e instala `python -m pip install -r requirements.txt` antes de este paso.

## Límites de esta prueba

- [PostgreSQL gratuito vence a los 30 días](https://render.com/docs/free). Para conservar datos más tiempo, cambia a un plan de pago antes del vencimiento.
- El servidor web gratuito no tiene disco persistente. Los archivos subidos durante la prueba se perderán cuando Render reinicie, suspenda o vuelva a desplegar el servicio. La base PostgreSQL no se borra con esos reinicios. Para conservar archivos en producción, usa almacenamiento externo o un servicio de pago con disco persistente.
- La primera visita después de un periodo de inactividad puede tardar cerca de un minuto mientras el servicio gratuito arranca.

No subas `db.sqlite3`, `media/`, `.env` ni contraseñas al repositorio. Para un dominio propio, añade el dominio a `DJANGO_ALLOWED_HOSTS` y su origen HTTPS a `DJANGO_CSRF_TRUSTED_ORIGINS` en las variables de entorno del servicio.
