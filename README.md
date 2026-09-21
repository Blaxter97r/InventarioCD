# Inventario 2026

Aplicación Django desplegada en Render. En Render usa PostgreSQL; en desarrollo local sigue usando `db.sqlite3`. Los datos y archivos locales no se publican automáticamente.

## Publicar

1. Crea un repositorio privado y vacío en GitHub. Desde esta carpeta, enlázalo y sube el código:

   ```powershell
   git remote add origin https://github.com/TU_USUARIO/TU_REPOSITORIO.git
   git branch -M main
   git push -u origin main
   ```

2. En [Render Blueprints](https://dashboard.render.com/blueprints), elige **New Blueprint Instance**, conecta ese repositorio y aplica el archivo `render.yaml`. Esto configura el servicio web de pago con disco persistente de 1 GB y PostgreSQL gratuito, genera `SECRET_KEY`, conecta `DATABASE_URL` internamente, instala dependencias, recoge archivos estáticos y aplica migraciones al arrancar.
3. Espera a que Render muestre el despliegue como **Live**. Abre la URL `https://inventario-2026.onrender.com/login/` que Render asigne al servicio. El nombre final puede variar si ya está ocupado.
4. Crea el primer administrador desde esta computadora. En el panel de la base de datos de Render, copia la **External Database URL** (no la URL interna) y ejecuta en PowerShell desde esta carpeta:

   ```powershell
   $env:DATABASE_URL = Read-Host 'External Database URL de Render'
   .\venv\Scripts\python.exe manage.py createsuperuser
   Remove-Item Env:DATABASE_URL
   ```

   El usuario y la contraseña que crees permitirán entrar en `/login/`. Asegúrate de usar la URL de la misma base creada por el Blueprint. Si todavía no tienes el entorno virtual local, créalo con `python -m venv venv` e instala `python -m pip install -r requirements.txt` antes de este paso.

## Almacenamiento y preparación del inventario

- El disco del servicio web se monta en `/opt/render/project/src/media`, la misma ruta usada por `MEDIA_ROOT`. Conserva los PDF AS400 y los Excel originales entre reinicios y despliegues. Render toma [instantáneas diarias del disco](https://render.com/docs/disks), pero restaurar una instantánea revierte todo el disco a ese momento.
- El disco comienza con 1 GB. [Se puede ampliar más adelante, pero no reducir](https://render.com/docs/disks). Vigila su uso antes de cargar muchos reconteos: 70 PDF de 20 MB superarían esta capacidad incluso sin contar los Excel.
- Antes de adjuntar un disco nuevo, conserva copias de los archivos ya subidos: el disco comienza vacío y los archivos del sistema temporal no se trasladan automáticamente. Si falta un AS400 anterior, un Administrador puede volver a adjuntarlo desde **Reconteos**.
- [PostgreSQL gratuito vence a los 30 días, limita el espacio a 1 GB y no incluye copias de seguridad](https://render.com/docs/free). El disco web no protege los datos de PostgreSQL. Cambia la base a un plan de pago y prepara una copia independiente antes del inventario.
- Tras configurar el disco, sube un PDF AS400 de prueba, genera el reconteo, vuelve a desplegar el servicio y verifica que el PDF completo todavía se descargue.

No subas `db.sqlite3`, `media/`, `.env` ni contraseñas al repositorio. Para un dominio propio, añade el dominio a `DJANGO_ALLOWED_HOSTS` y su origen HTTPS a `DJANGO_CSRF_TRUSTED_ORIGINS` en las variables de entorno del servicio.
