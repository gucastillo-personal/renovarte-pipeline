"""Defensa en origen antes de abrir el PR (Fase 3 del plan). Espeja
`scripts/check-leak.mjs` de renovarte-catalogo (constitution §I.5) — la
misma regla aplicada en el otro extremo: nada de costo/margen/precio de
lista de LACA puede llegar a un archivo que este pipeline publique.
"""

import re
from dataclasses import dataclass
from pathlib import Path

FORBIDDEN: tuple[re.Pattern[str], ...] = (
    re.compile(r"precio_costo", re.IGNORECASE),
    re.compile(r"precio_publico_laca", re.IGNORECASE),
    re.compile(r"precio_lista_laca", re.IGNORECASE),
    re.compile(r"precio_profesional", re.IGNORECASE),
    re.compile(r"margin_percent", re.IGNORECASE),
    re.compile(r"\bmargen\b", re.IGNORECASE),
    re.compile(r"(?<!\w)costo(?!\w)", re.IGNORECASE | re.UNICODE),
)


@dataclass(frozen=True)
class LeakHit:
    file: str
    token: str


def check_file_for_leaks(path: str | Path) -> list[LeakHit]:
    """Every forbidden pattern that matches in `path`'s content, empty if none."""
    content = Path(path).read_text(encoding="utf-8")
    hits = []
    for pattern in FORBIDDEN:
        match = pattern.search(content)
        if match:
            hits.append(LeakHit(file=str(path), token=match.group(0)))
    return hits
