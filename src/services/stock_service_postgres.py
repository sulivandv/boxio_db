"""Serviço de estoque usando PostgreSQL/Neon como fonte principal.

Este módulo substitui a dependência direta do JSON quando BOXIO_DB_MODE=postgresql.
Ele mantém a mesma interface pública usada pela UI antiga, mas traduz os dados
relacionais do PostgreSQL para os dicionários já esperados pelas telas PySide.

Objetivos:
- Ler e gravar CRUD diretamente no banco online.
- Manter compatibilidade com a interface existente durante a transição.
- Preservar JSON apenas como fallback, nunca como fonte principal em produção.
"""
from __future__ import annotations

import json
import re
import uuid
from uuid import UUID
import threading
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import text

from src.database.postgres.connection import db_session, engine
from src.services.local_cache import LocalCache
from src.domain.units import is_fractional, round_value
from src.core.version import APP_VERSION

LOWER_WORDS = {"de", "da", "do", "das", "dos", "e", "em", "com", "para", "por"}
FINAL_PURCHASE_STATUSES = {"Finalizado", "Cancelado", "Rejeitado", "Compra Recebida Integralmente", "Item devolvido", "Troca recebida"}
ACTIVE_PURCHASE_STATUSES = {
    "Solicitação Criada", "Em Análise", "Aguardando Aprovação", "Aguardando Pedido",
    "Pedido Realizado", "Compra Parcial Recebida", "Pendente de devolução", "Aguardando coleta do fornecedor"
}


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _dt_to_iso(v) -> str:
    if not v:
        return ""
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    return str(v)


def _dec(v) -> Decimal:
    if v in (None, ""):
        return Decimal("0")
    return Decimal(str(v))



def is_uuid(value: str | None) -> bool:
    """Valida se uma string pode ser usada como UUID no PostgreSQL.

    Evita enviar identificadores temporários ou legados, como ``purchase_*``
    ou ``tmp-*``, para colunas UUID do banco. Quando isso acontecia no fluxo
    de recebimento de compra, o PostgreSQL retornava erro técnico para o
    usuário.
    """
    if not value:
        return False
    try:
        UUID(str(value))
        return True
    except Exception:
        return False


def uuid_or_none(value: str | None) -> str | None:
    """Retorna UUID válido ou None para evitar erro em colunas UUID.

    Alguns dados legados vindos do JSON/cache tinham IDs temporários como
    ``resp-padrao``. Enviar esses textos para PostgreSQL gera
    ``invalid input syntax for type uuid``. Este helper normaliza esses casos.
    """
    return str(value) if is_uuid(value) else None


def user_friendly_db_error(exc: Exception) -> str:
    """Converte erros técnicos comuns do banco em mensagens compreensíveis."""
    raw = str(exc)
    low = raw.lower()
    if "invalid input syntax for type uuid" in low or "invalid input syntax" in low:
        return "Não foi possível concluir a operação porque há um vínculo interno inválido ou desatualizado. Atualize a tela e tente novamente."
    if "violates foreign key constraint" in low:
        return "Não foi possível salvar porque um dos registros vinculados não existe mais ou está desatualizado."
    if "duplicate key" in low or "unique constraint" in low:
        return "Já existe um registro com essas informações. Verifique o código/SKU e tente novamente."
    if "could not determine data type" in low or "ambiguousparameter" in low:
        return "Não foi possível validar os dados enviados ao banco. Atualize a tela e tente novamente."
    return raw

def title_pt(text: str) -> str:
    text = (text or "").strip()
    parts = re.split(r"(\s+)", text.lower())
    out = []
    for p in parts:
        if p.isspace():
            out.append(p)
        elif p in LOWER_WORDS:
            out.append(p)
        else:
            out.append(p[:1].upper() + p[1:])
    return "".join(out).strip()


def slug_prefix(text: str, size: int = 3) -> str:
    clean = re.sub(r"[^A-Za-zÀ-ÿ0-9 ]+", " ", text or "").strip()
    words = [w for w in clean.split() if w.lower() not in LOWER_WORDS]
    if not words:
        return "PRO"
    if len(words) == 1:
        return re.sub(r"[^A-Za-z0-9]", "", words[0]).upper()[:size].ljust(size, "X")
    return "".join(re.sub(r"[^A-Za-z0-9]", "", w)[0].upper() for w in words[:size]).ljust(size, "X")


class StockServicePostgres:
    """Implementa a API do serviço antigo usando tabelas PostgreSQL do Boxio."""

    reference_map = {
        "categories": {"table": "categories", "prefix": "cat"},
        "brands": {"table": "brands", "prefix": "mar"},
        "suppliers": {"table": "suppliers", "prefix": "for"},
        "warehouses": {"table": "stock_locations", "prefix": "est"},
        "responsibles": {"table": "users_app", "prefix": "resp"},
    }

    def __init__(self):
        self.local_cache = LocalCache()
        # Evita usar snapshots antigos criados por versões anteriores da camada
        # PostgreSQL, que podiam conter IDs temporários herdados do JSON.
        if self.local_cache.get_meta("cache_app_version") != APP_VERSION:
            self.local_cache.clear_all()
            self.local_cache.set_meta("cache_app_version", APP_VERSION)
        self.company_id = self.local_cache.get_meta("company_id") or self._ensure_company("Inovi")
        self.local_cache.set_meta("company_id", self.company_id)
        self._cache: dict[str, Any] = {}
        self._cache_time: dict[str, datetime] = {}
        # Cache em RAM para a sessão atual e cache SQLite local para abertura
        # instantânea de páginas já sincronizadas. O PostgreSQL/Neon permanece
        # como fonte oficial e é sincronizado em segundo plano.
        self._cache_ttl_seconds = 20
        self._sync_lock = threading.Lock()
        self._sync_thread: threading.Thread | None = None
        self._ensure_runtime_schema()
        self._ensure_default_records()

    def _cache_get(self, key: str):
        created = self._cache_time.get(key)
        if created and key in self._cache and datetime.now() - created < timedelta(seconds=self._cache_ttl_seconds):
            return self._cache[key]
        return None

    def _cache_set(self, key: str, value):
        self._cache[key] = value
        self._cache_time[key] = datetime.now()
        return value

    def _clear_cache(self) -> None:
        """Limpa caches leves após gravações no banco."""
        self._cache.clear()
        self._cache_time.clear()

    def _invalidate_domain_cache(self, *collections: str) -> None:
        """Invalida cache de RAM e SQLite das coleções alteradas."""
        self._clear_cache()
        self.local_cache.invalidate(*collections)

    def sync_remote_cache(self, force: bool = False) -> None:
        """Sincroniza snapshots principais do Neon para o cache local SQLite.

        Este método deve rodar fora da thread principal da UI. Ele evita que a
        navegação dependa de consultas remotas repetidas e prepara o sistema
        para a estratégia offline-first/cache-first usada em ERPs modernos.
        """
        with self._sync_lock:
            self.local_cache.set_collection("products", self._products_remote())
            for name in ["categories", "brands", "suppliers", "warehouses", "responsibles"]:
                self.local_cache.set_collection(name, self._references_remote(name))
            self.local_cache.set_collection("recent_movements", self._recent_movements_remote(500))
            self.local_cache.set_collection("purchase_requests", self._purchase_requests_remote())
            self.local_cache.set_meta("last_sync", now_iso())

    def sync_remote_cache_async(self) -> None:
        """Inicia sincronização em background sem travar digitação ou cliques."""
        if self._sync_thread and self._sync_thread.is_alive():
            return
        self._sync_thread = threading.Thread(target=self.sync_remote_cache, kwargs={"force": False}, daemon=True)
        self._sync_thread.start()

    # ------------------------------------------------------------------
    # Infraestrutura e helpers internos
    # ------------------------------------------------------------------
    def _scalar(self, sql: str, params: dict | None = None):
        with engine.connect() as conn:
            return conn.execute(text(sql), params or {}).scalar_one_or_none()

    def _rows(self, sql: str, params: dict | None = None) -> list[dict]:
        with engine.connect() as conn:
            return [dict(r) for r in conn.execute(text(sql), params or {}).mappings().all()]

    def _ensure_company(self, name: str) -> str:
        with db_session() as session:
            row = session.execute(text("SELECT id FROM companies WHERE lower(name)=lower(:name) LIMIT 1"), {"name": name}).scalar_one_or_none()
            if row:
                return str(row)
            new_id = session.execute(text("INSERT INTO companies (name) VALUES (:name) RETURNING id"), {"name": name}).scalar_one()
            return str(new_id)

    def _ensure_default_records(self) -> None:
        # Garante dados-base usados pelas combos da interface.
        self.create_reference("warehouses", "Estoque Principal", save=False, audit=False)
        self.create_reference("responsibles", "Responsável Padrão", save=False, audit=False)
        self._ensure_units()

    def _ensure_runtime_schema(self) -> None:
        """Cria estruturas complementares usadas por versões novas do app.

        Essa proteção evita falha quando o usuário atualiza o executável antes
        de rodar manualmente novas migrations SQL no Neon.
        """
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS supplier_return_requests (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    company_id UUID REFERENCES companies(id) ON DELETE CASCADE,
                    purchase_request_id UUID REFERENCES purchase_requests(id) ON DELETE SET NULL,
                    product_id UUID REFERENCES products(id) ON DELETE SET NULL,
                    supplier_id UUID REFERENCES suppliers(id) ON DELETE SET NULL,
                    quantity NUMERIC(18,4) NOT NULL CHECK (quantity > 0),
                    unit_code TEXT REFERENCES measurement_units(code),
                    reason TEXT,
                    status TEXT NOT NULL DEFAULT 'Pendente de devolução',
                    notes TEXT,
                    requested_by UUID REFERENCES users_app(id) ON DELETE SET NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    finalized_at TIMESTAMPTZ
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_return_requests_purchase ON supplier_return_requests(purchase_request_id, created_at DESC)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_return_requests_status ON supplier_return_requests(company_id, status, updated_at DESC)"))

    def _ensure_units(self) -> None:
        units = [
            ("un", "Unidade", False, 0, "un", 1), ("cx", "Caixa", False, 0, "cx", 1),
            ("pc", "Pacote", False, 0, "pc", 1), ("ml", "Mililitros", True, 2, "ml", 1),
            ("l", "Litros", True, 3, "ml", 1000), ("g", "Gramas", True, 2, "g", 1),
            ("kg", "Quilogramas", True, 3, "g", 1000), ("lb", "Libras", True, 3, "g", 453.59237),
            ("mm", "Milímetros", True, 2, "mm", 1), ("cm", "Centímetros", True, 2, "mm", 10),
            ("in", "Polegadas", True, 3, "mm", 25.4),
        ]
        with db_session() as session:
            for code, desc, frac, prec, base, factor in units:
                session.execute(text("""
                    INSERT INTO measurement_units (code, description, fractionable, decimal_precision, base_code, conversion_factor)
                    VALUES (:code,:desc,:frac,:prec,:base,:factor)
                    ON CONFLICT (code) DO NOTHING
                """), {"code": code, "desc": desc, "frac": frac, "prec": prec, "base": base, "factor": factor})

    def _status_for_product(self, product_id: str) -> str:
        row = self._rows("""
            SELECT status FROM purchase_requests
            WHERE product_id=:pid AND status NOT IN ('Finalizado','Cancelado','Rejeitado','Compra Recebida Integralmente')
            ORDER BY updated_at DESC NULLS LAST, created_at DESC LIMIT 1
        """, {"pid": product_id})
        return row[0]["status"] if row else ""

    def _product_from_row(self, r: dict) -> dict:
        return {
            "id": str(r.get("id")),
            "sku": r.get("sku") or "",
            "nome": r.get("name") or "",
            "descricao": r.get("description") or "",
            "categoria_id": str(r.get("category_id") or ""),
            "marca_id": str(r.get("brand_id") or ""),
            "fornecedor_id": str(r.get("supplier_id") or ""),
            "multiestoque_id": str(r.get("stock_location_id") or ""),
            "tipo_material": r.get("material_type") or "",
            "unidade_medida": r.get("unit_code") or "un",
            "quantidade_base": float(r.get("quantity_base") or 1),
            "estoque_atual": float(r.get("current_stock") or 0),
            "estoque_minimo": float(r.get("minimum_stock") or 0),
            "preco_custo": float(r.get("cost_price") or 0),
            "preco_venda": float(r.get("sale_price") or 0),
            "controla_lote": bool(r.get("controls_batch")),
            "controla_validade": bool(r.get("controls_expiration")),
            "data_validade": _dt_to_iso(r.get("expiration_date")),
            "controla_serial": bool(r.get("controls_serial")),
            "ativo": bool(r.get("active")),
            "compra_status": r.get("purchase_status") or "",
            "ultima_solicitacao_compra_id": "",
            "criado_em": _dt_to_iso(r.get("created_at")),
            "atualizado_em": _dt_to_iso(r.get("updated_at")),
        }

    def _ref_from_row(self, table: str, r: dict) -> dict:
        return {
            "id": str(r.get("id")),
            "nome": r.get("name") or "",
            "descricao": r.get("description") or r.get("notes") or "",
            "ativo": bool(r.get("active", True)),
            "origem": "postgresql",
            "criado_em": _dt_to_iso(r.get("created_at")),
            "atualizado_em": _dt_to_iso(r.get("updated_at") or r.get("created_at")),
        }

    # ------------------------------------------------------------------
    # Referências, unidades e nomes
    # ------------------------------------------------------------------
    def units(self) -> list[dict]:
        cached = self._cache_get("units")
        if cached is not None:
            return cached
        rows = self._rows("SELECT code, description, fractionable, decimal_precision, base_code, conversion_factor FROM measurement_units ORDER BY code")
        data = [
            {"codigo": r["code"], "descricao": r["description"], "fracionavel": bool(r["fractionable"]),
             "precisao_decimal": int(r["decimal_precision"] or 0), "ativo": True,
             "dimensao": r.get("base_code") or r["code"], "quantidade_base_padrao": 1.0}
            for r in rows
        ]
        return self._cache_set("units", data)

    def unit(self, code: str) -> dict:
        return next((u for u in self.units() if u["codigo"] == code), {})

    def unit_label(self, code: str) -> str:
        u = self.unit(code)
        return f"{u.get('codigo', code)} - {u.get('descricao', '')}".strip(" -")

    def _references_remote(self, table: str) -> list[dict]:
        meta = self.reference_map[table]
        db_table = meta["table"]
        if table == "responsibles":
            rows = self._rows("SELECT id, name, active, created_at, updated_at, NULL::text AS description FROM users_app WHERE company_id=:cid AND active=TRUE ORDER BY name", {"cid": self.company_id})
        elif table == "suppliers":
            rows = self._rows("SELECT id, name, active, created_at, updated_at, notes AS description FROM suppliers WHERE company_id=:cid AND active=TRUE ORDER BY name", {"cid": self.company_id})
        elif table == "brands":
            rows = self._rows("SELECT id, name, active, created_at, updated_at, NULL::text AS description FROM brands WHERE company_id=:cid AND active=TRUE ORDER BY name", {"cid": self.company_id})
        else:
            rows = self._rows(f"SELECT id, name, active, created_at, updated_at, description FROM {db_table} WHERE company_id=:cid AND active=TRUE ORDER BY name", {"cid": self.company_id})
        return [self._ref_from_row(table, r) for r in rows]

    def _references(self, table: str) -> list[dict]:
        cache_key = f"references:{table}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached
        local = self.local_cache.get_collection(table)
        if local is not None:
            return self._cache_set(cache_key, local)
        data = self._references_remote(table)
        self.local_cache.set_collection(table, data)
        return self._cache_set(cache_key, data)

    def brands(self) -> list[dict]: return self._references("brands")
    def responsibles(self) -> list[dict]: return self._references("responsibles")
    def warehouses(self) -> list[dict]: return self._references("warehouses")
    def suppliers(self) -> list[dict]: return self._references("suppliers")
    def categories(self) -> list[dict]: return self._references("categories")

    def brand_name(self, brand_id: str) -> str: return next((b["nome"] for b in self.brands() if b["id"] == str(brand_id)), "")
    def warehouse_name(self, warehouse_id: str) -> str: return next((w["nome"] for w in self.warehouses() if w["id"] == str(warehouse_id)), "")
    def responsible_name(self, responsible_id: str) -> str: return next((r["nome"] for r in self.responsibles() if r["id"] == str(responsible_id)), "")
    def category_name(self, category_id: str) -> str: return next((c["nome"] for c in self.categories() if c["id"] == str(category_id)), "")
    def supplier_name(self, supplier_id: str) -> str: return next((s["nome"] for s in self.suppliers() if s["id"] == str(supplier_id)), "")

    def create_reference(self, table: str, name: str, save: bool = True, audit: bool = True) -> dict:
        if table not in self.reference_map:
            raise ValueError("Cadastro de referência inválido.")
        name = title_pt(name)
        if not name:
            raise ValueError("Informe um nome válido.")
        existing = next((r for r in self._references(table) if r["nome"].lower() == name.lower()), None)
        if existing:
            return existing
        meta = self.reference_map[table]
        db_table = meta["table"]
        with db_session() as session:
            if table == "responsibles":
                rid = session.execute(text("""
                    INSERT INTO users_app (company_id, name, role, active)
                    VALUES (:cid, :name, 'operador', TRUE) RETURNING id
                """), {"cid": self.company_id, "name": name}).scalar_one()
            elif db_table == "suppliers":
                rid = session.execute(text("INSERT INTO suppliers (company_id, name, active) VALUES (:cid,:name,TRUE) RETURNING id"), {"cid": self.company_id, "name": name}).scalar_one()
            else:
                rid = session.execute(text(f"INSERT INTO {db_table} (company_id, name, active) VALUES (:cid,:name,TRUE) RETURNING id"), {"cid": self.company_id, "name": name}).scalar_one()
        self._invalidate_domain_cache(table)
        rec = next((r for r in self._references(table) if r["id"] == str(rid)), None)
        return rec or {"id": str(rid), "nome": name, "ativo": True, "origem": "postgresql", "atualizado_em": now_iso()}

    def update_reference(self, table: str, record_id: str, name: str, descricao: str | None = None) -> dict:
        if table not in self.reference_map:
            raise ValueError("Cadastro de referência inválido.")
        name = title_pt(name)
        db_table = self.reference_map[table]["table"]
        with db_session() as session:
            if table == "responsibles":
                session.execute(text("UPDATE users_app SET name=:name, updated_at=now() WHERE id=:id AND company_id=:cid"), {"name": name, "id": record_id, "cid": self.company_id})
            elif db_table == "suppliers":
                session.execute(text("UPDATE suppliers SET name=:name, notes=COALESCE(:desc, notes), updated_at=now() WHERE id=:id AND company_id=:cid"), {"name": name, "desc": descricao, "id": record_id, "cid": self.company_id})
            else:
                session.execute(text(f"UPDATE {db_table} SET name=:name, description=COALESCE(:desc, description), updated_at=now() WHERE id=:id AND company_id=:cid"), {"name": name, "desc": descricao, "id": record_id, "cid": self.company_id})
        self._invalidate_domain_cache(table)
        return next((r for r in self._references(table) if r["id"] == str(record_id)), {"id": record_id, "nome": name})

    def delete_reference(self, table: str, record_id: str) -> None:
        if table not in self.reference_map:
            raise ValueError("Cadastro inválido.")
        usage = {
            "categories": ("products", "category_id"), "brands": ("products", "brand_id"),
            "suppliers": ("product_supplier_history", "supplier_id"), "warehouses": ("products", "stock_location_id"),
            "responsibles": ("stock_movements", "responsible_user_id"),
        }
        db_table = self.reference_map[table]["table"]
        if table in usage:
            t, f = usage[table]
            count = self._scalar(f"SELECT count(*) FROM {t} WHERE {f}=:id", {"id": record_id}) or 0
            if int(count) > 0:
                raise ValueError("Este cadastro está em uso e não pode ser excluído. Desative ou remova os vínculos primeiro.")
        with db_session() as session:
            session.execute(text(f"UPDATE {db_table} SET active=FALSE WHERE id=:id"), {"id": record_id})
        self._invalidate_domain_cache(table)

    # ------------------------------------------------------------------
    # Produtos
    # ------------------------------------------------------------------
    def _products_remote(self) -> list[dict]:
        rows = self._rows("""
            SELECT p.*,
                (
                    SELECT supplier_id FROM product_supplier_history h
                    WHERE h.product_id=p.id AND h.supplier_id IS NOT NULL
                    ORDER BY h.created_at DESC LIMIT 1
                ) AS supplier_id,
                (
                    SELECT status FROM purchase_requests pr
                    WHERE pr.product_id=p.id
                      AND pr.status NOT IN ('Finalizado','Cancelado','Rejeitado','Compra Recebida Integralmente')
                    ORDER BY pr.updated_at DESC NULLS LAST, pr.created_at DESC LIMIT 1
                ) AS purchase_status
            FROM products p
            WHERE p.company_id=:cid AND p.active=TRUE
            ORDER BY p.name
        """, {"cid": self.company_id})
        return [self._product_from_row(r) for r in rows]

    def products(self) -> list[dict]:
        cached = self._cache_get("products")
        if cached is not None:
            return cached
        local = self.local_cache.get_collection("products")
        if local is not None:
            return self._cache_set("products", local)
        data = self._products_remote()
        self.local_cache.set_collection("products", data)
        return self._cache_set("products", data)

    def get_product(self, product_id: str) -> dict | None:
        rows = self._rows("""
            SELECT p.*,
                (SELECT supplier_id FROM product_supplier_history h WHERE h.product_id=p.id AND h.supplier_id IS NOT NULL ORDER BY h.created_at DESC LIMIT 1) AS supplier_id,
                (SELECT status FROM purchase_requests pr WHERE pr.product_id=p.id AND pr.status NOT IN ('Finalizado','Cancelado','Rejeitado','Compra Recebida Integralmente') ORDER BY pr.updated_at DESC NULLS LAST, pr.created_at DESC LIMIT 1) AS purchase_status
            FROM products p
            WHERE p.id=:id AND p.company_id=:cid AND p.active=TRUE
        """, {"id": product_id, "cid": self.company_id})
        return self._product_from_row(rows[0]) if rows else None

    def products_by_category(self, category_id: str) -> list[dict]:
        return [p for p in self.products() if p.get("categoria_id") == str(category_id)]

    def preview_sku(self, categoria_id: str = "", nome: str = "", marca_id: str = "", tipo_material: str = "") -> str:
        cat = self.category_name(categoria_id) if categoria_id else ""
        prefix = slug_prefix(cat or nome or "Produto")
        seq = int(self._scalar("SELECT count(*) + 1 FROM products WHERE company_id=:cid AND sku ILIKE :prefix", {"cid": self.company_id, "prefix": f"{prefix}%"}) or 1)
        return f"{prefix}-{seq:04d}"

    def _normalize_product_payload(self, payload: dict[str, Any], existing_id: str | None = None) -> dict[str, Any]:
        nome = title_pt(payload.get("nome", ""))
        if not nome:
            raise ValueError("Informe o nome do produto.")
        sku = (payload.get("sku") or "").strip().upper().replace(" ", "-")
        if not sku:
            sku = self.preview_sku(payload.get("categoria_id", ""), nome, payload.get("marca_id", ""), payload.get("tipo_material", ""))
        unit_code = payload.get("unidade_medida") or "un"
        quantidade_base = float(payload.get("quantidade_base") or 1)
        estoque = float(payload.get("estoque_atual") or 0)
        minimo = float(payload.get("estoque_minimo") or 0)
        if not is_fractional(unit_code, self.units()):
            if not float(estoque).is_integer() or not float(minimo).is_integer():
                raise ValueError("Unidades singulares aceitam apenas valores inteiros.")
            quantidade_base = 1
        if estoque < 0 or minimo < 0 or quantidade_base <= 0:
            raise ValueError("Quantidades não podem ser negativas e a quantidade base deve ser maior que zero.")
        if existing_id:
            duplicate = self._scalar(
                "SELECT id FROM products WHERE company_id=:cid AND upper(sku)=upper(:sku) AND id::text <> :eid LIMIT 1",
                {"cid": self.company_id, "sku": sku, "eid": str(existing_id)},
            )
        else:
            duplicate = self._scalar(
                "SELECT id FROM products WHERE company_id=:cid AND upper(sku)=upper(:sku) LIMIT 1",
                {"cid": self.company_id, "sku": sku},
            )
        if duplicate:
            raise ValueError("Já existe um produto com esse SKU.")
        return {
            "nome": nome, "sku": sku, "categoria_id": payload.get("categoria_id") or None,
            "marca_id": payload.get("marca_id") or None, "multiestoque_id": payload.get("multiestoque_id") or None,
            "unidade_medida": unit_code, "tipo_material": (payload.get("tipo_material") or "").strip(),
            "quantidade_base": quantidade_base, "estoque_atual": estoque, "estoque_minimo": minimo,
            "preco_custo": float(payload.get("preco_custo") or 0), "preco_venda": float(payload.get("preco_venda") or 0),
            "descricao": (payload.get("descricao") or "").strip(), "controla_lote": bool(payload.get("controla_lote")),
            "controla_validade": bool(payload.get("controla_validade")), "data_validade": payload.get("data_validade") or None,
            "controla_serial": bool(payload.get("controla_serial")), "fornecedor_id": payload.get("fornecedor_id") or None,
        }

    def add_product(self, payload: dict[str, Any]) -> dict:
        p = self._normalize_product_payload(payload)
        with db_session() as session:
            pid = session.execute(text("""
                INSERT INTO products (company_id, sku, name, category_id, brand_id, stock_location_id, material_type,
                    unit_code, quantity_base, current_stock, minimum_stock, cost_price, sale_price, description,
                    controls_batch, controls_expiration, expiration_date, controls_serial, active)
                VALUES (:cid,:sku,:nome,:categoria_id,:marca_id,:multiestoque_id,:tipo_material,:unidade_medida,
                    :quantidade_base,:estoque_atual,:estoque_minimo,:preco_custo,:preco_venda,:descricao,
                    :controla_lote,:controla_validade,:data_validade,:controla_serial,TRUE)
                RETURNING id
            """), {"cid": self.company_id, **p}).scalar_one()
            if p["fornecedor_id"]:
                session.execute(text("""
                    INSERT INTO product_supplier_history (company_id, product_id, supplier_id, paid_price, negotiation_status, notes)
                    VALUES (:cid, :pid, :sid, :price, 'Cadastro inicial', 'Fornecedor inicial informado no cadastro')
                """), {"cid": self.company_id, "pid": pid, "sid": p["fornecedor_id"], "price": p["preco_custo"]})
            if p["estoque_atual"] > 0:
                session.execute(text("""
                    INSERT INTO stock_movements (company_id, product_id, movement_type, quantity, unit_code, converted_quantity, previous_stock, resulting_stock, source_destination, notes)
                    VALUES (:cid, :pid, 'cadastro_inicial', :qty, :unit, :qty, 0, :qty, 'Cadastro', 'Saldo inicial do produto')
                """), {"cid": self.company_id, "pid": pid, "qty": p["estoque_atual"], "unit": p["unidade_medida"]})
            session.execute(text("""
                INSERT INTO audit_logs (company_id, entity_type, entity_id, action, new_data)
                VALUES (:cid, 'products', :pid, 'criar', CAST(:data AS jsonb))
            """), {"cid": self.company_id, "pid": pid, "data": json.dumps(p, ensure_ascii=False)})
        self._invalidate_domain_cache("products", "recent_movements", "purchase_requests")
        return self.get_product(str(pid)) or {"id": str(pid), **p}

    def update_product(self, product_id: str, payload: dict[str, Any]) -> dict:
        p = self._normalize_product_payload(payload, existing_id=product_id)
        old = self.get_product(product_id) or {}
        with db_session() as session:
            session.execute(text("""
                UPDATE products SET sku=:sku, name=:nome, category_id=:categoria_id, brand_id=:marca_id,
                    stock_location_id=:multiestoque_id, material_type=:tipo_material, unit_code=:unidade_medida,
                    quantity_base=:quantidade_base, current_stock=:estoque_atual, minimum_stock=:estoque_minimo,
                    cost_price=:preco_custo, sale_price=:preco_venda, description=:descricao,
                    controls_batch=:controla_lote, controls_expiration=:controla_validade, expiration_date=:data_validade,
                    controls_serial=:controla_serial, updated_at=now()
                WHERE id=:id AND company_id=:cid
            """), {"id": product_id, "cid": self.company_id, **p})
            session.execute(text("""
                INSERT INTO audit_logs (company_id, entity_type, entity_id, action, old_data, new_data)
                VALUES (:cid, 'products', :pid, 'editar', CAST(:old AS jsonb), CAST(:new AS jsonb))
            """), {"cid": self.company_id, "pid": product_id, "old": json.dumps(old, ensure_ascii=False), "new": json.dumps(p, ensure_ascii=False)})
        self._invalidate_domain_cache("products", "recent_movements", "purchase_requests")
        return self.get_product(product_id) or {}

    def delete_product(self, product_id: str) -> None:
        with db_session() as session:
            session.execute(text("UPDATE products SET active=FALSE, updated_at=now() WHERE id=:id AND company_id=:cid"), {"id": product_id, "cid": self.company_id})
        self._invalidate_domain_cache("products", "recent_movements", "purchase_requests")

    # ------------------------------------------------------------------
    # Movimentações
    # ------------------------------------------------------------------
    def validate_quantity_for_unit(self, unit_code: str, quantidade: float, label: str = "quantidade") -> float:
        if quantidade <= 0:
            raise ValueError(f"{label.title()} deve ser maior que zero.")
        if not is_fractional(unit_code, self.units()) and not float(quantidade).is_integer():
            raise ValueError(f"{label.title()} deve ser inteiro para a unidade {unit_code}.")
        return quantidade

    def add_movement(self, product_id: str, tipo: str, quantidade: float, unidade_usada: str | None = None, responsavel_id: str = "", origem_destino: str = "", observacao: str = "", purchase_request_id: str = "") -> dict:
        responsavel_id = uuid_or_none(responsavel_id)
        if not is_uuid(product_id):
            raise ValueError("Produto inválido ou desatualizado. Atualize a tela e tente novamente.")
        prod = self.get_product(product_id)
        if not prod:
            raise ValueError("Produto não encontrado.")
        unit_code = unidade_usada or prod.get("unidade_medida") or "un"
        quantidade = self.validate_quantity_for_unit(unit_code, float(quantidade), "quantidade")
        tipo_norm = tipo.lower().strip()
        if tipo_norm in {"entrada", "recebimento_compra", "cadastro_inicial"}:
            delta = quantidade
        elif tipo_norm == "saida":
            delta = -quantidade
        elif tipo_norm == "ajuste":
            delta = None
        else:
            raise ValueError("Tipo de movimentação inválido.")
        with db_session() as session:
            row = session.execute(text("SELECT current_stock FROM products WHERE id=:id AND company_id=:cid FOR UPDATE"), {"id": product_id, "cid": self.company_id}).mappings().first()
            if not row:
                raise ValueError("Produto não encontrado.")
            prev = float(row["current_stock"] or 0)
            result = quantidade if delta is None else prev + delta
            if result < 0:
                raise ValueError("Saldo insuficiente para saída de estoque.")
            session.execute(text("UPDATE products SET current_stock=:stock, updated_at=now() WHERE id=:id"), {"stock": result, "id": product_id})
            mid = session.execute(text("""
                INSERT INTO stock_movements (company_id, product_id, movement_type, quantity, unit_code, converted_quantity, previous_stock, resulting_stock, responsible_user_id, source_destination, notes)
                VALUES (:cid,:pid,:type,:qty,:unit,:qty,:prev,:result,:resp,:src,:notes) RETURNING id
            """), {"cid": self.company_id, "pid": product_id, "type": tipo_norm, "qty": quantidade, "unit": unit_code, "prev": prev, "result": result, "resp": responsavel_id, "src": origem_destino, "notes": observacao}).scalar_one()
        self._invalidate_domain_cache("products", "recent_movements", "purchase_requests")
        return next((m for m in self.recent_movements(50) if m["id"] == str(mid)), {})

    def _recent_movements_remote(self, limit: int = 500) -> list[dict]:
        rows = self._rows("""
            SELECT m.*, p.name AS product_name, p.sku, u.name AS responsible_name
            FROM stock_movements m
            LEFT JOIN products p ON p.id=m.product_id
            LEFT JOIN users_app u ON u.id=m.responsible_user_id
            WHERE m.company_id=:cid
            ORDER BY m.created_at DESC LIMIT :limit
        """, {"cid": self.company_id, "limit": limit})
        label = {"entrada": "Entrada", "saida": "Saída", "ajuste": "Ajuste", "cadastro_inicial": "Entrada", "recebimento_compra": "Entrada"}
        return [{
            "id": str(r["id"]), "produto_id": str(r.get("product_id") or ""), "produto_nome": r.get("product_name") or "",
            "sku": r.get("sku") or "", "tipo": label.get(r.get("movement_type"), r.get("movement_type") or ""),
            "quantidade": float(r.get("quantity") or 0), "unidade_usada": r.get("unit_code") or "",
            "quantidade_convertida": float(r.get("converted_quantity") or 0), "saldo_anterior": float(r.get("previous_stock") or 0),
            "saldo_restante": float(r.get("resulting_stock") or 0), "responsavel_nome": r.get("responsible_name") or "",
            "criado_em": _dt_to_iso(r.get("created_at")), "observacao": r.get("notes") or ""
        } for r in rows]

    def recent_movements(self, limit: int = 20) -> list[dict]:
        cache_key = f"recent_movements:{limit}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached
        local = self.local_cache.get_collection("recent_movements")
        if local is not None:
            return self._cache_set(cache_key, local[:limit])
        data = self._recent_movements_remote(max(limit, 500))
        self.local_cache.set_collection("recent_movements", data)
        return self._cache_set(cache_key, data[:limit])

    # ------------------------------------------------------------------
    # Compras e fornecedores
    # ------------------------------------------------------------------
    def _purchase_requests_remote(self) -> list[dict]:
        rows = self._rows("""
            SELECT pr.*, p.name AS product_name, p.sku, s.name AS supplier_name
            FROM purchase_requests pr
            LEFT JOIN products p ON p.id=pr.product_id
            LEFT JOIN suppliers s ON s.id=pr.supplier_id
            WHERE pr.company_id=:cid
            ORDER BY pr.updated_at DESC, pr.created_at DESC
        """, {"cid": self.company_id})
        return [{
            "id": str(r["id"]), "produto_id": str(r.get("product_id") or ""), "produto_nome": r.get("product_name") or "",
            "sku": r.get("sku") or "", "status": r.get("status") or "", "quantidade_solicitada": float(r.get("requested_quantity") or 0),
            "quantidade_recebida": float(r.get("received_quantity") or 0), "unidade": r.get("unit_code") or "", "unidade_medida": r.get("unit_code") or "", "prioridade": r.get("priority") or "",
            "fornecedor_id": str(r.get("supplier_id") or ""), "fornecedor_nome": r.get("supplier_name") or "", "fornecedor": r.get("supplier_name") or "", "numero_pedido": r.get("order_number") or "",
            "valor": float(r.get("order_value") or 0), "previsao_entrega": _dt_to_iso(r.get("expected_delivery_date")),
            "justificativa": r.get("justification") or "", "observacao": r.get("notes") or "", "atualizado_em": _dt_to_iso(r.get("updated_at")), "criado_em": _dt_to_iso(r.get("created_at"))
        } for r in rows]

    def _purchase_request_by_id_remote(self, request_id: str) -> dict | None:
        """Busca uma solicitação diretamente no Neon, ignorando cache local.

        O recebimento de compra é uma operação crítica e não pode depender de
        snapshots antigos do cache SQLite/RAM, pois um cache antigo pode conter
        IDs temporários herdados de versões anteriores.
        """
        rows = self._rows("""
            SELECT pr.*, p.name AS product_name, p.sku, s.name AS supplier_name
            FROM purchase_requests pr
            LEFT JOIN products p ON p.id=pr.product_id
            LEFT JOIN suppliers s ON s.id=pr.supplier_id
            WHERE pr.company_id=:cid AND pr.id=:id
            LIMIT 1
        """, {"cid": self.company_id, "id": request_id})
        if not rows:
            return None
        r = rows[0]
        return {
            "id": str(r["id"]), "produto_id": str(r.get("product_id") or ""), "produto_nome": r.get("product_name") or "",
            "sku": r.get("sku") or "", "status": r.get("status") or "", "quantidade_solicitada": float(r.get("requested_quantity") or 0),
            "quantidade_recebida": float(r.get("received_quantity") or 0), "unidade": r.get("unit_code") or "", "unidade_medida": r.get("unit_code") or "", "prioridade": r.get("priority") or "",
            "fornecedor_id": str(r.get("supplier_id") or ""), "fornecedor_nome": r.get("supplier_name") or "", "fornecedor": r.get("supplier_name") or "", "numero_pedido": r.get("order_number") or "",
            "valor": float(r.get("order_value") or 0), "previsao_entrega": _dt_to_iso(r.get("expected_delivery_date")),
            "justificativa": r.get("justification") or "", "observacao": r.get("notes") or "", "atualizado_em": _dt_to_iso(r.get("updated_at")), "criado_em": _dt_to_iso(r.get("created_at"))
        }

    def purchase_requests(self, statuses: list[str] | set[str] | None = None, product_id: str | None = None) -> list[dict]:
        cache_key = f"purchase_requests:{','.join(sorted(statuses)) if statuses else 'all'}:{product_id or ''}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached
        data = self.local_cache.get_collection("purchase_requests")
        if data is None:
            data = self._purchase_requests_remote()
            self.local_cache.set_collection("purchase_requests", data)
        if statuses:
            data = [r for r in data if r.get("status") in set(statuses)]
        if product_id:
            data = [r for r in data if r.get("produto_id") == str(product_id)]
        return self._cache_set(cache_key, data)

    def latest_purchase_for_product(self, product_id: str) -> dict | None:
        reqs = self.purchase_requests(product_id=product_id)
        return reqs[0] if reqs else None

    def purchase_status_for_product(self, product_id: str) -> str:
        # Usa o status pré-carregado em products() antes de consultar solicitações.
        # Isso evita uma chamada remota por linha da tabela.
        prod = next((p for p in self.products() if p.get("id") == str(product_id)), None)
        if prod and prod.get("compra_status"):
            return prod.get("compra_status", "")
        req = self.latest_purchase_for_product(product_id)
        return req["status"] if req and req.get("status") not in FINAL_PURCHASE_STATUSES else ""

    def create_purchase_request(self, product_id: str, quantidade: float, solicitante_id: str, prioridade: str, justificativa: str, observacao: str = "") -> dict:
        prod = self.get_product(product_id)
        if not prod:
            raise ValueError("Produto não encontrado.")
        solicitante_id = uuid_or_none(solicitante_id)
        with db_session() as session:
            rid = session.execute(text("""
                INSERT INTO purchase_requests (company_id, product_id, requested_quantity, unit_code, priority, status, justification, notes, requested_by)
                VALUES (:cid,:pid,:qty,:unit,:priority,'Solicitação Criada',:just,:notes,:user) RETURNING id
            """), {"cid": self.company_id, "pid": product_id, "qty": quantidade, "unit": prod.get("unidade_medida"), "priority": prioridade, "just": justificativa, "notes": observacao, "user": solicitante_id}).scalar_one()
        self._invalidate_domain_cache("purchase_requests", "products")
        return self._purchase_request_by_id_remote(str(rid)) or {}

    def update_purchase_status(self, request_id: str, status: str, responsible_id: str = "", supplier_id: str = "", order_number: str = "", value: float = 0.0, expected_date: str = "", observacao: str = "") -> dict:
        responsible_id = uuid_or_none(responsible_id)
        supplier_id = uuid_or_none(supplier_id)
        with db_session() as session:
            session.execute(text("""
                UPDATE purchase_requests SET status=:status, supplier_id=COALESCE(:sid, supplier_id), order_number=COALESCE(:ord, order_number),
                    order_value=COALESCE(:val, order_value), expected_delivery_date=COALESCE(:dt, expected_delivery_date), notes=COALESCE(:obs, notes), purchased_by=COALESCE(:resp, purchased_by),
                    updated_at=now(), finalized_at=CASE WHEN :status IN ('Finalizado','Cancelado','Rejeitado','Compra Recebida Integralmente','Item devolvido','Troca recebida') THEN now() ELSE finalized_at END
                WHERE id=:id AND company_id=:cid
            """), {"status": status, "sid": supplier_id, "ord": order_number or None, "val": value or None, "dt": expected_date or None, "obs": observacao or None, "resp": responsible_id, "id": request_id, "cid": self.company_id})
            session.execute(text("""
                INSERT INTO audit_logs (company_id, entity_type, entity_id, action, new_data)
                VALUES (:cid, 'purchase_request', :id, 'status_update', CAST(:data AS jsonb))
            """), {"cid": self.company_id, "id": request_id if is_uuid(request_id) else None, "data": json.dumps({"status": status, "observacao": observacao}, ensure_ascii=False)})
        self._invalidate_domain_cache("purchase_requests", "products")
        return self._purchase_request_by_id_remote(str(request_id)) or {}

    def receive_purchase(self, request_id: str, quantidade_recebida: float, responsible_id: str, observacao: str = "", avarias: str = "", overage_action: str = "stock", return_reason: str = "") -> dict:
        """Confirma recebimento de compra de forma transacional e segura.

        - Bloqueia a solicitação e o produto com ``FOR UPDATE`` para evitar
          cliques duplicados ou confirmações simultâneas em computadores
          diferentes.
        - Permite tratar excedente: adicionar ao estoque ou abrir devolução.
        - Converte IDs temporários/legados para ``None`` antes de gravar UUID.
        """
        if not is_uuid(request_id):
            raise ValueError("Solicitação de compra inválida ou desatualizada. Atualize a tela e tente novamente.")
        quantidade_recebida = float(quantidade_recebida or 0)
        if quantidade_recebida <= 0:
            raise ValueError("Informe uma quantidade recebida maior que zero.")
        responsible_id = uuid_or_none(responsible_id)
        overage_action = (overage_action or "stock").lower().strip()
        if overage_action not in {"stock", "return"}:
            raise ValueError("Ação para quantidade excedente inválida.")

        try:
            with db_session() as session:
                req_row = session.execute(text("""
                    SELECT pr.*, p.current_stock, p.name AS product_name
                    FROM purchase_requests pr
                    JOIN products p ON p.id = pr.product_id
                    WHERE pr.company_id=:cid AND pr.id=:rid
                    FOR UPDATE OF pr, p
                """), {"cid": self.company_id, "rid": request_id}).mappings().first()
                if not req_row:
                    raise ValueError("Solicitação de compra não encontrada. Atualize a tela e tente novamente.")

                product_id = str(req_row["product_id"]) if req_row.get("product_id") else ""
                if not is_uuid(product_id):
                    raise ValueError("Esta solicitação está com vínculo de produto inválido ou desatualizado. Atualize a lista de compras antes de confirmar o recebimento.")

                requested = float(req_row.get("requested_quantity") or 0)
                already_received = float(req_row.get("received_quantity") or 0)
                remaining = max(0.0, requested - already_received)
                excess = max(0.0, quantidade_recebida - remaining)

                # Se a compra já foi completamente recebida, só permite nova
                # entrada quando o usuário confirmou explicitamente adicionar
                # excedente ao estoque. Isso reduz duplicidades por cliques.
                if remaining <= 0 and overage_action != "stock":
                    raise ValueError("Essa compra já foi recebida integralmente. Atualize a tela antes de confirmar novo recebimento.")

                stock_quantity = quantidade_recebida
                return_quantity = 0.0
                if excess > 0 and overage_action == "return":
                    stock_quantity = remaining
                    return_quantity = excess

                previous_stock = float(req_row.get("current_stock") or 0)
                unit_code = req_row.get("unit_code") or "un"
                resulting_stock = previous_stock

                if stock_quantity > 0:
                    stock_quantity = self.validate_quantity_for_unit(unit_code, stock_quantity, "quantidade recebida")
                    resulting_stock = previous_stock + stock_quantity
                    session.execute(text("""
                        UPDATE products
                        SET current_stock=:stock, updated_at=now()
                        WHERE id=:pid AND company_id=:cid
                    """), {"stock": resulting_stock, "pid": product_id, "cid": self.company_id})
                    session.execute(text("""
                        INSERT INTO stock_movements
                        (company_id, product_id, movement_type, quantity, unit_code, converted_quantity, previous_stock, resulting_stock, responsible_user_id, source_destination, notes)
                        VALUES (:cid,:pid,'recebimento_compra',:qty,:unit,:qty,:prev,:result,:resp,'Compra',:notes)
                    """), {"cid": self.company_id, "pid": product_id, "qty": stock_quantity, "unit": unit_code, "prev": previous_stock, "result": resulting_stock, "resp": responsible_id, "notes": observacao})

                total_received = already_received + stock_quantity
                status = "Compra Recebida Integralmente" if total_received >= requested else "Compra Parcial Recebida"

                if return_quantity > 0:
                    session.execute(text("""
                        INSERT INTO supplier_return_requests
                        (company_id, purchase_request_id, product_id, supplier_id, quantity, unit_code, reason, status, notes, requested_by)
                        VALUES (:cid,:rid,:pid,:sid,:qty,:unit,:reason,'Pendente de devolução',:notes,:resp)
                    """), {"cid": self.company_id, "rid": request_id, "pid": product_id, "sid": req_row.get("supplier_id"), "qty": return_quantity, "unit": unit_code, "reason": return_reason or avarias or "Quantidade recebida acima do previsto", "notes": observacao, "resp": responsible_id})
                    status = "Pendente de devolução"

                session.execute(text("""
                    UPDATE purchase_requests
                    SET received_quantity=:total, status=:status, updated_at=now(),
                        finalized_at=CASE WHEN :final THEN now() ELSE finalized_at END
                    WHERE id=:rid AND company_id=:cid
                """), {"total": total_received, "status": status, "final": status == "Compra Recebida Integralmente", "rid": request_id, "cid": self.company_id})

                session.execute(text("""
                    INSERT INTO audit_logs (company_id, user_id, entity_type, entity_id, action, new_data)
                    VALUES (:cid,:uid,'purchase_request',:rid,'receive_purchase',CAST(:data AS jsonb))
                """), {"cid": self.company_id, "uid": responsible_id, "rid": request_id, "data": json.dumps({"quantidade_recebida": quantidade_recebida, "adicionada_ao_estoque": stock_quantity, "excedente_devolucao": return_quantity, "status": status, "observacao": observacao}, ensure_ascii=False)})
        except Exception as exc:
            raise ValueError(user_friendly_db_error(exc)) from exc

        self._invalidate_domain_cache("purchase_requests", "products", "recent_movements")
        refreshed = self._purchase_request_by_id_remote(str(request_id))
        self.local_cache.invalidate("purchase_requests", "products", "recent_movements")
        return refreshed or {}

    def force_refresh(self) -> None:
        """Limpa cache e sincroniza novamente dados remotos principais."""
        self._clear_cache()
        self.local_cache.clear_all()
        self.sync_remote_cache(force=True)

    def product_purchase_history(self, product_id: str) -> list[dict]:
        return self.purchase_requests(product_id=product_id)

    def supplier_history_for_product(self, product_id: str) -> list[dict]:
        rows = self._rows("""
            SELECT h.*, s.name AS supplier_name FROM product_supplier_history h
            LEFT JOIN suppliers s ON s.id=h.supplier_id
            WHERE h.company_id=:cid AND h.product_id=:pid ORDER BY h.created_at DESC
        """, {"cid": self.company_id, "pid": product_id})
        return [{"id": str(r["id"]), "produto_id": str(r.get("product_id") or ""), "fornecedor_id": str(r.get("supplier_id") or ""), "fornecedor_nome": r.get("supplier_name") or "", "preco_cotado": float(r.get("quoted_price") or 0), "preco_pago": float(r.get("paid_price") or 0), "data_cotacao": _dt_to_iso(r.get("quote_date")), "data_compra": _dt_to_iso(r.get("purchase_date")), "prazo_entrega_dias": r.get("delivery_days") or 0, "status_negociacao": r.get("negotiation_status") or "", "observacao": r.get("notes") or ""} for r in rows]

    def add_supplier_history(self, product_id: str, fornecedor_id: str, preco_cotado: float = 0.0, preco_pago: float = 0.0, data_cotacao: str = "", data_compra: str = "", prazo_entrega_dias: int = 0, status_negociacao: str = "Cotado", responsavel_id: str = "", observacao: str = "") -> dict:
        with db_session() as session:
            hid = session.execute(text("""
                INSERT INTO product_supplier_history (company_id, product_id, supplier_id, quoted_price, paid_price, quote_date, purchase_date, delivery_days, negotiation_status, notes)
                VALUES (:cid,:pid,:sid,:quoted,:paid,:qdate,:pdate,:days,:status,:notes) RETURNING id
            """), {"cid": self.company_id, "pid": product_id, "sid": fornecedor_id or None, "quoted": preco_cotado or None, "paid": preco_pago or None, "qdate": data_cotacao or None, "pdate": data_compra or None, "days": prazo_entrega_dias or None, "status": status_negociacao, "notes": observacao}).scalar_one()
        self._invalidate_domain_cache("products")
        return next((r for r in self.supplier_history_for_product(product_id) if r["id"] == str(hid)), {})

    def supplier_comparison_for_product(self, product_id: str) -> dict:
        rows = self.supplier_history_for_product(product_id)
        best_price = min((r for r in rows if r.get("preco_pago") or r.get("preco_cotado")), key=lambda r: r.get("preco_pago") or r.get("preco_cotado"), default=None)
        best_deadline = min((r for r in rows if r.get("prazo_entrega_dias")), key=lambda r: r.get("prazo_entrega_dias"), default=None)
        return {"rows": rows, "menor_preco": best_price, "melhor_prazo": best_deadline, "mais_usado": None}

    # ------------------------------------------------------------------
    # Painéis, atividades e configurações
    # ------------------------------------------------------------------
    def low_stock_products(self) -> list[dict]:
        return [p for p in self.products() if float(p.get("estoque_atual", 0)) <= float(p.get("estoque_minimo", 0)) and float(p.get("estoque_atual", 0)) > 0]

    def out_stock_products(self) -> list[dict]:
        return [p for p in self.products() if float(p.get("estoque_atual", 0)) <= 0]

    def analysis_products(self) -> list[dict]:
        return [p for p in self.products() if p.get("compra_status")]

    def dashboard(self) -> dict:
        """Retorna todos os indicadores esperados pela tela de dashboard.

        A UI original foi criada sobre a camada JSON e espera algumas chaves
        específicas em português, como ``itens_baixo`` e
        ``aguardando_recebimento``. Ao migrar para PostgreSQL/Neon, este método
        precisa manter o mesmo contrato de dados para evitar erros de interface
        como ``KeyError: 'itens_baixo'``.
        """
        products = self.products()
        low_all = [
            p for p in products
            if float(p.get("estoque_atual", 0) or 0) <= float(p.get("estoque_minimo", 0) or 0)
        ]
        out = [p for p in products if float(p.get("estoque_atual", 0) or 0) <= 0]
        analysis = self.analysis_products()
        active_purchases = self.purchase_requests(statuses=ACTIVE_PURCHASE_STATUSES)
        awaiting_receipt = self.purchase_requests(statuses={"Pedido Realizado", "Compra Parcial Recebida"})

        return {
            "total_produtos": len(products),
            "itens_analise": len(analysis),
            "baixo_estoque": len(low_all),
            "sem_estoque": len(out),
            "movimentacoes": len(self.recent_movements(9999)),
            "compras_pendentes": len(active_purchases),
            "aguardando_recebimento": len(awaiting_receipt),
            "itens_baixo": low_all[:8],
        }

    def recent_activities(self, limit: int = 20) -> list[dict]:
        acts = []
        for m in self.recent_movements(limit):
            acts.append({"id": m["id"], "tipo": "movimentacao", "descricao": f"{m['tipo']} de estoque", "produto_id": m.get("produto_id", ""), "produto_nome": m.get("produto_nome", ""), "quantidade": m.get("quantidade", 0), "unidade": m.get("unidade_usada", ""), "status": m.get("tipo", ""), "responsavel_nome": m.get("responsavel_nome", ""), "criado_em": m.get("criado_em", "")})
        return acts[:limit]

    def record_activity(self, *args, **kwargs) -> dict:
        # Mantido por compatibilidade. No PostgreSQL, atividades são derivadas de movimentos/auditoria.
        return {"id": str(uuid.uuid4()), "criado_em": now_iso()}

    def audit(self, entidade: str, entidade_id: str, acao: str, antes: dict, depois: dict) -> None:
        with db_session() as session:
            session.execute(text("INSERT INTO audit_logs (company_id, entity_type, entity_id, action, old_data, new_data) VALUES (:cid,:ent,:eid,:act,CAST(:old AS jsonb),CAST(:new AS jsonb))"), {"cid": self.company_id, "ent": entidade, "eid": entidade_id or None, "act": acao, "old": json.dumps(antes or {}, ensure_ascii=False), "new": json.dumps(depois or {}, ensure_ascii=False)})

    def table_columns(self, table_name: str) -> list[int]:
        cache_key = f"table_columns:{table_name}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached
        raw = self._scalar("SELECT value FROM app_metadata WHERE key=:key", {"key": f"table_columns:{table_name}"})
        try:
            return self._cache_set(cache_key, json.loads(raw) if raw else [])
        except Exception:
            return self._cache_set(cache_key, [])

    def save_table_columns(self, table_name: str, widths: list[int]) -> None:
        with db_session() as session:
            session.execute(text("INSERT INTO app_metadata (key, value) VALUES (:key,:val) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=now()"), {"key": f"table_columns:{table_name}", "val": json.dumps(widths)})
