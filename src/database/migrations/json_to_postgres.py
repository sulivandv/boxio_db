"""Migração inicial de inventory_db.json para PostgreSQL/Neon.

Este script lê o JSON atual do Boxio e grava os dados no PostgreSQL. Ele foi
projetado para ser seguro para iniciantes:
- não apaga o JSON original;
- evita duplicar produtos por SKU dentro da mesma empresa;
- cria cadastros auxiliares quando necessário;
- registra estatísticas no final;
- pode ser executado por linha de comando.

Exemplo:
python -m src.database.migrations.json_to_postgres --json database/inventory_db.json --company "Inovi"
"""
from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

from src.database.postgres.connection import db_session
from src.database.postgres.models import (
    Brand,
    Category,
    Company,
    MeasurementUnit,
    Product,
    ProductSupplierHistory,
    StockLocation,
    Supplier,
)

VALID_UNITS = {"un", "cx", "pc", "ml", "l", "g", "kg", "lb", "mm", "cm", "in"}


def _text(value, default="") -> str:
    return str(value if value is not None else default).strip()


def _decimal(value, default="0") -> Decimal:
    try:
        if value in (None, ""):
            return Decimal(default)
        text = str(value).replace("R$", "").strip()
        # Se vier no padrão brasileiro 1.234,56, converte para 1234.56.
        if "," in text:
            text = text.replace(".", "").replace(",", ".")
        return Decimal(text)
    except Exception:
        return Decimal(default)


def _normalize_sku(raw: str, fallback_number: int) -> str:
    raw = _text(raw).upper().replace(" ", "")
    if raw:
        return raw
    return f"SKU-{fallback_number:05d}"


def _get_or_create(session, model, company_id, name: str):
    name = _text(name, "Não informado").title()
    stmt = select(model).where(model.company_id == company_id, model.name == name)
    item = session.scalar(stmt)
    if item:
        return item
    item = model(company_id=company_id, name=name)
    session.add(item)
    session.flush()
    return item


def _unit_from_quantity_text(quantity_text: str) -> str:
    text = quantity_text.lower()
    if "kg" in text or "kgs" in text:
        return "kg"
    if "ml" in text:
        return "ml"
    if "litro" in text:
        return "l"
    if "g" in text:
        return "g"
    if "caixa" in text:
        return "cx"
    if "pacote" in text:
        return "pc"
    return "un"


def _load_products(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return data
    return data.get("products") or data.get("produtos") or []


def migrate_json_to_postgres(json_path: str | Path, company_name: str = "Inovi") -> dict:
    """Migra produtos, cadastros auxiliares e histórico de fornecedores."""
    path = Path(json_path)
    if not path.exists():
        raise FileNotFoundError(f"JSON não encontrado: {path}")
    products = _load_products(path)
    stats = {"products_created": 0, "products_existing": 0, "supplier_history": 0, "skipped": 0}

    with db_session() as session:
        company = session.scalar(select(Company).where(Company.name == company_name))
        if not company:
            company = Company(name=company_name)
            session.add(company)
            session.flush()

        for unit in VALID_UNITS:
            if not session.get(MeasurementUnit, unit):
                session.add(MeasurementUnit(code=unit, description=unit, fractionable=unit not in {"un", "cx", "pc"}))
        session.flush()

        used_skus: set[str] = set()
        for index, row in enumerate(products, start=1):
            try:
                legacy_id = row.get("sku") or row.get("id de estoque") or row.get("id") or row.get("codigo")
                sku = _normalize_sku(legacy_id, index)
                if sku in used_skus:
                    sku = f"{sku}-{index:03d}"
                used_skus.add(sku)

                existing = session.scalar(select(Product).where(Product.company_id == company.id, Product.sku == sku))
                if existing:
                    product = existing
                    stats["products_existing"] += 1
                else:
                    category = _get_or_create(session, Category, company.id, row.get("categoria") or row.get("item") or "Geral")
                    brand = _get_or_create(session, Brand, company.id, row.get("marca") or "Não informado")
                    location = _get_or_create(session, StockLocation, company.id, row.get("tipo de estoque") or row.get("estoque") or "Principal")
                    quantity_text = _text(row.get("quantidade"))
                    unit_code = row.get("unidade_medida") or row.get("unidade") or _unit_from_quantity_text(quantity_text)
                    unit_code = unit_code if unit_code in VALID_UNITS else "un"
                    name_parts = [row.get("item"), row.get("tipo"), row.get("descricao"), row.get("medida")]
                    name = " ".join(_text(p) for p in name_parts if _text(p)).title() or _text(row.get("nome"), f"Produto {index}")
                    product = Product(
                        company_id=company.id,
                        sku=sku,
                        name=name,
                        category_id=category.id,
                        brand_id=brand.id,
                        stock_location_id=location.id,
                        material_type=_text(row.get("tipo")),
                        unit_code=unit_code,
                        quantity_base=_decimal(row.get("quantidade_base"), "1"),
                        current_stock=_decimal(row.get("estoque_atual") or row.get("nivel de estoque") or row.get("estoque"), "0"),
                        minimum_stock=_decimal(row.get("estoque_minimo") or row.get("nivel de estoque (2 meses)"), "0"),
                        cost_price=_decimal(row.get("preco de custo") or row.get("cost_price") or row.get("valor base"), "0"),
                        sale_price=_decimal(row.get("preco_venda") or row.get("sale_price"), "0"),
                        description=_text(row.get("observacao") or row.get("description")),
                        vendor_name=_text(row.get("nome com vendedor")),
                        active=True,
                    )
                    session.add(product)
                    session.flush()
                    stats["products_created"] += 1

                supplier = _get_or_create(session, Supplier, company.id, row.get("fornecedor") or "Não informado")
                history = ProductSupplierHistory(
                    company_id=company.id,
                    product_id=product.id,
                    supplier_id=supplier.id,
                    quoted_price=_decimal(row.get("valor base"), "0"),
                    paid_price=_decimal(row.get("preco de custo") or row.get("valor base"), "0"),
                    negotiation_status="migrado",
                    notes="Registro migrado do JSON legado.",
                )
                session.add(history)
                stats["supplier_history"] += 1
            except Exception as exc:
                stats["skipped"] += 1
                print(f"[AVISO] Item {index} ignorado: {exc}")
                continue

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Migra dados JSON do Boxio para PostgreSQL/Neon.")
    parser.add_argument("--json", default="database/inventory_db.json", help="Caminho do JSON de origem")
    parser.add_argument("--company", default="Inovi", help="Nome da empresa no banco")
    args = parser.parse_args()
    stats = migrate_json_to_postgres(args.json, args.company)
    print("Migração concluída:")
    for key, value in stats.items():
        print(f"- {key}: {value}")


if __name__ == "__main__":
    main()
