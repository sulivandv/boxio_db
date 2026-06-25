"""Repositórios PostgreSQL para operações de estoque.

A UI não deve executar SQL diretamente. Esta camada centraliza consultas,
validações de concorrência e regras transacionais. Em uso multiusuário, isso
facilita manutenção e reduz o risco de inconsistência de saldo.
"""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.postgres.models import Product, StockMovement


class ProductRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_products(self, company_id: UUID) -> list[Product]:
        stmt = select(Product).where(Product.company_id == company_id, Product.active.is_(True)).order_by(Product.name)
        return list(self.session.scalars(stmt))

    def get_for_update(self, product_id: UUID) -> Product:
        """Carrega o produto com bloqueio de linha.

        SELECT FOR UPDATE evita que dois usuários movimentem o mesmo item ao
        mesmo tempo e gravem saldos incorretos.
        """
        stmt = select(Product).where(Product.id == product_id).with_for_update()
        product = self.session.scalar(stmt)
        if product is None:
            raise ValueError("Produto não encontrado.")
        return product


class StockMovementService:
    def __init__(self, session: Session):
        self.session = session
        self.products = ProductRepository(session)

    def move_stock(
        self,
        *,
        company_id: UUID,
        product_id: UUID,
        movement_type: str,
        quantity: Decimal,
        unit_code: str,
        notes: str | None = None,
    ) -> StockMovement:
        if quantity <= 0:
            raise ValueError("A quantidade da movimentação deve ser maior que zero.")

        product = self.products.get_for_update(product_id)
        previous = Decimal(product.current_stock)

        if movement_type in {"entrada", "recebimento_compra", "cadastro_inicial"}:
            resulting = previous + quantity
        elif movement_type == "saida":
            resulting = previous - quantity
            if resulting < 0:
                raise ValueError("Saldo insuficiente para saída de estoque.")
        elif movement_type == "ajuste":
            resulting = quantity
        else:
            raise ValueError(f"Tipo de movimentação inválido: {movement_type}")

        product.current_stock = resulting
        movement = StockMovement(
            company_id=company_id,
            product_id=product_id,
            movement_type=movement_type,
            quantity=quantity,
            unit_code=unit_code,
            converted_quantity=quantity,
            previous_stock=previous,
            resulting_stock=resulting,
            notes=notes,
        )
        self.session.add(movement)
        return movement
