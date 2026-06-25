"""Cria cliente e licença anual pelo terminal.

Uso:
    python scripts/create_license.py "Clínica Exemplo" BOXIO-2026-0001 2027-05-18

Requer:
    DATABASE_URL configurado no .env do license_server.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from app.database import SessionLocal, init_schema
from app.models import Customer, License


def main():
    if len(sys.argv) < 4:
        print('Uso: python scripts/create_license.py "Empresa" CHAVE-LICENCA AAAA-MM-DD')
        raise SystemExit(1)

    company_name = sys.argv[1]
    license_key = sys.argv[2]
    expires_at = sys.argv[3]

    init_schema()
    db = SessionLocal()
    try:
        customer = Customer(company_name=company_name)
        db.add(customer)
        db.flush()

        license = License(
            customer_id=customer.id,
            license_key=license_key,
            expires_at=expires_at,
            plan="profissional",
            max_devices=5,
            max_users=5,
            allowed_modules=["inventory", "purchases", "reports"],
        )
        db.add(license)
        db.commit()
        print("Cliente criado:", customer.id)
        print("Licença criada:", license.license_key)
        print("Validade:", license.expires_at)
    finally:
        db.close()


if __name__ == "__main__":
    main()
