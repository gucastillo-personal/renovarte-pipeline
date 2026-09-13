"""Manual offer list (spec 0005). Serlaca's API has no promo field, so
RenovArte marks offers in `data/offers.json` (committed). Read at transform
time.

Shapes accepted for `codigos` (or the top-level value):
    ["A", "B"]                                  -> flag only (badge, no price change)
    {"A": {}, "B": {"descuento_pct": 10}}       -> per-code, optional % off precio_venta
"""

import json
import math
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Offer:
    """`descuento_pct`: percent off `precio_venta`, 0..100. 0 = badge only."""

    descuento_pct: float


def _parse_entry(file_path: str, codigo: str, raw: object) -> Offer:
    if raw is None or (isinstance(raw, dict)):
        pct = raw.get("descuento_pct") if isinstance(raw, dict) else None
        if pct is None:
            return Offer(descuento_pct=0)
        is_number = isinstance(pct, int | float) and not isinstance(pct, bool)
        if not is_number or not math.isfinite(pct) or not (0 <= pct < 100):
            raise ValueError(
                f'{file_path}: "{codigo}".descuento_pct inválido (esperado 0..100): {pct!r}'
            )
        return Offer(descuento_pct=pct)
    raise ValueError(f'{file_path}: entrada inválida para "{codigo}": {raw!r}')


def load_offers(file_path: str | Path) -> dict[str, Offer]:
    """Map of product code -> offer.

    A missing file is fine (no offers). Raises on invalid JSON or an
    unexpected shape.
    """
    path = Path(file_path)
    if not path.exists():
        return {}

    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"{file_path}: JSON inválido — {error}") from error

    if isinstance(parsed, list) or (isinstance(parsed, dict) and "codigos" not in parsed):
        value: object = parsed
    else:
        value = parsed.get("codigos") if isinstance(parsed, dict) else None

    offers: dict[str, Offer] = {}

    if isinstance(value, list):
        for codigo in value:
            if not isinstance(codigo, str):
                raise ValueError(f"{file_path}: se esperaban strings en el array de códigos")
            key = codigo.strip()
            if key:
                offers[key] = Offer(descuento_pct=0)
        return offers

    if isinstance(value, dict):
        for codigo, raw in value.items():
            key = codigo.strip()
            if key:
                offers[key] = _parse_entry(str(file_path), key, raw)
        return offers

    raise ValueError(
        f'{file_path}: se esperaba {{ "codigos": [...] | {{...}} }} o un array/objeto en la raíz'
    )
