"""İlk admin kullanıcısını oluşturur (auth.register admin-only olduğundan bir
bootstrap yolu gerekir). Kullanım:

    docker compose exec backend python -m app.scripts.bootstrap_admin \\
        --email admin@example.com --password changeme --name "Yönetici"
"""
from __future__ import annotations

import argparse

from app.core.security import hash_password
from app.db.models import User
from app.db.session import SessionLocal


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--name", default="Yönetici")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == args.email).first()
        if existing is not None:
            print(f"Zaten mevcut: {args.email} (role={existing.role})")
            return
        user = User(
            email=args.email,
            hashed_password=hash_password(args.password),
            full_name=args.name,
            role="admin",
        )
        db.add(user)
        db.commit()
        print(f"Admin oluşturuldu: {args.email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
