# F1 — Ingesta y lectura validada

Validación: 6 de noviembre de 2026 (America/Guayaquil). El entorno publicado por el usuario
permitió completar las pruebas pendientes. No se modificó ni se volvió a publicar su configuración.
F0 ya tenía confirmación del usuario de acceso ORCID real y Actions en verde.

## Criterio del plan

Se cumple la lectura de tres revisiones sistemáticas OA reales con secciones, referencias y
 tablas legibles. Se usó el recorrido real por API, autenticación, cola Celery, Europe PMC,
PostgreSQL y MinIO/S3. Todas tienen licencia CC BY verificada en los metadatos y en su JATS.

| DOI | Secciones | Referencias | Tablas | Filas |
|---|---:|---:|---:|---:|
| 10.3390/ijms262412164 | 17 | 103 | 2 | 88 |
| 10.3389/fspor.2025.1694648 | 15 | 33 | 2 | 39 |
| 10.1016/j.fochx.2025.103378 | 19 | 69 | 1 | 112 |

Además se cargó un PDF real de PLOS para DOI **10.1371/journal.pone.0337516**: 13 secciones,
60 referencias y 11 fragmentos de tablas detectados por página con GROBID/PyMuPDF. Los
fragmentos del PDF requieren revisión manual: no equivalen necesariamente a 11 tablas
científicas distintas. Se descargó del endpoint público de archivos de PLOS con atribución al DOI.

La evidencia reproducible con títulos, fuentes, formatos, versiones de parser, hashes y muestras
literales se guarda en [f1-live.json](evidence/f1-live.json). Los originales permanecen privados
en MinIO. Su descarga autenticada coincidió byte a byte con el hash del documento procesado.

## Comprobaciones realizadas

- Compilación completa API, frontend y MinIO. MinIO proviene del código oficial, etiqueta
  RELEASE.2025-09-07T16-13-09Z fijada al objeto Git 01ce918d8279a20e4706b96a64396146894adee4.
  Se conservaron TLS y Go.sum; el contenedor incluye la licencia AGPL de MinIO.
- Arranque completo del Compose estándar con override de certificados para esta nube, sin
  almacenamiento local alternativo. MinIO se probó mediante operaciones S3 PUT/GET reales.
- Migraciones hasta 0002 y `alembic check` sin diferencias de esquema.
- 59 pruebas backend aprobadas, cobertura 92,04 %. Ruff y mypy correctos.
- Frontend: ESLint, tipos, formato y build correctos. Suite de 22 pruebas de navegador.
- Verificación adicional de las cuatro revisiones reales, sin respuestas simuladas, a 1440 y
  390 píxeles: títulos, celdas, tablas y referencias visibles, sin desbordamiento de la página.
- Los errores temporales de DNS/transporte/503 se reintentan como máximo tres veces con espera;
  se respeta Retry-After. No se reintentan accesos denegados ni URL privadas.
- Licencias XML: se reconocen enlaces y license_ref de diferentes editoriales. Se conservan
  spans, notas y separación entre párrafos de celdas; las referencias mantienen texto fuente.
- CI del primer avance F1 estaba verde: https://github.com/IpialesJuan15/Vigilancia/actions/runs/42329230787.
  La subida de las correcciones finales inicia otra ejecución; no se da por verde sin observarla.

## Reproducir la validación técnica

Desde la raíz, con Compose arrancado, Python 3.12 y las dependencias de backend:

```sh
backend/.venv/bin/python scripts/validate_f1_live.py
node scripts/validate_f1_render.mjs
```

Para añadir el caso PDF, descargar el artículo público de PLOS indicado arriba y usar
`--pdf /ruta/al/archivo.pdf`. `--reparse` vuelve a leer solo las revisiones del perfil técnico.
El script crea explícitamente una cuenta de curador de pruebas, con contraseña aleatoria que
no imprime ni guarda. No se añaden artículos ficticios ni se registran credenciales en la evidencia.
Las pruebas unitarias y de pantallas sí usan fixtures dentro de tests, separados de esta prueba real.

## Alcance y siguiente fase

F1 registra revisiones privadas por DOI/PDF, comprueba OA/licencia, conserva el original,
permite ver la lectura, reintentar fallos y confirmar licencias restrictivas con auditoría.
La carga exige rol de curador/admin y cada descarga verifica propietario. El cuerpo de los
uploads está limitado antes del procesamiento multipart, además de validar MIME, firma y PDF.

La clasificación científica con IA, la extracción de preguntas y criterios, la corrección del
método y la verificación de citas corresponden a F2. Publicación y catálogo con datos serán F3.
No se afirma que esas fases estén implementadas. Se espera confirmación del usuario antes de F2.
