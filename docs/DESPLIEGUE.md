# Despliegue de prueba

F0 se valida en Docker Compose. No hay despliegue público ni DOI oficiales.
Consulta README para los comandos locales y el override de CA del entorno administrado.

Para una futura instancia staging: terminar F1–F8; configurar proxy HTTPS y dominio,
APP_BASE_URL exacta, COOKIE_SECURE=true, JWT_SECRET aleatoria, contraseña de BD y DATABASE_URL
coherentes, SMTP autenticado con TLS, aplicación ORCID Sandbox con callback exacto y
los proveedores necesarios. Introducir secretos mediante el gestor del proveedor, nunca Git.
El puerto frontend está ligado a loopback para usarse detrás de un proxy en la misma máquina.
Revisar retención de correo de prueba, backups y límite de intentos compartido por el proxy.
No exponer Mailpit, Redis, PostgreSQL, MinIO ni GROBID públicamente.

Backups: usar pg_dump en almacenamiento cifrado con retención y ensayo de restauración
antes de staging; automatización diaria y verificación quedan para F9. Preservar también
objetos y auth-state; no se incluyen datos reales en el repositorio.
