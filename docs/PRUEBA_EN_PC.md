# Probar en tu PC junto al proyecto de Claude

Estos comandos son para PowerShell en Windows, con Git y Docker Desktop instalados.
Abre Docker Desktop y espera que el motor esté funcionando.

```powershell
cd ([Environment]::GetFolderPath('Desktop'))
git clone --branch livesrl-f0 https://github.com/IpialesJuan15/Vigilancia.git LiveSRL-Codex
cd LiveSRL-Codex
Copy-Item .env.pc.example .env
docker compose -p livesrl-codex up --build -d --wait
```

Usa una carpeta nueva: `LiveSRL-Codex`. Si ya existe, no sobrescribas sus archivos;
elige otro nombre para el clon. Si el repositorio es privado, Git pedirá iniciar sesión
con tu cuenta de GitHub mediante su gestor de credenciales.

Abre en tu navegador:

- Aplicación: `http://localhost:3001`.
- Buzón de pruebas: `http://localhost:8026`.

Crea una cuenta con contraseña de 12+ caracteres. Abre el mensaje en el buzón de pruebas,
sigue su enlace, confirma el correo y después inicia sesión en la aplicación.
No necesitas una clave de IA ni ORCID para esta prueba. Todavía no se pueden cargar artículos.

El nombre de proyecto Compose `livesrl-codex` mantiene sus contenedores, red y volúmenes
separados de otros proyectos Docker. Los puertos 3001/8026 evitan usar el 3000 de Claude.
El puerto 3000 dentro del contenedor es independiente del puerto 3001 de tu computadora.

Para actualizar más adelante, desde esa carpeta:

```powershell
git pull --ff-only origin livesrl-f0
docker compose -p livesrl-codex up --build -d --wait
```

Para detener sin borrar tus datos:

```powershell
docker compose -p livesrl-codex down
```

Si falla el arranque, consulta `docker compose -p livesrl-codex ps -a` y
`docker compose -p livesrl-codex logs --tail=80`. No publiques archivos `.env` ni secretos.
