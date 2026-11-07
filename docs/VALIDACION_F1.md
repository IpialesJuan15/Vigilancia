# F1 — Ingesta y lectura (en desarrollo)

F0 se cierra con la confirmación del usuario de GitHub Actions en verde y del acceso
real a ORCID Sandbox en su PC. Sus credenciales siguen siendo locales; no se copiaron al chat.

Implementado en F1: carga privada por DOI y PDF opcional; comprobación OA y licencia mediante
Europe PMC/OpenAlex; documento interno con secciones, referencias y celdas; conservación del
archivo y su digest; confirmación explícita de licencias NC/ND; progreso, reintento, auditoría,
duplicados por DOI/título y autorización por propietario/rol. El PDF subido debe contener su DOI.
La clasificación científica y extracción de método con IA son F2, todavía pendientes.

## Evidencia

- Backend: suite de autenticación e ingesta con cobertura mínima exigida del 70 %.
  Ver resultado de la última ejecución al final de este documento.
- Frontend: lint, tipos y build correctos; 22 pruebas Playwright pasan en escritorio/móvil.
- Las pruebas de nuevas pantallas usan respuestas simuladas exclusivamente dentro de tests.
  No demuestran por sí solas conectividad con las fuentes ni publicación científica.
- Migración 0002 aplicada en PostgreSQL; `alembic check` sin diferencias con los modelos.
- GROBID 0.8.2 + PyMuPDF respondieron sobre un PDF generado exclusivamente como fixture
  automático: una sección, una referencia y una tabla leídas. No es un artículo real.
- GROBID necesita `-XX:-UseContainerSupport -Xmx2g` en este Docker anidado; el ajuste está
  en compose.cloud.yml. Los servicios internos se excluyen del proxy mediante NO_PROXY.
- Para validar lo independiente de MinIO se usó compose.local-storage.yml: archivos locales
  privados en auth-state. El almacenamiento S3 aún no está verificado en este entorno.

## Bloqueos externos actuales

La política del proxy rechaza www.ebi.ac.uk y api.openalex.org. Tampoco permite
storage.googleapis.com, destino de descargas de módulos Go requeridos al compilar MinIO.
Los dominios se guardaron en el borrador del entorno; guardarlo no los aplica automáticamente.
El usuario debe revisar y guardar el borrador de red en ajustes del entorno. Publicar hace
reutilizable la configuración cuando la interfaz lo permita y la conversación esté inactiva.
Después se debe comprobar la política efectiva y repetir con conexiones nuevas.

Las imágenes probadas de minio/minio no se pudieron descargar. Se preparó un Dockerfile
con código oficial de MinIO, etiqueta RELEASE.2025-09-07T16-13-09Z fijada al objeto Git
01ce918d8279a20e4706b96a64396146894adee4, verificación TLS y Go.sum. La compilación
sigue bloqueada por el dominio anterior. No se cambiaron checksums ni se desactivó TLS.

**F1 no está aceptada aún:** faltan la compilación y prueba real de MinIO/S3, el arranque
estándar completo de Compose y tres revisiones sistemáticas OA reales con secciones,
referencias y tablas legibles. No se han inventado ni sustituido por fixtures esos resultados.
No se inicia F2 mientras estén pendientes.

## Acceso del curador en la PC

El registro público sigue creando suscriptores. El operador de su propia instalación puede
asignar un rol a una cuenta ya verificada por correo u ORCID:

```cmd
docker compose -p livesrl-codex exec api sh /app/entrypoint.sh python -m app.cli TU_ORCID curator
```

Después se vuelve a iniciar sesión. La promoción queda auditada e invalida las sesiones
anteriores. Las revisiones cargadas son privadas; el catálogo público corresponde a F3.
No se deben compartir secretos del archivo .env.

Última ejecución: **54 pruebas backend aprobadas, cobertura 92,72 %**.
Incluye límites de cuerpo HTTP antes de almacenar multipart, incluso sin Content-Length fiable.
