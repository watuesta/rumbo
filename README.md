# Rumbo

Sabe a dónde vas. App web para registrar peso, pasos y calorías, con gráficas
de evolución. Cada persona tiene su cuenta y solo ve sus propios datos.

Hecha con Django, PostgreSQL y Chart.js. Se despliega con Docker Compose en un
NAS Synology, gestionado con Portainer, detrás de Nginx Proxy Manager.

## Qué hace

Rumbo está pensada para usarse desde el celular en pocos segundos al día: anotas
el pesaje de la mañana, los pasos y lo que comiste, y la app te muestra cuánto
has avanzado hacia tu meta.

- **Inicio.** Tu último peso en grande y una línea que va de tu peso inicial a
  tu meta, con un marcador en el punto donde estás. Debajo, los kilos que has
  bajado, los que faltan, tu promedio de pasos de la semana (de lunes a hoy)
  frente a tu meta diaria y las calorías de hoy con lo que te queda de tu
  objetivo.
- **Esta semana.** También en el inicio, las calorías de lunes a domingo frente
  a un presupuesto semanal, para saber si vas bien y cuánto margen tienes para el
  fin de semana. Muestra lo consumido, lo que queda hasta el domingo y cuánto
  puedes comer en promedio por día en los días que faltan. El presupuesto suma
  el objetivo de hoy, de los días que faltan y de los días pasados en los que
  anotaste comidas: un día sin anotar no cuenta como margen, y la app lo avisa.
  También avisa si el promedio por día baja del mínimo seguro. Se reinicia cada
  lunes.
- **Registrar hoy.** Una sola pantalla por día con peso, pasos, calorías
  activas, cintura y cadera, todos opcionales: puedes anotar el peso en la
  mañana y los pasos en la noche. En la misma pantalla agregas comidas con sus
  calorías y una descripción corta, y ves el total del día frente a tu objetivo.
  Las calorías las escribes tú; la app no las calcula. Las calorías activas
  (ejercicio, movimiento) se suman al objetivo de ese día. Peso y medidas
  aceptan coma o punto decimal.
- **Historial.** La lista de días registrados con peso, pasos y calorías. Desde
  ahí abres cualquier día para corregirlo o borrarlo, y editas o borras comidas.
- **Gráficas.** Peso diario con su promedio móvil de 7 días y la línea de la
  meta; pasos por día frente a la meta diaria; y calorías totales por día frente
  al objetivo de cada día. Puedes ver los últimos 30 días, 90 días o todo el
  historial.
- **Perfil.** Peso inicial, fecha de inicio, peso meta, meta diaria de pasos
  (8.000 por defecto), sexo, fecha de nacimiento y altura. Se pide la primera vez
  que entras y lo puedes cambiar cuando quieras. Con tu último peso, sexo, edad
  y altura, la app calcula tu objetivo diario de calorías: tu mantenimiento
  (Mifflin-St Jeor, con vida sedentaria) menos 500 kcal, sin bajar de 1.200 kcal
  en mujeres ni de 1.500 en hombres.

Otros detalles:

- **Privada por cuenta.** No hay registro público: las cuentas se crean desde el
  panel de administración y cada persona ve y edita solo sus propios datos.
- **Hecha para el iPhone.** Botones grandes, teclado numérico en los campos de
  números y opción de agregarla a la pantalla de inicio con su propio ícono.
- **Modo claro y oscuro.** Sigue la configuración del teléfono y tiene un botón
  para cambiarlo; recuerda tu elección.
- **En español**, con hora de Colombia (America/Bogota), kilos y centímetros.
- **Sesión de 90 días**, para no tener que entrar seguido.

## Despliegue en Portainer

En esta guía, `rumbo.ejemplo.com` representa tu dominio y `192.168.1.10` la IP
de tu NAS en la red local. Cámbialos por los tuyos.

### 1. Crear el stack desde el repositorio

1. En Portainer, entra a **Stacks > Add stack**.
2. Ponle de nombre `rumbo` y elige **Repository**.
3. Antes de desplegar, crea la carpeta de los respaldos: en DSM, ve a
   **Panel de control > Carpeta compartida**, crea una carpeta compartida
   `backups` y, dentro, una subcarpeta `rumbo`.
4. Completa:
   - **Repository URL:** `https://github.com/watuesta/rumbo`
   - **Repository reference:** `refs/heads/main`
   - **Compose path:** `docker-compose.yml`
5. En **Environment variables**, agrega las variables de `.env.example` con sus
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
   | `BACKUP_DIR` | `/volume1/backups/rumbo` (la carpeta del paso 3) |
   | `BACKUP_RETENCION_DIAS` | `30`, opcional |

6. Pulsa **Deploy the stack**. Portainer descarga el repo, construye la imagen
   desde el `Dockerfile` y levanta tres contenedores:
   - `web`: la app, publicada en el puerto **8130** del NAS.
   - `db`: PostgreSQL, sin puerto publicado. Sus datos quedan en el volumen
     `rumbo_pgdata` (Portainer lo muestra como `rumbo_rumbo_pgdata`).
   - `backup`: respalda la base de datos todos los días en `BACKUP_DIR`. Ver
     [Respaldos](#respaldos).

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
2. Pulsa **Console**, deja el comando en `/bin/bash`, escribe `rumbo` en
   **User** y pulsa **Connect**.
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
2. Si el cambio toca modelos o migraciones, haz antes un respaldo: en
   Portainer, reinicia el contenedor `rumbo-backup-1` y revisa en sus logs que
   diga `Respaldo creado`.
3. En Portainer, abre **Stacks > rumbo**.
4. Pulsa **Pull and redeploy** y confirma. Activa **Re-pull image and
   redeploy** solo si cambió la imagen de Postgres; para cambios de la app no
   hace falta.
5. Portainer descarga el código nuevo, reconstruye `web` y lo reinicia. Las
   migraciones nuevas se aplican solas al arrancar.

Los datos de Postgres viven en el volumen `rumbo_pgdata` y se conservan entre
despliegues, reinicios y aunque el contenedor `db` se recree. No borres ese
volumen.

## Respaldos

El contenedor `backup` ejecuta `pg_dump` al arrancar y luego cada 24 horas.
Arranca después de que `web` aparece como *healthy*, es decir, con las
migraciones ya aplicadas; si `web` no llega a ese estado, `backup` tampoco
arranca. Guarda archivos como `rumbo-2026-11-14_0300.dump` en `BACKUP_DIR` y
borra los que tengan más de `BACKUP_RETENCION_DIAS` días (30 por defecto).

- **Revisar que funciona:** en Portainer, abre los logs de `rumbo-backup-1`.
  Cada respaldo deja una línea `Respaldo creado: ...` o
  `ERROR: no se pudo crear el respaldo`.
- **Respaldo inmediato:** reinicia `rumbo-backup-1`. Hazlo antes de desplegar
  cambios que toquen la base de datos.
- **Copia fuera del NAS:** configura Hyper Backup para copiar la carpeta
  compartida `backups` a un disco USB, otro NAS o la nube. Si el NAS falla, los
  respaldos guardados solo en él se pierden con los datos.

Los respaldos contienen los datos personales de cada cuenta. No los subas al
repositorio ni los compartas.

### Restaurar un respaldo

Restaurar **reemplaza** todos los datos actuales por los del archivo.

1. En Portainer, detén el contenedor `rumbo-web-1` para que nadie escriba
   mientras tanto.
2. Abre la **Console** de `rumbo-backup-1` con `/bin/sh` y pulsa **Connect**.
3. Lista los respaldos y elige uno:

   ```sh
   ls -l /respaldos
   ```

4. Restáuralo, cambiando el nombre del archivo:

   ```sh
   pg_restore --clean --if-exists --no-owner -d "$PGDATABASE" /respaldos/rumbo-2026-11-14_0300.dump
   ```

5. Vuelve a iniciar `rumbo-web-1` y revisa la app.

Prueba una restauración al menos una vez: un respaldo que nunca se restauró no
está garantizado.

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
