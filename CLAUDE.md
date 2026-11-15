# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Rumbo

App para hacer seguimiento al proceso de pérdida de peso: registro de peso,
alimentación y pasos, con gráficas. Se comparte con otra persona (mi hermana).

## Comandos
- Entorno local: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
- Servidor: `DEBUG=True .venv/bin/python manage.py runserver`
- Tests: `DEBUG=True .venv/bin/python manage.py test`
- Un test: `DEBUG=True .venv/bin/python manage.py test seguimiento.tests.test_vistas.DiaTests.test_suma_calorias_del_dia`
- Migraciones: `DEBUG=True .venv/bin/python manage.py makemigrations seguimiento`
- `DEBUG=True` hace falta en local: sin él, la configuración exige `SECRET_KEY`
  y usa el almacenamiento de WhiteNoise con manifiesto, que necesita
  `collectstatic`.

## Arquitectura
- `config/settings.py` lee todo de variables de entorno. Sin `POSTGRES_DB` usa
  SQLite (desarrollo y tests); con ella, Postgres.
- Una sola app, `seguimiento`: modelos `Perfil` (uno por usuario),
  `RegistroDiario` (uno por usuario y fecha) y `Comida` (varias por día, ligadas
  a usuario y fecha, no al registro).
- `seguimiento/calculos.py` tiene los cálculos puros (promedio móvil de 7 días,
  pasos de la semana, progreso hacia la meta). Las vistas consultan la base y
  les pasan dicts.
- Las vistas usan `perfil_requerido`, que exige login y un perfil creado.
  Toda consulta filtra por `usuario=request.user`.
- Plantillas de Django sin frameworks: `templates/` (base, login) y
  `seguimiento/templates/`. CSS propio en `static/css/rumbo.css` con tokens de
  color para modo claro y oscuro; `static/js/tema.js` guarda la elección.
- Las gráficas reciben los datos con `json_script` y las dibuja
  `static/js/graficas.js` con Chart.js guardado en `static/vendor/`.
- Docker: `entrypoint.sh` corre `migrate` y `collectstatic` antes de Gunicorn.
  `docker-compose.yml` usa `${VAR}` para que Portainer cargue las variables.
- El servicio `backup` del compose usa la imagen `postgres:17` con el script de
  respaldo escrito en `command` (Portainer CE no monta archivos del repo; en el
  compose los `$` del script se escriben `$$`). Guarda en `BACKUP_DIR`.

## Stack
- Backend: Django + Python
- Base de datos: PostgreSQL
- Despliegue: Docker sobre un NAS Synology (autoalojado)
- Repo en GitHub, trabajo por SSH

## Flujo de trabajo
- Nunca trabajes directamente en `main`: crea una rama por función o arreglo
  (`feat/...`, `fix/...`).
- Haz commits pequeños, uno por cambio lógico, con mensajes en español.
- Solo haz commit, push o PR cuando yo lo pida explícitamente.
- Antes de abrir un PR, corre los tests y revisa los cambios con code-review.
- Para funciones nuevas, usa feature-dev. Para interfaces y gráficas, usa
  frontend-design.
- Si el cambio es grande o ambiguo, propón primero un plan y espera mi
  aprobación antes de editar archivos.

## Seguridad
- Nunca subas `.env`, credenciales de Postgres, `SECRET_KEY`, volúmenes de
  datos (`pgdata/` o similares) ni dumps (`*.sql`, `*.dump`).
- Lee la configuración sensible desde variables de entorno. Mantén un
  `.env.example` con los nombres de las variables y sin valores reales.
- Antes del primer commit, verifica que el `.gitignore` cubra todo lo anterior.
- Los datos de peso y alimentación son personales: no los imprimas en logs
  ni los pongas en ejemplos o tests con datos reales.

## Código
- Sigue las convenciones de Django (apps separadas, modelos con migraciones,
  vistas simples).
- Cada cambio en modelos debe incluir su migración.
- Escribe tests para la lógica nueva y no rompas los existentes.
- No agregues dependencias sin avisarme y sin actualizar `requirements.txt`.
- Prefiere soluciones simples sobre abstracciones innecesarias.

## Comunicación
- Respóndeme en español.
- Explica brevemente qué vas a cambiar antes de hacerlo.
