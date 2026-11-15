# Rumbo

Sabe a dónde vas. App web para registrar peso, pasos y calorías, con gráficas
de evolución. Cada persona tiene su cuenta y solo ve sus propios datos.

Hecha con Django, PostgreSQL y Chart.js. Se despliega con Docker Compose en un
NAS Synology, gestionado con Portainer, detrás de Nginx Proxy Manager.

## Despliegue en Portainer

En esta guía, `rumbo.ejemplo.com` representa tu dominio y `192.168.1.10` la IP
de tu NAS en la red local. Cámbialos por los tuyos.

### 1. Crear el stack desde el repositorio

1. En Portainer, entra a **Stacks > Add stack**.
2. Ponle de nombre `rumbo` y elige **Repository**.
3. Completa:
   - **Repository URL:** `https://github.com/watuesta/rumbo`
   - **Repository reference:** `refs/heads/main`
   - **Compose path:** `docker-compose.yml`
4. En **Environment variables**, agrega las variables de `.env.example` con sus
   valores reales:

   | Variable | Valor |
   |---|---|
   | `SECRET_KEY` | Una clave larga y aleatoria. Genérala con `python3 -c "import secrets; print(secrets.token_urlsafe(50))"` |
   | `DEBUG` | `False` |
   | `ALLOWED_HOSTS` | `rumbo.ejemplo.com` |
   | `CSRF_TRUSTED_ORIGINS` | `https://rumbo.ejemplo.com` |
   | `POSTGRES_DB` | `rumbo` |
   | `POSTGRES_USER` | `rumbo` |
   | `POSTGRES_PASSWORD` | Una contraseña larga y aleatoria |

5. Pulsa **Deploy the stack**. Portainer descarga el repo, construye la imagen
   desde el `Dockerfile` y levanta dos contenedores:
   - `web`: la app, publicada en el puerto **8130** del NAS.
   - `db`: PostgreSQL, sin puerto publicado. Sus datos quedan en el volumen
     `rumbo_pgdata`.

Al arrancar, `web` aplica las migraciones y recopila los archivos estáticos por
su cuenta.

> Guarda `SECRET_KEY` y `POSTGRES_PASSWORD` en tu gestor de contraseñas. Si
> cambias `POSTGRES_PASSWORD` después del primer despliegue, Postgres no la
> toma: la contraseña queda fijada al crear el volumen.

### 2. Publicar el dominio en Nginx Proxy Manager

1. Crea un **Proxy Host** para `rumbo.ejemplo.com`.
2. Destino: esquema `http`, IP `192.168.1.10`, puerto `8130`.
3. En la pestaña **SSL**, pide un certificado de Let's Encrypt y activa
   **Force SSL**.

Entra siempre por `https://rumbo.ejemplo.com`. Con `DEBUG=False` las cookies
solo viajan por HTTPS, así que el login no funciona si entras directo a
`http://192.168.1.10:8130`.

### 3. Crear el superusuario

1. En Portainer, ve a **Containers** y abre el contenedor `web` del stack
   `rumbo` (se llama algo como `rumbo-web-1`).
2. Pulsa **Console**, deja el comando en `/bin/sh` y pulsa **Connect**.
3. Ejecuta:

   ```sh
   python manage.py createsuperuser
   ```

4. Escribe el usuario, el correo (opcional) y la contraseña.

### 4. Crear la cuenta del segundo usuario

1. Entra a `https://rumbo.ejemplo.com/admin/` con el superusuario.
2. En **Usuarios**, pulsa **Agregar usuario**.
3. Escribe el nombre de usuario y la contraseña, y guarda.
4. No marques "Es staff" ni "Es superusuario": la cuenta solo necesita usar la
   app.
5. Comparte el usuario y la contraseña con la otra persona. La primera vez que
   entre, Rumbo le pide su peso inicial, su meta y su meta de pasos.

No hay registro público: todas las cuentas se crean desde el panel de
administración.

## Actualizar tras un cambio en el repo

1. Haz push del cambio a `main` en GitHub.
2. En Portainer, abre **Stacks > rumbo**.
3. Pulsa **Pull and redeploy** y confirma. Activa **Re-pull image and
   redeploy** solo si cambió la imagen de Postgres; para cambios de la app no
   hace falta.
4. Portainer descarga el código nuevo, reconstruye `web` y lo reinicia. Las
   migraciones nuevas se aplican solas al arrancar.

Los datos de Postgres viven en el volumen `rumbo_pgdata` y se conservan entre
despliegues. No borres ese volumen.

## Desarrollo local

Requiere Python 3.13 o superior. Sin `POSTGRES_DB` definida, la app usa SQLite.

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
export DEBUG=True
.venv/bin/python manage.py migrate
.venv/bin/python manage.py createsuperuser
.venv/bin/python manage.py runserver
```

Tests:

```sh
DEBUG=True .venv/bin/python manage.py test
```

## Créditos

- [Chart.js](https://www.chartjs.org/) 4.4.7, licencia MIT, en `static/vendor/`.
- [Bricolage Grotesque](https://github.com/ateliertriay/bricolage), licencia
  SIL Open Font License, en `static/fonts/`.
