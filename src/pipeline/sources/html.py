"""Text helpers for the Serlaca API adapter (spec 0009). The API returns
product copy as HTML with named/numeric entities (`&iacute;`, `<p>`,
`<br />`, `\\r\\n`) and product names sometimes ALL IN CAPS.
"""

import re

# Named entities that actually appear in serlaca `detail` fields, plus the
# common Latin-1 / punctuation set. Anything else falls through unchanged.
NAMED_ENTITIES: dict[str, str] = {
    "amp": "&", "lt": "<", "gt": ">", "quot": '"', "apos": "'", "nbsp": " ",
    "aacute": "á", "eacute": "é", "iacute": "í", "oacute": "ó", "uacute": "ú",
    "Aacute": "Á", "Eacute": "É", "Iacute": "Í", "Oacute": "Ó", "Uacute": "Ú",
    "ntilde": "ñ", "Ntilde": "Ñ", "uuml": "ü", "Uuml": "Ü", "agrave": "à",
    "ordf": "ª", "ordm": "º", "deg": "°", "trade": "™", "reg": "®", "copy": "©",
    "laquo": "«", "raquo": "»", "hellip": "…", "mdash": "—", "ndash": "–",
    "rsquo": "’", "lsquo": "‘", "ldquo": "“", "rdquo": "”",
    "middot": "·", "euro": "€", "pound": "£", "cent": "¢", "plusmn": "±",
    "times": "×", "divide": "÷", "frac12": "½", "frac14": "¼", "frac34": "¾",
}

_ENTITY_RE = re.compile(r"&(#x?[0-9a-fA-F]+|[a-zA-Z][a-zA-Z0-9]*);")
_BR_HR_RE = re.compile(r"<\s*(br|hr)\s*/?\s*>", re.IGNORECASE)
_BLOCK_CLOSE_RE = re.compile(r"<\s*/\s*(p|div|li|ul|ol|h[1-6]|tr)\s*>", re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")
_CRLF_RE = re.compile(r"\r\n?")
_NON_NEWLINE_WS_RE = re.compile(r"[^\S\n]+")
_SPACE_AROUND_NEWLINE_RE = re.compile(r" *\n *")
_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")


def decode_entities(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        body = match.group(1)
        if body.startswith("#"):
            is_hex = len(body) > 1 and body[1] in "xX"
            try:
                code = int(body[2:], 16) if is_hex else int(body[1:], 10)
            except ValueError:
                return match.group(0)
            if code <= 0 or code > 0x10FFFF:
                return match.group(0)
            try:
                return chr(code)
            except ValueError:
                return match.group(0)
        return NAMED_ENTITIES.get(body, match.group(0))

    return _ENTITY_RE.sub(replace, text)


def html_to_text(html: str | None) -> str:
    """HTML -> readable plain text: block tags become newlines, other tags
    drop, entities decode.
    """
    if not html:
        return ""
    with_breaks = _TAG_RE.sub("", _BLOCK_CLOSE_RE.sub("\n", _BR_HR_RE.sub("\n", html)))
    decoded = decode_entities(with_breaks)
    decoded = _CRLF_RE.sub("\n", decoded)
    decoded = _NON_NEWLINE_WS_RE.sub(" ", decoded)
    decoded = _SPACE_AROUND_NEWLINE_RE.sub("\n", decoded)
    decoded = _MULTI_NEWLINE_RE.sub("\n\n", decoded)
    return decoded.strip()


def clean_name(raw: str) -> str:
    """Collapse whitespace; Title Case a name that arrives entirely upper-cased."""
    collapsed = re.sub(r"\s+", " ", raw).strip()
    letters = "".join(ch for ch in collapsed if ch.isalpha())
    is_all_caps = len(letters) > 0 and letters == letters.upper()
    if not is_all_caps:
        return collapsed
    return " ".join(word[:1].upper() + word[1:] if word else word for word in collapsed.lower().split(" "))


def format_size(size: float | None, measurement_code: str | None) -> str:
    """`format_size(250, "mL")` -> `"250 ml"`. `size` absent -> `""`."""
    if size is None:
        return ""
    amount = _format_number(size)
    unit = (measurement_code or "").strip().lower()
    return f"{amount} {unit}" if unit else amount


def _format_number(value: float) -> str:
    """Match JS's `String(number)`: integral floats print without ".0"."""
    if isinstance(value, int) or value.is_integer():
        return str(int(value))
    return str(value)
