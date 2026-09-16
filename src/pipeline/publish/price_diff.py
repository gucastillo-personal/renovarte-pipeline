"""Diff producto por producto entre el `products.json` ya publicado y el
recién generado — insumo del POC event-driven `renovarte-events`.

Este módulo no sabe nada de AWS ni de SNS: solo produce un archivo de datos
neutro (`data/price-changes.json`) que otro repo (`renovarte-events/producer`)
consume para publicar el evento. Contrato completo en
`renovarte-events/docs/evento-price-changes.md`. Sin dependencias nuevas:
reusa `pipeline.models.validate_products`, ya presente en este repo.
"""

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pipeline.models import validate_products

ChangeKind = Literal["added", "removed", "price_up", "price_down"]


@dataclass(frozen=True)
class ProductChange:
    kind: ChangeKind
    id: str
    nombre: str
    old_price: int | None
    new_price: int | None


def compute_price_diff(old_products_json: Path, new_products_json: Path) -> list[ProductChange]:
    """Compara por `id` y `precio_venta`.

    `old_products_json` puede no existir (primera corrida del repo) — se
    trata como catálogo vacío, así que todo aparece como `added`.
    """
    old_raw = json.loads(old_products_json.read_text(encoding="utf-8")) if old_products_json.exists() else []
    new_raw = json.loads(new_products_json.read_text(encoding="utf-8"))
    old_by_id = {p.id: p for p in validate_products(old_raw)}
    new_by_id = {p.id: p for p in validate_products(new_raw)}

    changes: list[ProductChange] = []
    for product_id, new in new_by_id.items():
        old = old_by_id.get(product_id)
        if old is None:
            changes.append(ProductChange("added", product_id, new.nombre, None, new.precio_venta))
        elif new.precio_venta > old.precio_venta:
            changes.append(
                ProductChange("price_up", product_id, new.nombre, old.precio_venta, new.precio_venta)
            )
        elif new.precio_venta < old.precio_venta:
            changes.append(
                ProductChange("price_down", product_id, new.nombre, old.precio_venta, new.precio_venta)
            )
    for product_id, old in old_by_id.items():
        if product_id not in new_by_id:
            changes.append(ProductChange("removed", product_id, old.nombre, old.precio_venta, None))
    return changes


def write_price_diff(changes: list[ProductChange], out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "changes": [asdict(change) for change in changes],
    }
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out_path
