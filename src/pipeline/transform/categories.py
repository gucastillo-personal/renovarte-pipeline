"""Category name cleanup for the transform stage (spec 0009). Serlaca's
`productLine.name` arrives with trailing periods ("Uñas."), typo duplicates
("Uñas." vs "Uñas"), a missing accent ("Proteccion Solar.") and a few
unwieldy slash-lists.
"""

import re

# Key = category after trailing-dot/space strip, lower-cased.
# Value = the display name to use. Edit freely to taste.
RENAMES: dict[str, str] = {
    "proteccion solar": "Protección Solar",
    "correctores / iluminadores": "Correctores e Iluminadores",
    "hidratación-humectación-tonificación": "Hidratación",
    "paletas / pincelería / artístico": "Pinceles y Paletas",
    "pre bases / bases / polvos / rubores / fijadores / preparación piel": "Rostro",
    "dermatocosmética dr. enero": "Dr. Enero",
}

_WHITESPACE_RE = re.compile(r"\s+")
_TRAILING_DOT_RE = re.compile(r"[.\s]+$")


def clean_category(raw: str) -> str:
    """Trim, collapse spaces, drop a trailing ".", then apply the rename map."""
    trimmed = _TRAILING_DOT_RE.sub("", _WHITESPACE_RE.sub(" ", raw.strip()))
    return RENAMES.get(trimmed.lower(), trimmed)
