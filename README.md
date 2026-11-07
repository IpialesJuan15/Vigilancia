# LiveSRL

Plataforma web de revisiones sistemáticas de literatura vivas, en español y en modo prueba.
Implementación por fases del [plan maestro](docs/PLAN_MAESTRO.md).

**Estado: F1 implementada y validada.** Carga privada por DOI/PDF, verificación OA/licencia,
lectura de secciones, referencias y tablas, originales privados en MinIO y acceso por curador.
Se probaron tres revisiones reales por DOI y una adicional por PDF; ver [evidencia F1](docs/VALIDACION_F1.md).
La extracción con IA corresponde a F2; vigilancia y publicación se implementan en fases posteriores.
No se crean artículos de ejemplo al arrancar la aplicación.

Para probar en Windows sin ocupar el puerto 3000 de otro proyecto, sigue
[Probar en tu PC](docs/PRUEBA_EN_PC.md).

## Arranque con un comando

Requisitos: Docker Engine y Compose v2; puertos locales 3000 y 8025 disponibles.
Desde la raíz del repositorio:

```sh
docker compose up --build -d --wait
```

El arranque crea las tablas mediante Alembic y una clave aleatoria persistida en el volumen
`auth-state` si no se configura `JWT_SECRET`. No hay administrador ni contraseña predefinidos.
Los servicios se reinician automáticamente salvo la migración, que debe finalizar con éxito.
La interfaz se sirve en el puerto 3000 y el buzón de desarrollo Mailpit en el 8025.
Ambos puertos están restringidos al equipo local. No se envían correos fuera de Mailpit por defecto.

1. Abre la interfaz, pulsa **Crear cuenta** y registra un correo y una contraseña de 12+ caracteres.
2. En Mailpit abre el mensaje de verificación y sigue su enlace.
3. Confirma el correo e inicia sesión: verás **Mis revisiones** y un estado vacío real.
4. **Olvidé mi contraseña** permite comprobar el flujo de recuperación en el mismo buzón.
5. **Cerrar sesión** invalida las sesiones existentes de esa cuenta.

Para otorgar un rol a una cuenta existente y verificada (operación de quien administra el servidor):

```sh
docker compose exec api sh /app/entrypoint.sh python -m app.cli usuario@institucion.edu curator
docker compose exec api sh /app/entrypoint.sh python -m app.cli admin@institucion.edu admin
```

No se permite elegir un rol en el registro. Los cambios de rol y las acciones de acceso quedan
registrados en auditoría; PostgreSQL impide actualizar, borrar o truncar ese registro.
El rol de autor reclamado será una relación con la revisión en una fase posterior.

## ORCID Sandbox

La integración está implementada, pero requiere registrar una aplicación en ORCID Sandbox.
Copia `.env.example` a `.env` sin sobrescribir un archivo existente; configura
`ORCID_CLIENT_ID`, `ORCID_CLIENT_SECRET`, `APP_BASE_URL=http://127.0.0.1:3000` y el callback exacto
`http://127.0.0.1:3000/api/auth/orcid/callback`. Para el perfil de PC se usa el puerto 3001.
ORCID rechaza localhost en su validador: abre también LiveSRL usando 127.0.0.1. Reinicia con `docker compose up -d`.
El botón permanece desactivado y explica el motivo cuando faltan las credenciales.
Nunca compartas valores secretos en incidencias ni commits.

Solo se solicita `/authenticate`; se verifica el estado OAuth firmado, caducidad y código.
No se infiere un correo verificado desde ORCID ni se fusionan identidades por nombre/correo.
Una cuenta ORCID comienza como suscriptor, sin correo; la vinculación de cuentas es trabajo futuro.

## Pruebas

Backend (Python 3.12 y uv):

```sh
cd backend
uv sync --frozen
uv run ruff check app alembic
uv run ruff format --check app alembic
uv run mypy app --exclude app/tests
uv run pytest --cov=app --cov-report=term-missing --cov-fail-under=70
```

Las pruebas aisladas usan SQLite y respuestas del proveedor exclusivamente dentro de pruebas.
La integración de navegador usa PostgreSQL, Redis, Celery y SMTP reales del Compose:

```sh
cd frontend
npm ci
npm run lint
npm run typecheck
npm run build
npx playwright install --with-deps chromium
npm run test:e2e
```

Si ya hay Chromium instalado, configura `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` con su ruta.
Las pruebas crean cuentas de prueba con correos únicos en el entorno local. Usa una instalación
separada de pruebas si necesitas mantener limpia tu base de desarrollo.
El flujo de prueba nunca contacta autores ni publica DOI.

Comprobaciones de servicios:

```sh
docker compose ps -a
docker compose exec api sh /app/entrypoint.sh alembic check
docker compose exec worker sh /app/entrypoint.sh celery -A app.tasks:celery inspect ping
```

La API documenta sus rutas en `/api/docs` a través de la interfaz; la disponibilidad de BD y
Redis se verifica en `/api/health`. Para detener sin perder datos: `docker compose down`.
No uses `down -v` si deseas conservar cuentas, auditoría y clave de firma.

## Entorno administrado en la nube

Usa el checkout existente; cada tarea ya está aislada, no necesitas otro worktree.
Para conservar la verificación TLS del proxy durante la compilación:

```sh
docker compose -f docker-compose.yml -f compose.cloud.yml up --build -d --wait
```

El override monta el certificado del entorno como secreto de compilación y para ORCID en la API.
No se incorpora el certificado a las imágenes. Para comandos locales con caché de solo lectura,
usa `UV_CACHE_DIR=/workspace/.cache/uv` y `npm --cache /workspace/.cache/npm`.

## Documentación

- [Decisiones y límites](docs/DECISIONES.md)
- [Arquitectura](docs/ARQUITECTURA.md)
- [API](docs/API.md)
- [Despliegue](docs/DESPLIEGUE.md)
- [Validación de F0](docs/VALIDACION_F0.md)
- [Evaluación](docs/EVALUACION.md)

La sección 24 del plan requiere confirmar cada fase antes de avanzar a la siguiente.
