"""Explicit operator-only role assignment. No default administrator password."""

import argparse

from sqlalchemy import select

from app.db import SessionLocal
from app.models import User
from app.services.auth import audit


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("email")
    parser.add_argument("role", choices=["admin", "curator", "subscriber"])
    args = parser.parse_args()
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == args.email.lower()))
        if not user or not user.email_verified:
            parser.error("La cuenta debe existir y tener el correo verificado")
        audit(db, user, "operator_role_changed", {"role": user.role}, {"role": args.role})
        user.role = args.role
        user.session_version += 1
        db.commit()
        print("Rol actualizado; inicia sesión de nuevo")


if __name__ == "__main__":
    main()
