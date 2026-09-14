"""Persistencia de la decisión de precio por producto (spec 0008, AC-4).

`data/reference/precio_pdf_decisiones.json` (committed) — keyed por
`codigo`, guarda la fuente elegida (`abc` | `catalogo` | `actual`) y el
valor resultante. Nunca contiene `precio_profesional`, `precio_costo` ni
margen — mismo nivel de exposición que `products.json`.
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

Fuente = Literal["abc", "catalogo", "actual"]


@dataclass(frozen=True)
class PdfDecision:
    fuente: Fuente
    valor: int


def load_decisions(path: str | Path) -> dict[str, PdfDecision]:
    """A missing file means no decisions yet — returns `{}`."""
    file_path = Path(path).expanduser()
    if not file_path.exists():
        return {}
    raw = json.loads(file_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path}: se esperaba un objeto {{codigo: {{fuente, valor}}}}")
    decisions: dict[str, PdfDecision] = {}
    for codigo, entry in raw.items():
        if not isinstance(entry, dict) or entry.get("fuente") not in ("abc", "catalogo", "actual"):
            raise ValueError(f'{path}: entrada inválida para "{codigo}": {entry!r}')
        valor = entry.get("valor")
        if not isinstance(valor, int) or isinstance(valor, bool):
            raise ValueError(f'{path}: "{codigo}".valor debe ser un entero: {valor!r}')
        decisions[codigo] = PdfDecision(fuente=entry["fuente"], valor=valor)
    return decisions


def save_decisions(path: str | Path, decisions: dict[str, PdfDecision]) -> None:
    """Deterministic JSON, sorted by `codigo`, trailing newline — same
    convention as `products.json`.
    """
    out = Path(path).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    ordered = {codigo: asdict(decisions[codigo]) for codigo in sorted(decisions)}
    out.write_text(json.dumps(ordered, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
