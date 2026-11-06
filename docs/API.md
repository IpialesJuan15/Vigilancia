# API F0

Rutas expuestas por Next.js con prefijo `/api`. FastAPI no publica puerto al host.
OpenAPI: `/api/openapi.json`; documentación: `/api/docs`.

| Método | Ruta API (sin /api) | Acceso |
|---|---|---|
| GET | /health | Público; verifica BD/Redis |
| GET | /auth/csrf | Público; crea cookie HttpOnly y devuelve token |
| GET | /auth/capabilities | Disponibilidad de ORCID |
| POST | /auth/register | Público; crea solo suscriptor; envía verificación |
| POST | /auth/verify-email | Token de un solo uso |
| POST | /auth/verification/resend | Respuesta genérica |
| POST | /auth/login | Correo verificado + contraseña |
| POST | /auth/logout | Sesión; invalida todas las sesiones de la cuenta |
| POST | /auth/password/forgot | Respuesta genérica |
| POST | /auth/password/reset | Token + contraseña nueva |
| GET | /auth/orcid/login | Inicio OAuth Sandbox |
| GET | /auth/orcid/callback | Estado firmado + código OAuth |
| GET | /me | Sesión |
| GET | /reviews | Sesión; lista vacía hasta F1 |
| GET | /public/reviews | Público; lista vacía hasta F3 |
| GET | /admin/users | Administrador; primeras 100 cuentas |
| PATCH | /admin/users/{id}/role | Administrador; cuerpo {role} |

En cada POST/PATCH se requiere `Origin` igual a APP_BASE_URL, cookie CSRF y cabecera
`X-CSRF-Token` con el valor devuelto por GET /auth/csrf. El cliente de frontend ya lo hace.
Los errores usan `{code, message, details}` sin incluir contraseñas, tokens ni trazas.
Las contraseñas nuevas requieren 12–128 caracteres. No hay endpoints de publicación ni DOI en F0.
