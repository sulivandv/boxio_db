"""Modelos ORM principais do banco PostgreSQL.

O projeto ainda pode manter partes da UI existentes, mas a camada de dados passa
a ter estrutura relacional preparada para multiusuário, auditoria e expansão.
"""
from __future__ import annotations

import uuid
from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def uuid_pk() -> uuid.UUID:
    return uuid.uuid4()


class Company(Base):
    __tablename__ = "companies"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pk)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    document: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Category(Base):
    __tablename__ = "categories"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pk)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (UniqueConstraint("company_id", "name", name="uq_category_company_name"),)


class Brand(Base):
    __tablename__ = "brands"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pk)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(Text, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (UniqueConstraint("company_id", "name", name="uq_brand_company_name"),)


class Supplier(Base):
    __tablename__ = "suppliers"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pk)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(Text, nullable=False)
    contact_name: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(Text)
    website: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (UniqueConstraint("company_id", "name", name="uq_supplier_company_name"),)


class MeasurementUnit(Base):
    __tablename__ = "measurement_units"
    code: Mapped[str] = mapped_column(String(12), primary_key=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    fractionable: Mapped[bool] = mapped_column(Boolean, default=False)
    decimal_precision: Mapped[int] = mapped_column(default=0)
    base_code: Mapped[str | None] = mapped_column(String(12))
    conversion_factor: Mapped[Decimal] = mapped_column(Numeric(18, 6), default=1)


class StockLocation(Base):
    __tablename__ = "stock_locations"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pk)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (UniqueConstraint("company_id", "name", name="uq_location_company_name"),)


class Product(Base):
    __tablename__ = "products"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pk)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"))
    sku: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    category_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"))
    brand_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("brands.id", ondelete="SET NULL"))
    stock_location_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("stock_locations.id", ondelete="SET NULL"))
    material_type: Mapped[str | None] = mapped_column(Text)
    unit_code: Mapped[str] = mapped_column(String(12), ForeignKey("measurement_units.code"), default="un")
    quantity_base: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=1)
    current_stock: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    minimum_stock: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=0)
    cost_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    sale_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    description: Mapped[str | None] = mapped_column(Text)
    vendor_name: Mapped[str | None] = mapped_column(Text)
    controls_expiration: Mapped[bool] = mapped_column(Boolean, default=False)
    expiration_date: Mapped[date | None] = mapped_column(Date)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    category = relationship("Category")
    brand = relationship("Brand")
    location = relationship("StockLocation")
    unit = relationship("MeasurementUnit")

    __table_args__ = (
        UniqueConstraint("company_id", "sku", name="uq_product_company_sku"),
        CheckConstraint("current_stock >= 0", name="ck_product_stock_non_negative"),
        CheckConstraint("quantity_base > 0", name="ck_product_quantity_base_positive"),
    )


class StockMovement(Base):
    __tablename__ = "stock_movements"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pk)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"))
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"))
    movement_type: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit_code: Mapped[str] = mapped_column(String(12), ForeignKey("measurement_units.code"))
    converted_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    previous_stock: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    resulting_stock: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProductSupplierHistory(Base):
    __tablename__ = "product_supplier_history"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pk)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"))
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"))
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="SET NULL"))
    quoted_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    paid_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    quote_date: Mapped[date | None] = mapped_column(Date)
    purchase_date: Mapped[date | None] = mapped_column(Date)
    delivery_days: Mapped[int | None]
    negotiation_status: Mapped[str] = mapped_column(Text, default="cotado")
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid_pk)
    company_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"))
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    action: Mapped[str] = mapped_column(Text, nullable=False)
    old_data: Mapped[dict | None] = mapped_column(JSONB)
    new_data: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
