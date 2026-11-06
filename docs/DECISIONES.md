# Decisiones de implementación

## F0 — Fundaciones

1. El checkout `Vigilancia` es la raíz de LiveSRL; no se agrega un directorio anidado ni un
   worktree. El repositorio estaba vacío y sin commits al comenzar.
2. Se respeta el orden F0–F9. No se presentan ingestión, resultados, vigilancia ni DOI
   como disponibles antes de implementarlos y validarlos. El catálogo y el espacio muestran
   estados vacíos, no registros inventados. Las rutas vacías de catálogo/espacio solo definen
   el contrato inicial; no consultan aún revisiones, cuyo modelo se incorpora en F1.
3. Python 3.12, FastAPI, SQLAlchemy, Alembic, PostgreSQL 16/pgvector, Redis 7, Celery,
   Next.js App Router, React, TypeScript, Tailwind 4 y primitiva de botón al estilo shadcn/ui.
   Inter se empaqueta localmente mediante @fontsource/inter. Nada descarga fuentes en ejecución.
4. Versiones consultadas en los registros oficiales PyPI/npm el 6 de noviembre de 2026;
   dependencias y transitivas quedan fijadas en uv.lock y package-lock.json. TypeScript
   6.0.3 y ESLint 9.39.5 se eligen por compatibilidad con los plugins de Next.js;
   las versiones más recientes TS 7/ESLint 10 no son compatibles con esos plugins.
   ESLint 9 está fuera de soporte: actualizar cuando los plugins soporten ESLint 10.
5. La consulta directa de documentación en fastapi.tiangolo.com, nextjs.org,
   info.orcid.org y docs.docker.com fue rechazada por la política de red. Se documenta
   este límite: no se afirma haber comprobado el contenido inaccesible.
6. Registro público solo como suscriptor. Promoción a curador/administrador mediante CLI
   de operador o endpoint de administrador. No se asigna admin al primer registro.
7. Argon2id para contraseñas. JWT en cookie HttpOnly, SameSite=Lax, expiración 60 min.
   Versión de sesión en BD invalida sesiones al cerrar sesión, cambiar rol o contraseña.
   Cerrar sesión afecta todas las sesiones de la cuenta (elección simple y segura).
8. Todas las escrituras requieren origen exacto y doble token CSRF. CORS restringido.
   Redis aplica límites distribuidos por dirección del par directo; no se confía en
   X-Forwarded-For externo. Con el proxy de Next el límite se comparte entre clientes:
   revisar topología y límites por cuenta en el endurecimiento de F8.
9. Tokens de verificación y recuperación aleatorios de un solo uso, caducidad de una hora,
   almacenados solo mediante digest SHA-256 y consumidos atómicamente. Los mensajes se
   entregan por Celery/SMTP con reintentos. Las respuestas de registro/recuperación son
   genéricas para reducir enumeración de cuentas. El contenido de los tokens no se registra.
10. Sin JWT_SECRET explícita, el arranque genera una clave en volumen local protegido.
    Las imágenes corren como usuarios sin privilegios. HTTPS exige COOKIE_SECURE=true.
    Las credenciales locales de BD son solo de desarrollo y sus puertos no se publican.
11. ORCID solo en sandbox y con scope /authenticate. La integración no crea un correo
    ficticio ni asume que un correo existe o está verificado. No fusiona cuentas por correo.
    No hay credenciales ORCID inyectadas; la aceptación con proveedor real sigue pendiente.
12. Un único borrador por revisión, evidencia y versiones inmutables se implementarán en
    sus fases; no se construyen pantallas de extracción vacías que parezcan operativas.
13. GROBID y MinIO están declarados bajo el perfil `parsing`: no son requisitos de F0.
    Se arrancarán y validarán en F1 antes de declarar el parsing funcional. Docling, LLM,
    modelos y proveedores DOI no se instalan hasta sus fases. Beat está listo, sin tareas
    de búsqueda programadas todavía.
14. Auditoría de accesos y cambios de rol almacenada en una tabla con trigger PostgreSQL
    que rechaza UPDATE/DELETE/TRUNCATE. El operador de BD conserva privilegios de migración;
    no equivale a almacenamiento inviolable frente al administrador de infraestructura.
15. Tests unitarios/integración aislada con SQLite, contratos OAuth simulados solo en tests;
    navegador contra servicios reales de Compose. El ensayo SUS y el flujo de candidatos
    en 10 minutos corresponden a fases posteriores con investigadores reales.
16. CI definido con lint, tipos, cobertura mínima 70 %, build, migraciones y pruebas de
    navegador en escritorio/móvil. Su ejecución en GitHub requiere subir el repositorio;
    no se afirman ejecuciones remotas que no se hayan observado. La subida a la rama
    `livesrl-f0` fue autorizada expresamente por el usuario.

## Decisiones del tutor pendientes (sección 23)

Aprobación humana por defecto; no habilitar publicación automática hasta acordarlo.
Licencias NC/ND, creadores de DOI, gold standard, nombre/dominio definitivo y propiedad
intelectual se resolverán antes de las fases donde son necesarios. No bloquean F0.

## Prueba en PC

Se agregan APP_PORT y MAILPIT_PORT configurables, y `.env.pc.example` para los puertos
3001/8026. El proyecto Compose `livesrl-codex` separa contenedores y volúmenes de otros
proyectos del usuario. `.gitattributes` conserva LF en scripts para Docker sobre Windows.
La comprobación de tipos genera primero los tipos de Next.js para funcionar en un clon nuevo.

## Corrección del menú y diseño de F0

- El encabezado ya no contiene un enlace fijo de acceso: consulta la sesión real mediante
  un contexto compartido con el formulario y el espacio privado. El nombre de la cuenta
  sustituye al enlace de acceso solo tras confirmar la identidad.
- Entrar/salir actualiza inmediatamente ese contexto; navegar, recuperar foco y recibir
  cambios de otra pestaña vuelven a validar contra `/me`. Un contador de solicitudes
  impide que respuestas antiguas restauren el estado anterior a un cambio de sesión.
- Un fallo de red tiene estado propio con reintento. Solo una respuesta 401 se trata
  como sesión ausente; mientras se comprueba, no se muestra un acceso anónimo incorrecto.
- Menú de cuenta accesible con cierre mediante Escape o clic exterior, navegación activa,
  tema claro/oscuro persistente y controles adecuados a pantallas estrechas.
- Se rediseñan acceso y espacio privado sin métricas ficticias: estado de correo verificado,
  rol actual, un siguiente paso y aviso explícito de que la carga aún no está disponible.
  No se inicia F1 ni se añaden funciones científicas en este cambio.
