"""Camada de regras de negócio e persistência do inventário.

O serviço isola a interface gráfica do formato físico do banco JSON. Todas as
operações que alteram dados passam por aqui para manter consistência, auditoria,
rastreabilidade e compatibilidade futura com SQLite, PostgreSQL ou APIs REST.

Principais responsabilidades:
- Normalizar produtos, SKUs, categorias, marcas, fornecedores e estoques.
- Validar quantidades conforme a unidade de medida.
- Registrar movimentações, atividades recentes e auditorias.
- Controlar o fluxo de compras e recebimento com atualização automática de saldo.
"""

from __future__ import annotations

import re
import uuid
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

from src.domain.units import convert_value, is_fractional, physical_total, round_value
from src.services.json_storage import JsonStorage
from src.core.paths import ensure_user_database

# Banco persistente do cliente. Em produção fica em AppData, não na pasta do exe.
DB_PATH = ensure_user_database()
LOWER_WORDS = {"de", "da", "do", "das", "dos", "e", "em", "com", "para", "por"}
FINAL_PURCHASE_STATUSES = {"Finalizado", "Cancelado", "Rejeitado", "Compra Recebida Integralmente"}
ACTIVE_PURCHASE_STATUSES = {
    "Solicitação Criada", "Em Análise", "Aguardando Aprovação", "Aguardando Pedido",
    "Pedido Realizado", "Compra Parcial Recebida"
}


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


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


class StockService:
    def __init__(self, path: Path = DB_PATH):
        self.storage = JsonStorage(path)
        self.data = self.storage.load()
        if not self.data:
            self.data = {
                "version": 14, "schema_version": 14, "units": [], "categories": [], "suppliers": [], "brands": [],
                "warehouses": [], "responsibles": [], "products": [], "movements": [],
                "purchase_requests": [], "purchase_events": [], "supplier_item_history": [], "activities": [], "audits": [],
                "settings": {"arredondamento": "half_up", "table_columns": {}}
            }
            self.save()
        self.migrate_v5()

    def save(self) -> None:
        self.data["updated_at"] = now_iso()
        self.storage.save(self.data)

        # Migração defensiva: garante chaves obrigatórias sem apagar dados do usuário.
    # Este método permite abrir bancos antigos e normalizá-los para o modelo atual.
    def migrate_v5(self) -> None:
        changed = False
        for key in ["brands", "responsibles", "warehouses", "suppliers", "categories", "movements", "activities", "audits", "purchase_requests", "purchase_events", "supplier_item_history"]:
            if key not in self.data:
                self.data[key] = []
                changed = True
        self.data.setdefault("settings", {}).setdefault("table_columns", {})
        self.data.setdefault("settings", {}).setdefault("estoque_principal", "estoque-principal")
        self.data.setdefault("settings", {}).setdefault("usuario_padrao", "Operador")

        if not self.data["responsibles"]:
            self.data["responsibles"].append({"id": "resp-padrao", "nome": "Responsável Padrão", "ativo": True, "origem": "sistema", "criado_em": now_iso(), "atualizado_em": now_iso()})
            changed = True
        if not self.data["warehouses"]:
            self.data["warehouses"].append({"id": "estoque-principal", "nome": "Estoque Principal", "descricao": "Estoque físico padrão", "ativo": True, "origem": "sistema", "criado_em": now_iso(), "atualizado_em": now_iso()})
            changed = True

        for prod in self.data.get("products", []):
            marca_nome = title_pt(prod.get("marca", ""))
            if marca_nome and not prod.get("marca_id"):
                brand = self.create_reference("brands", marca_nome, save=False, audit=False)
                prod["marca_id"] = brand["id"]
                prod["marca"] = brand["nome"]
                changed = True
            prod.setdefault("compra_status", "")
            prod.setdefault("ultima_solicitacao_compra_id", "")

        for prod in self.data.get("products", []):
            prod.setdefault("data_validade", prod.get("validade", ""))
            if prod.get("controla_validade") and not prod.get("data_validade") and prod.get("validade"):
                prod["data_validade"] = prod.get("validade")
                changed = True
        if self.data.get("version", 0) < 14:
            self.data["version"] = 14
            self.data["schema_version"] = 14
            changed = True
        # Constrói histórico item-fornecedor a partir dos metadados importados,
        # mantendo rastreabilidade de preços por fornecedor sem sobrescrever dados antigos.
        if not self.data.get("supplier_item_history"):
            self._bootstrap_supplier_history_from_products()
            changed = True
        if changed:
            self.save()

    def _active(self, table: str) -> list[dict]:
        return [r for r in self.data.get(table, []) if r.get("ativo", True)]

    def brands(self) -> list[dict]: return self._active("brands")
    def responsibles(self) -> list[dict]: return self._active("responsibles")
    def warehouses(self) -> list[dict]: return self._active("warehouses")
    def suppliers(self) -> list[dict]: return self._active("suppliers")
    def categories(self) -> list[dict]: return self._active("categories")
    def products(self) -> list[dict]: return [p for p in self.data.get("products", []) if p.get("ativo", True)]
    def units(self) -> list[dict]: return self.data.get("units", [])

    def brand_name(self, brand_id: str) -> str: return next((b["nome"] for b in self.brands() if b["id"] == brand_id), "")
    def warehouse_name(self, warehouse_id: str) -> str: return next((w["nome"] for w in self.warehouses() if w["id"] == warehouse_id), "")
    def responsible_name(self, responsible_id: str) -> str: return next((r["nome"] for r in self.responsibles() if r["id"] == responsible_id), "")
    def category_name(self, category_id: str) -> str: return next((c["nome"] for c in self.categories() if c["id"] == category_id), "")
    def supplier_name(self, supplier_id: str) -> str: return next((s["nome"] for s in self.suppliers() if s["id"] == supplier_id), "")
    def get_product(self, product_id: str) -> dict | None: return next((p for p in self.products() if p["id"] == product_id), None)

    def unit(self, code: str) -> dict:
        return next((u for u in self.units() if u.get("codigo") == code), {})

    def unit_label(self, code: str) -> str:
        u = self.unit(code)
        return f"{u.get('codigo', code)} - {u.get('descricao', '')}".strip(" -")

    def create_reference(self, table: str, name: str, save: bool = True, audit: bool = True) -> dict:
        allowed = {"categories": "cat", "brands": "mar", "suppliers": "for", "warehouses": "est", "responsibles": "resp"}
        if table not in allowed:
            raise ValueError("Cadastro de referência inválido.")
        name = title_pt(name)
        if not name:
            raise ValueError("Informe um nome válido.")
        records = self.data.setdefault(table, [])
        existing = next((r for r in records if r.get("ativo", True) and r.get("nome", "").lower() == name.lower()), None)
        if existing:
            return existing
        rec = {"id": f"{allowed[table]}-{uuid.uuid4().hex[:8]}", "nome": name, "descricao": "", "ativo": True, "origem": "usuario", "criado_em": now_iso(), "atualizado_em": now_iso()}
        records.append(rec)
        if audit:
            self.audit(table, rec["id"], "criar", {}, rec)
        if save:
            self.save()
        return rec

    def update_reference(self, table: str, record_id: str, name: str, descricao: str | None = None) -> dict:
        name = title_pt(name)
        if not name:
            raise ValueError("Informe um nome válido.")
        duplicate = next((r for r in self._active(table) if r["id"] != record_id and r.get("nome", "").lower() == name.lower()), None)
        if duplicate:
            raise ValueError("Já existe um cadastro com esse nome.")
        rec = next((r for r in self.data.setdefault(table, []) if r["id"] == record_id), None)
        if not rec:
            raise ValueError("Registro não encontrado.")
        old = deepcopy(rec)
        rec["nome"] = name
        if descricao is not None:
            rec["descricao"] = descricao.strip()
        rec["atualizado_em"] = now_iso()
        self.audit(table, record_id, "editar", old, rec)
        self.save()
        return rec

    def delete_reference(self, table: str, record_id: str) -> None:
        usage_fields = {
            "categories": ("categoria_id", "products"), "brands": ("marca_id", "products"),
            "suppliers": ("fornecedor_id", "products"), "warehouses": ("multiestoque_id", "products"),
            "responsibles": ("responsavel_id", "movements"),
        }
        if table in usage_fields:
            field, collection = usage_fields[table]
            if any(item.get(field) == record_id and item.get("ativo", True) for item in self.data.get(collection, [])):
                raise ValueError("Este cadastro está em uso e não pode ser excluído. Edite-o ou remova os vínculos antes.")
        rec = next((r for r in self.data.setdefault(table, []) if r["id"] == record_id), None)
        if not rec:
            raise ValueError("Registro não encontrado.")
        old = deepcopy(rec)
        rec["ativo"] = False
        rec["atualizado_em"] = now_iso()
        self.audit(table, record_id, "excluir", old, rec)
        self.save()


    def _supplier_id_by_name(self, name: str) -> str:
        """Localiza ou cria fornecedor pelo nome normalizado.

        A função é usada na migração do histórico de preços importado do JSON
        legado. O cadastro passa a ter referência relacional, mas preserva o
        nome original do fornecedor para auditoria e futuras integrações.
        """
        name = title_pt(name or "Fornecedor Não Informado")
        rec = self.create_reference("suppliers", name, save=False, audit=False)
        return rec["id"]

    def _bootstrap_supplier_history_from_products(self) -> None:
        """Extrai histórico de preço dos produtos para uma tabela normalizada.

        Cada produto importado pode possuir ``metadados.historico_precos`` com
        múltiplas linhas de orçamento/compra por fornecedor. Esta rotina cria
        registros independentes em ``supplier_item_history`` para permitir
        comparação por fornecedor, análise de variação de preço e rastreabilidade.
        """
        history = self.data.setdefault("supplier_item_history", [])
        seen = set()
        for product in self.data.get("products", []):
            product_id = product.get("id")
            for h in product.get("metadados", {}).get("historico_precos", []):
                supplier_name = h.get("fornecedor") or self.supplier_name(product.get("fornecedor_id", "")) or "Fornecedor Não Informado"
                supplier_id = self._supplier_id_by_name(supplier_name)
                key = (product_id, supplier_id, str(h.get("atualizacao", "")), float(h.get("preco_custo") or 0), str(h.get("codigo_fornecedor", "")))
                if key in seen:
                    continue
                seen.add(key)
                history.append({
                    "id": f"hist-{uuid.uuid4().hex[:10]}",
                    "produto_id": product_id,
                    "fornecedor_id": supplier_id,
                    "fornecedor_nome": supplier_name,
                    "codigo_fornecedor": h.get("codigo_fornecedor", ""),
                    "preco_cotado": float(h.get("valor_base") or h.get("preco_custo") or 0),
                    "preco_pago": float(h.get("preco_custo") or 0),
                    "melhor_preco_registrado": float(h.get("melhor_preco_registrado") or 0),
                    "variacao_percentual": float(h.get("variacao_vs_melhor_preco_percentual") or 0),
                    "data_cotacao": h.get("atualizacao", ""),
                    "data_compra": h.get("atualizacao", ""),
                    "prazo_entrega_dias": 0,
                    "status_negociacao": "Histórico importado",
                    "responsavel_id": "",
                    "observacao": "Registro importado do histórico comercial do produto.",
                    "origem": "metadados.historico_precos",
                    "ativo": True,
                    "criado_em": now_iso(),
                    "atualizado_em": now_iso(),
                })

    def supplier_history_for_product(self, product_id: str) -> list[dict]:
        """Retorna cotações/compras de um item com nomes de fornecedor e responsável."""
        rows = []
        for h in self.data.get("supplier_item_history", []):
            if h.get("produto_id") == product_id and h.get("ativo", True):
                item = dict(h)
                item["fornecedor"] = self.supplier_name(item.get("fornecedor_id", "")) or item.get("fornecedor_nome", "")
                item["responsavel"] = self.responsible_name(item.get("responsavel_id", ""))
                rows.append(item)
        return sorted(rows, key=lambda x: x.get("data_compra") or x.get("data_cotacao") or x.get("atualizado_em", ""), reverse=True)

    def add_supplier_history(self, product_id: str, fornecedor_id: str, preco_cotado: float = 0.0, preco_pago: float = 0.0, data_cotacao: str = "", data_compra: str = "", prazo_entrega_dias: int = 0, status_negociacao: str = "Cotado", responsavel_id: str = "", observacao: str = "") -> dict:
        """Cria registro comercial item-fornecedor sem sobrescrever histórico antigo."""
        if not self.get_product(product_id):
            raise ValueError("Produto não encontrado.")
        if not fornecedor_id:
            raise ValueError("Selecione um fornecedor.")
        rec = {
            "id": f"hist-{uuid.uuid4().hex[:10]}", "produto_id": product_id, "fornecedor_id": fornecedor_id,
            "fornecedor_nome": self.supplier_name(fornecedor_id), "codigo_fornecedor": "",
            "preco_cotado": max(float(preco_cotado or 0), 0.0), "preco_pago": max(float(preco_pago or 0), 0.0),
            "melhor_preco_registrado": 0.0, "variacao_percentual": 0.0,
            "data_cotacao": data_cotacao, "data_compra": data_compra,
            "prazo_entrega_dias": max(int(prazo_entrega_dias or 0), 0), "status_negociacao": status_negociacao,
            "responsavel_id": responsavel_id, "observacao": observacao.strip(), "origem": "usuario",
            "ativo": True, "criado_em": now_iso(), "atualizado_em": now_iso()
        }
        self.data.setdefault("supplier_item_history", []).append(rec)
        self.record_activity("Histórico fornecedor", f"Registro comercial adicionado para {self.get_product(product_id).get('nome','produto')}", product_id, None, "", responsavel_id, rec["id"], status_negociacao)
        self.audit("historico_fornecedor", rec["id"], "criar", {}, rec)
        self.save()
        return rec

    def supplier_comparison_for_product(self, product_id: str) -> dict:
        """Calcula indicadores para comparação inteligente entre fornecedores."""
        rows = self.supplier_history_for_product(product_id)
        paid = [r for r in rows if float(r.get("preco_pago") or 0) > 0]
        quoted = [r for r in rows if float(r.get("preco_cotado") or 0) > 0]
        best_price = min(paid or quoted, key=lambda r: float(r.get("preco_pago") or r.get("preco_cotado") or 0), default=None)
        deadlines = [r for r in rows if int(r.get("prazo_entrega_dias") or 0) > 0]
        best_deadline = min(deadlines, key=lambda r: int(r.get("prazo_entrega_dias") or 0), default=None)
        usage = {}
        for r in rows:
            usage[r.get("fornecedor") or r.get("fornecedor_nome") or "Fornecedor"] = usage.get(r.get("fornecedor") or r.get("fornecedor_nome") or "Fornecedor", 0) + 1
        most_used = max(usage.items(), key=lambda kv: kv[1], default=("", 0))
        return {"rows": rows, "best_price": best_price, "best_deadline": best_deadline, "most_used": most_used}

    def preview_sku(self, categoria_id: str = "", nome: str = "", marca_id: str = "", tipo_material: str = "") -> str:
        """Gera prévia de SKU usando as mesmas regras do cadastro definitivo."""
        cat_name = self.category_name(categoria_id)
        brand_name = self.brand_name(marca_id)
        base = cat_name or nome or tipo_material or brand_name or "Produto"
        prefix = slug_prefix(base)
        existing = {p.get("sku", "") for p in self.products()}
        seq = 1
        while f"{prefix}-{seq:04d}" in existing:
            seq += 1
        return f"{prefix}-{seq:04d}"

    def products_by_category(self, category_id: str) -> list[dict]:
        return [p for p in self.products() if p.get("categoria_id") == category_id]

    def table_columns(self, table_name: str) -> list[int]:
        return self.data.get("settings", {}).get("table_columns", {}).get(table_name, [])

    def save_table_columns(self, table_name: str, widths: list[int]) -> None:
        self.data.setdefault("settings", {}).setdefault("table_columns", {})[table_name] = widths
        self.save()


    def _is_integer_quantity(self, value: float) -> bool:
        try:
            return abs(float(value) - round(float(value))) < 1e-9
        except Exception:
            return False

    def validate_quantity_for_unit(self, unit_code: str, quantidade: float, label: str = "quantidade") -> float:
        quantidade = float(quantidade or 0)
        if quantidade < 0:
            raise ValueError(f"A {label} não pode ser negativa.")
        if not is_fractional(unit_code, self.units()) and not self._is_integer_quantity(quantidade):
            raise ValueError(f"A unidade '{unit_code}' aceita apenas números inteiros. Não use valores fracionados.")
        return int(round(quantidade)) if not is_fractional(unit_code, self.units()) else quantidade

    def record_activity(self, tipo: str, descricao: str, product_id: str = "", quantidade: float | int | None = None, unidade: str = "", responsible_id: str = "", link_id: str = "", status: str = "") -> dict:
        activity = {
            "id": str(uuid.uuid4()), "tipo": tipo, "descricao": descricao, "produto_id": product_id,
            "quantidade": quantidade if quantidade is not None else "", "unidade": unidade,
            "responsavel_id": responsible_id, "responsavel": self.responsible_name(responsible_id),
            "link_id": link_id, "status": status, "criado_em": now_iso()
        }
        self.data.setdefault("activities", []).append(activity)
        return activity

        # Normaliza e valida os dados recebidos dos formulários antes de salvar.
    # Aqui ficam regras como SKU único, data de validade obrigatória e unidade fracionável.
    def normalize_product_payload(self, payload: dict[str, Any], existing_id: str | None = None) -> dict[str, Any]:
        payload = deepcopy(payload)
        unit_code = (payload.get("unidade_medida") or "un").lower()
        unit = self.unit(unit_code)
        frac = is_fractional(unit_code, self.units())
        precision = int(unit.get("precisao_decimal", self.data.get("settings", {}).get("precisao_decimal_padrao", 2)))
        payload["nome"] = title_pt(payload.get("nome", ""))
        payload["unidade_medida"] = unit_code
        payload["tipo_material"] = payload.get("tipo_material") or unit.get("tipo_material_padrao", "Unitário")
        if not frac:
            payload["quantidade_base"] = 1.0
        else:
            payload["quantidade_base"] = round_value(max(float(payload.get("quantidade_base") or 1), 0.0), precision, self.data.get("settings", {}).get("arredondamento", "half_up"))
            if payload["quantidade_base"] <= 0:
                payload["quantidade_base"] = 1.0
        payload["estoque_atual"] = self.validate_quantity_for_unit(unit_code, max(float(payload.get("estoque_atual") or 0), 0.0), "estoque atual")
        payload["estoque_minimo"] = self.validate_quantity_for_unit(unit_code, max(float(payload.get("estoque_minimo") or 0), 0.0), "estoque mínimo")
        payload["preco_custo"] = max(float(payload.get("preco_custo") or 0), 0.0)
        payload["preco_venda"] = max(float(payload.get("preco_venda") or 0), 0.0)
        payload["descricao"] = (payload.get("descricao") or "").strip()
        brand_id = payload.get("marca_id")
        brand_name = title_pt(payload.get("marca") or "")
        if brand_id:
            payload["marca"] = self.brand_name(brand_id)
        elif brand_name:
            brand = self.create_reference("brands", brand_name)
            payload["marca_id"] = brand["id"]
            payload["marca"] = brand["nome"]
        else:
            payload["marca_id"] = ""
            payload["marca"] = ""
        if not payload.get("sku"):
            cat_name = self.category_name(payload.get("categoria_id", ""))
            prefix = slug_prefix(cat_name or payload["nome"])
            seq = sum(1 for p in self.products() if (p.get("sku") or "").startswith(prefix)) + 1
            payload["sku"] = f"{prefix}-{seq:04d}"
        else:
            payload["sku"] = (payload["sku"] or "").strip().upper().replace(" ", "-")
        payload["controla_lote"] = bool(payload.get("controla_lote", False))
        payload["controla_validade"] = bool(payload.get("controla_validade", False))
        data_validade = (payload.get("data_validade") or payload.get("validade") or "").strip()
        if payload["controla_validade"] and not data_validade:
            raise ValueError("Informe a data de validade quando o controle de validade estiver ativo.")
        payload["data_validade"] = data_validade if payload["controla_validade"] else ""
        payload["validade"] = payload["data_validade"]
        payload["controla_serial"] = bool(payload.get("controla_serial", False))
        payload["multiestoque_id"] = payload.get("multiestoque_id") or self.data.get("settings", {}).get("estoque_principal", "estoque-principal")
        payload.setdefault("compra_status", "")
        payload.setdefault("ultima_solicitacao_compra_id", "")
        payload["ativo"] = True
        return payload

        # Cria produto e registra automaticamente movimentação inicial e atividade recente,
    # evitando que cadastros novos fiquem invisíveis nos históricos operacionais.
    def add_product(self, payload: dict[str, Any]) -> dict:
        p = self.normalize_product_payload(payload)
        p["id"] = str(uuid.uuid4())
        p["criado_em"] = now_iso()
        p["atualizado_em"] = p["criado_em"]
        p.setdefault("metadados", {})
        self.data.setdefault("products", []).append(p)
        self.audit("produto", p["id"], "criar", {}, p)
        # Movimento inicial e atividade recente de criação do item.
        movimento = {
            "id": str(uuid.uuid4()), "produto_id": p["id"], "tipo": "cadastro",
            "quantidade": float(p.get("estoque_atual", 0)), "unidade_utilizada": p.get("unidade_medida", ""),
            "quantidade_convertida": float(p.get("estoque_atual", 0)), "unidade_estoque": p.get("unidade_medida", ""),
            "quantidade_fisica": physical_total(p.get("estoque_atual", 0), p.get("quantidade_base", 1), p.get("unidade_medida", "un"), self.units()),
            "saldo_anterior": 0, "saldo_restante": p.get("estoque_atual", 0),
            "responsavel_id": self.data.get("settings", {}).get("responsavel_padrao", "resp-padrao"),
            "responsavel": self.responsible_name(self.data.get("settings", {}).get("responsavel_padrao", "resp-padrao")),
            "origem_destino": "Cadastro inicial", "observacao": "Movimentação inicial gerada automaticamente no cadastro do produto.",
            "purchase_request_id": "", "criado_em": now_iso()
        }
        self.data.setdefault("movements", []).append(movimento)
        self.record_activity("Produto criado", f"Item cadastrado: {p.get('nome','')}", p["id"], p.get("estoque_atual", 0), p.get("unidade_medida", ""), movimento["responsavel_id"], movimento["id"], "Cadastro")
        self.save()
        return p

    def update_product(self, product_id: str, payload: dict[str, Any]) -> dict:
        products = self.data.setdefault("products", [])
        idx = next(i for i, p in enumerate(products) if p["id"] == product_id)
        old = deepcopy(products[idx])
        updated = deepcopy(old)
        updated.update(payload)
        updated = self.normalize_product_payload(updated, product_id)
        updated["id"] = product_id
        updated["criado_em"] = old.get("criado_em", now_iso())
        updated["atualizado_em"] = now_iso()
        products[idx] = updated
        self.audit("produto", product_id, "editar", old, updated)
        self.save()
        return updated

    def delete_product(self, product_id: str) -> None:
        for p in self.data.setdefault("products", []):
            if p["id"] == product_id:
                old = deepcopy(p)
                p["ativo"] = False
                p["atualizado_em"] = now_iso()
                self.audit("produto", product_id, "excluir", old, p)
                self.save()
                return

        # Registra entradas, saídas ou ajustes com validação de unidade, conversão,
    # saldo anterior/restante e vínculo opcional com solicitação de compra.
    def add_movement(self, product_id: str, tipo: str, quantidade: float, unidade_usada: str | None = None, responsavel_id: str = "", origem_destino: str = "", observacao: str = "", purchase_request_id: str = "") -> dict:
        product = next(p for p in self.data.get("products", []) if p["id"] == product_id)
        tipo = tipo.lower()
        if tipo not in {"entrada", "saida", "ajuste"}:
            raise ValueError("Tipo de movimentação inválido.")
        unidade_usada = (unidade_usada or product["unidade_medida"]).lower()
        quantidade = self.validate_quantity_for_unit(unidade_usada, max(float(quantidade), 0.0), "quantidade movimentada")
        if quantidade <= 0:
            raise ValueError("A quantidade deve ser maior que zero.")
        quantidade_convertida = quantidade
        if unidade_usada != product["unidade_medida"]:
            quantidade_convertida = convert_value(quantidade, unidade_usada, product["unidade_medida"], self.units(), self.data.get("settings", {}).get("arredondamento", "half_up"))
        quantidade_convertida = self.validate_quantity_for_unit(product["unidade_medida"], quantidade_convertida, "quantidade convertida")
        saldo_anterior = float(product.get("estoque_atual", 0))
        if tipo == "entrada":
            saldo_novo = saldo_anterior + quantidade_convertida
        elif tipo == "saida":
            saldo_novo = saldo_anterior - quantidade_convertida
            if saldo_novo < 0:
                raise ValueError("Saída maior do que o saldo disponível.")
        else:
            saldo_novo = quantidade_convertida
        if not is_fractional(product["unidade_medida"], self.units()):
            saldo_novo = int(round(saldo_novo))
        old = deepcopy(product)
        product["estoque_atual"] = saldo_novo
        product["atualizado_em"] = now_iso()
        movimento = {
            "id": str(uuid.uuid4()), "produto_id": product_id, "tipo": tipo,
            "quantidade": quantidade, "unidade_utilizada": unidade_usada,
            "quantidade_convertida": quantidade_convertida, "unidade_estoque": product["unidade_medida"],
            "quantidade_fisica": physical_total(quantidade_convertida, product.get("quantidade_base", 1), product["unidade_medida"], self.units()),
            "saldo_anterior": saldo_anterior, "saldo_restante": saldo_novo,
            "responsavel_id": responsavel_id, "responsavel": self.responsible_name(responsavel_id),
            "origem_destino": origem_destino.strip(), "observacao": observacao.strip(),
            "purchase_request_id": purchase_request_id, "criado_em": now_iso()
        }
        self.data.setdefault("movements", []).append(movimento)
        self.record_activity("Movimentação", f"{tipo.title()} registrada para {product.get('nome','produto')}", product_id, quantidade, unidade_usada, responsavel_id, movimento["id"], tipo.title())
        self.audit("movimentacao", movimento["id"], tipo, {"produto": old}, {"produto": product, "movimento": movimento})
        self.save()
        return movimento

    # Compras e reposição
    def purchase_requests(self, statuses: list[str] | set[str] | None = None, product_id: str | None = None) -> list[dict]:
        rows = [r for r in self.data.get("purchase_requests", []) if r.get("ativo", True)]
        if statuses is not None:
            rows = [r for r in rows if r.get("status") in statuses]
        if product_id:
            rows = [r for r in rows if r.get("produto_id") == product_id]
        products = {p["id"]: p for p in self.products()}
        out = []
        for r in rows:
            item = dict(r)
            p = products.get(item.get("produto_id"), {})
            item["produto_nome"] = p.get("nome", "Produto removido")
            item["sku"] = p.get("sku", "")
            item["unidade_medida"] = p.get("unidade_medida", "")
            item["fornecedor"] = self.supplier_name(item.get("fornecedor_id", ""))
            item["responsavel_compra"] = self.responsible_name(item.get("responsavel_compra_id", ""))
            return_placeholder = None
            out.append(item)
        return sorted(out, key=lambda x: x.get("atualizado_em", x.get("criado_em", "")), reverse=True)

    def latest_purchase_for_product(self, product_id: str) -> dict | None:
        rows = self.purchase_requests(product_id=product_id)
        return rows[0] if rows else None

    def purchase_status_for_product(self, product_id: str) -> str:
        req = self.latest_purchase_for_product(product_id)
        if req and req.get("status") not in FINAL_PURCHASE_STATUSES:
            return req.get("status", "")
        return ""

        # Inicia o fluxo de reposição vinculando solicitação ao produto e criando pendência ativa.
    def create_purchase_request(self, product_id: str, quantidade: float, solicitante_id: str, prioridade: str, justificativa: str, observacao: str = "") -> dict:
        p = self.get_product(product_id)
        if not p:
            raise ValueError("Produto não encontrado.")
        quantidade = self.validate_quantity_for_unit(p.get("unidade_medida", "un"), max(float(quantidade or 0), 0.0), "quantidade solicitada")
        if quantidade <= 0:
            raise ValueError("Informe uma quantidade solicitada maior que zero.")
        req = {
            "id": f"compra-{uuid.uuid4().hex[:10]}", "produto_id": product_id,
            "quantidade_solicitada": quantidade, "quantidade_recebida": 0.0,
            "unidade_medida": p.get("unidade_medida", "un"),
            "solicitante_id": solicitante_id, "solicitante": self.responsible_name(solicitante_id),
            "prioridade": prioridade or "Normal", "justificativa": justificativa.strip(),
            "observacao": observacao.strip(), "status": "Solicitação Criada", "fornecedor_id": p.get("fornecedor_id", ""),
            "responsavel_compra_id": "", "numero_pedido": "", "valor": 0.0, "previsao_entrega": "",
            "ativo": True, "criado_em": now_iso(), "atualizado_em": now_iso(), "timeline": []
        }
        self.data.setdefault("purchase_requests", []).append(req)
        self._purchase_event(req, "Solicitação Criada", solicitante_id, "Solicitação de compra criada", observacao)
        self._set_product_purchase_status(product_id, req["id"], req["status"])
        self.record_activity("Solicitação de compra", f"Compra solicitada para {p.get('nome','produto')}", product_id, quantidade, p.get("unidade_medida", ""), solicitante_id, req["id"], req["status"])
        self.audit("compra", req["id"], "criar", {}, req)
        self.save()
        return req

    def _set_product_purchase_status(self, product_id: str, request_id: str, status: str) -> None:
        for p in self.data.get("products", []):
            if p.get("id") == product_id:
                p["ultima_solicitacao_compra_id"] = request_id
                p["compra_status"] = "" if status in FINAL_PURCHASE_STATUSES else status
                p["atualizado_em"] = now_iso()
                break

    def _purchase_event(self, req: dict, status: str, responsible_id: str, acao: str, observacao: str = "") -> dict:
        ev = {
            "id": str(uuid.uuid4()), "purchase_request_id": req["id"], "produto_id": req.get("produto_id"),
            "status": status, "acao": acao, "responsavel_id": responsible_id,
            "responsavel": self.responsible_name(responsible_id), "observacao": observacao.strip(), "criado_em": now_iso()
        }
        req.setdefault("timeline", []).append(ev)
        self.data.setdefault("purchase_events", []).append(ev)
        return ev

    def update_purchase_status(self, request_id: str, status: str, responsible_id: str = "", supplier_id: str = "", order_number: str = "", value: float = 0.0, expected_date: str = "", observacao: str = "") -> dict:
        req = next((r for r in self.data.setdefault("purchase_requests", []) if r["id"] == request_id), None)
        if not req:
            raise ValueError("Solicitação de compra não encontrada.")
        old = deepcopy(req)
        req["status"] = status
        if responsible_id:
            req["responsavel_compra_id"] = responsible_id
        if supplier_id:
            req["fornecedor_id"] = supplier_id
        if order_number:
            req["numero_pedido"] = order_number.strip()
        if value is not None:
            req["valor"] = max(float(value or 0), 0.0)
        if expected_date:
            req["previsao_entrega"] = (expected_date or "").strip()
        req["atualizado_em"] = now_iso()
        self._purchase_event(req, status, responsible_id, f"Status alterado para {status}", observacao)
        self._set_product_purchase_status(req["produto_id"], req["id"], status)
        if status in FINAL_PURCHASE_STATUSES or status == "Rejeitado":
            self.record_activity("Compra finalizada", f"Solicitação {req['id']} marcada como {status}", req.get("produto_id", ""), req.get("quantidade_recebida", 0), req.get("unidade_medida", ""), responsible_id, req["id"], status)
        self.audit("compra", req["id"], "atualizar_status", old, req)
        self.save()
        return req

        # Confirma recebimento parcial ou total e gera entrada automática no estoque.
    def receive_purchase(self, request_id: str, quantidade_recebida: float, responsible_id: str, observacao: str = "", avarias: str = "") -> dict:
        req = next((r for r in self.data.setdefault("purchase_requests", []) if r["id"] == request_id), None)
        if not req:
            raise ValueError("Solicitação de compra não encontrada.")
        quantidade_recebida = self.validate_quantity_for_unit(req.get("unidade_medida", "un"), max(float(quantidade_recebida or 0), 0.0), "quantidade recebida")
        if quantidade_recebida <= 0:
            raise ValueError("Informe a quantidade recebida.")
        old = deepcopy(req)
        total_recebido = float(req.get("quantidade_recebida", 0)) + quantidade_recebida
        solicitado = float(req.get("quantidade_solicitada", 0))
        status = "Compra Recebida Integralmente" if total_recebido >= solicitado else "Compra Parcial Recebida"
        req["quantidade_recebida"] = total_recebido
        req["status"] = status
        req["avarias"] = avarias.strip()
        req["atualizado_em"] = now_iso()
        mov = self.add_movement(
            req["produto_id"], "entrada", quantidade_recebida, req.get("unidade_medida"),
            responsible_id, f"Recebimento de compra {req['id']}", observacao, purchase_request_id=req["id"]
        )
        self._purchase_event(req, status, responsible_id, f"Recebimento registrado: {quantidade_recebida} {req.get('unidade_medida','')}", observacao + (f" | Avarias: {avarias}" if avarias else ""))
        self._set_product_purchase_status(req["produto_id"], req["id"], status)
        self.record_activity("Recebimento de compra", f"Recebimento {status.lower()} da solicitação {req['id']}", req.get("produto_id", ""), quantidade_recebida, req.get("unidade_medida", ""), responsible_id, req["id"], status)
        self.audit("compra", req["id"], "receber", old, {"compra": req, "movimentacao": mov})
        self.save()
        return req

    def product_purchase_history(self, product_id: str) -> list[dict]:
        return self.purchase_requests(product_id=product_id)

    def audit(self, entidade: str, entidade_id: str, acao: str, antes: dict, depois: dict) -> None:
        self.data.setdefault("audits", []).append({"id": str(uuid.uuid4()), "entidade": entidade, "entidade_id": entidade_id, "acao": acao, "antes": antes, "depois": depois, "criado_em": now_iso()})

    def low_stock_products(self) -> list[dict]:
        return [p for p in self.products() if float(p.get("estoque_atual", 0)) <= float(p.get("estoque_minimo", 0)) and float(p.get("estoque_atual", 0)) > 0]

    def out_stock_products(self) -> list[dict]:
        return [p for p in self.products() if float(p.get("estoque_atual", 0)) <= 0]

    def analysis_products(self) -> list[dict]:
        ids = {r.get("produto_id") for r in self.purchase_requests(statuses={"Em Análise", "Aguardando Aprovação", "Solicitação Criada"})}
        return [p for p in self.products() if p.get("id") in ids]

        # Consolida indicadores usados pelo dashboard sem duplicar lógica na camada visual.
    def dashboard(self) -> dict:
        prods = self.products()
        low_all = [p for p in prods if float(p.get("estoque_atual", 0)) <= float(p.get("estoque_minimo", 0))]
        out = self.out_stock_products()
        active_purchases = self.purchase_requests(statuses=ACTIVE_PURCHASE_STATUSES)
        awaiting_receipt = self.purchase_requests(statuses={"Pedido Realizado", "Compra Parcial Recebida"})
        analysis = self.analysis_products()
        return {
            "total_produtos": len(prods), "itens_analise": len(analysis),
            "baixo_estoque": len(low_all), "sem_estoque": len(out),
            "movimentacoes": len(self.data.get("movements", [])),
            "compras_pendentes": len(active_purchases), "aguardando_recebimento": len(awaiting_receipt),
            "itens_baixo": low_all[:8]
        }

    def recent_activities(self, limit: int = 20) -> list[dict]:
        products = {p["id"]: p for p in self.products()}
        rows = []
        for a in self.data.get("activities", []):
            item = dict(a)
            p = products.get(item.get("produto_id"), {})
            item["produto_nome"] = p.get("nome", item.get("produto_nome", ""))
            item["sku"] = p.get("sku", "")
            rows.append(item)
        return sorted(rows, key=lambda x: x.get("criado_em", ""), reverse=True)[:limit]

    def recent_movements(self, limit: int = 20) -> list[dict]:
        products = {p["id"]: p for p in self.products()}
        rows = []
        for m in reversed(self.data.get("movements", [])[-limit:]):
            p = products.get(m.get("produto_id"), {})
            item = dict(m)
            item["produto_nome"] = p.get("nome", "Produto removido")
            item["sku"] = p.get("sku", "")
            rows.append(item)
        return rows

# ---------------------------------------------------------------------------
# Seleção automática da camada de persistência
# ---------------------------------------------------------------------------
# A UI continua importando StockService deste módulo para preservar
# compatibilidade. Porém, quando BOXIO_DB_MODE=postgresql, substituímos a
# implementação JSON pela implementação PostgreSQL/Neon. Assim o sistema passa
# a ler e gravar diretamente no banco online, mantendo JSON apenas como fallback.
try:
    import os
    from dotenv import load_dotenv
    load_dotenv()
    if os.getenv("BOXIO_DB_MODE", "json").strip().lower() in {"postgres", "postgresql", "neon"}:
        from src.services.stock_service_postgres import StockServicePostgres as StockService  # type: ignore[assignment]
except Exception:
    # Se a configuração PostgreSQL falhar durante a transição, o sistema mantém
    # a implementação JSON para permitir diagnóstico sem impedir a abertura.
    pass
