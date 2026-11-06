# Validación observada — F0

Fecha: 6 de noviembre de 2026. Entorno de desarrollo administrado, Python 3.12.14,
Node.js 24.22.1, Docker 29.9.2 y Compose 2.40.3.

## Comprobado

- `uv sync --frozen`: dependencias instaladas con lockfile y verificación TLS activa.
- Ruff (lint y formato) y mypy: correctos.
- `pytest --cov=app --cov-fail-under=70`: **22 pruebas pasan; cobertura 97,68 %**.
  Incluyen registro, roles, contraseñas, correos, CSRF, caducidad/consumo único de tokens,
  revocación, límites de acceso y contratos ORCID. Respuestas simuladas solo en tests.
- Frontend: ESLint, Prettier, TypeScript y build de Next.js pasan.
- Compose con override de CA: construcción y arranque completos, servicios disponibles.
- Migración inicial completada; `alembic check`: sin diferencias con los modelos.
- Extensión pgvector habilitada en PostgreSQL (0.8.7).
- API `/api/health`: BD y Redis responden.
- Worker Celery: responde `pong`; Beat activo sin tareas científicas todavía.
- **16 pruebas Playwright pasan**, ocho escenarios en escritorio y móvil con Chromium:
  páginas en español sin jerga prohibida ni desbordamiento horizontal;
  registro, mensaje entregado a Mailpit por Celery/SMTP, verificación, login y logout;
  protección del espacio privado y pantalla de página no encontrada; menú autenticado al
  navegar/recargar, cierre entre pestañas, sesión caducada, reintento ante error de conexión,
  estado de carga sin enlace anónimo incorrecto, mostrar/ocultar contraseña, tema persistente
  y menú de cuenta contenido en pantallas de 320 px (también probado con Escape).
- PostgreSQL rechaza una actualización del registro de auditoría mediante su trigger.
- Swagger apunta al documento OpenAPI correcto detrás del prefijo `/api`.
- Inspección visual del inicio a 1440 px: jerarquía, paleta académica y contenido legible.
- Configuración Compose base y override pasan `config --quiet`.
- Reejecución de arranque conserva los volúmenes y la migración es idempotente.

## Pendiente y límites

- **ORCID Sandbox real:** adaptador y validación de estado se prueban automáticamente,
  pero no hay ORCID_CLIENT_ID/ORCID_CLIENT_SECRET configurados. Debe registrarse una
  aplicación sandbox, configurar el callback indicado en README y comprobar el acceso
  con una cuenta real de ORCID Sandbox antes de cerrar la aceptación externa de F0.
  No se solicitan secretos en chat ni se inventan credenciales.
- **GitHub Actions:** workflow guardado en GitHub; su resultado remoto no se ha comprobado.
  Los comandos de calidad y las pruebas equivalentes se ejecutaron localmente.
- Documentación oficial web de FastAPI, Next.js, ORCID y Docker bloqueada por la red.
  Las versiones se consultaron en registros PyPI/npm. No se desactivó TLS.
- ESLint 9 y TS 6 se fijan por compatibilidad; ESLint 9 está fuera de soporte.
  El runner de FastAPI también avisa de una futura migración de httpx a httpx2.
- La base de desarrollo contiene cuentas creadas exclusivamente por los tests automáticos;
  no hay artículos, revisiones, DOI ni resultados científicos inventados.
- No se evaluaron SUS, métricas científicas ni el flujo de cargar/decidir/publicar en 10 min:
  requieren las fases posteriores y participantes reales.
- GROBID/MinIO (perfil parsing) no se iniciaron: corresponden a F1. No se afirma que
  ingestión, extracción, vigilancia, depósitos DOI o publicación científica funcionen.
- No hay despliegue público ni publicación del entorno. La entrega de código a GitHub
  se realiza en `livesrl-f0`, tras autorización expresa del usuario.

## Reproducir y aprobar la fase

Seguir los comandos de README para `docker compose up --build -d --wait`, backend y
navegador. Verificar manualmente registro/correo/login y configurar ORCID Sandbox.
Resolver la comprobación externa y confirmar F0 antes de iniciar F1, tal como pide la
sección 24 del plan maestro. Las fases F1–F9 no están implementadas en esta entrega.

## Verificación de la corrección visual

La suite completa de 16 pruebas se ejecutó contra una instalación aislada en los puertos
3001/8026, con PostgreSQL, Redis, Celery y SMTP reales para el flujo de cuenta.
Los errores de red, sesión caducada y el caso de pantalla estrecha se simulan únicamente
en pruebas automáticas. Pasaron ESLint, Prettier, TypeScript y la compilación Docker de Next.js.
Se inspeccionaron capturas del acceso y del espacio privado en escritorio/móvil y tema oscuro.
El ajuste no incorpora la ingesta de F1. Para actualizar el clon de PC, seguir PRUEBA_EN_PC.md.
