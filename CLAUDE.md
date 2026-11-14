# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Rumbo

App para hacer seguimiento al proceso de pérdida de peso: registro de peso,
alimentación y pasos, con gráficas. Se comparte con otra persona (mi hermana).

## Estado actual
- El repositorio solo contiene el README; todavía no hay código, comandos de
  build ni tests. Actualiza este archivo con comandos y arquitectura cuando
  existan.

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
