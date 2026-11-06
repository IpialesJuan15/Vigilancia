# Arquitectura

El navegador consume Next.js (App Router). El proxy `/api/*` reenvía a FastAPI dentro de
la red de Compose; así el navegador conserva un único origen para cookies y CSRF.
FastAPI usa SQLAlchemy y PostgreSQL con pgvector; Alembic se ejecuta antes de servir.
Celery entrega correos a Mailpit usando Redis como broker. Beat inicia sin tareas científicas
hasta F4. Los volúmenes conservan BD, Redis y clave de firma; los procesos se reinician.

F0 contiene módulos de autenticación, esquemas, seguridad, modelos, tareas y auditoría.
Las carpetas ai/sources/doi/reports/evaluation reservan la separación del plan sin
implementar proveedores ficticios. GROBID y MinIO se habilitarán con el perfil `parsing`.

F1 introduce living_reviews y documento interno. F2 incorpora adaptadores LLM/embeddings,
prompts versionados y verificación de citas. Las fases siguientes añaden resultados,
vigilancia, cribado, publicación, notificaciones y evaluación en ese orden.
