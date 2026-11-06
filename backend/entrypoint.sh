#!/bin/sh
set -eu
if [ -z "${JWT_SECRET:-}" ]; then
  # Only the API/migration container generates this; workers read after migrations finish.
  python - <<'PYCODE'
import os, secrets
path = '/state/jwt_secret'
try:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
except FileExistsError:
    pass
else:
    with os.fdopen(fd, 'w') as f:
        f.write(secrets.token_urlsafe(64))
PYCODE
  JWT_SECRET="$(cat /state/jwt_secret)"
  export JWT_SECRET
fi
exec "$@"
