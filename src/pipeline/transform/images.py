"""Local product image resolution for the CSV source (spec 0002)."""

from pathlib import Path

PLACEHOLDER_IMAGE = "/img/placeholder.svg"

# Real product photos win over the SVG placeholders shipped for the walking skeleton.
_EXT_PRIORITY = ("jpg", "jpeg", "webp", "png", "svg")


def resolve_image_path(codigo: str, public_dir: str | Path) -> str:
    """Public path to a product's image.

    Returns `/img/laca/<codigo>.<ext>` for the first matching file under
    `<public_dir>/img/laca/`, else the shared placeholder.
    """
    public_dir = Path(public_dir)
    for ext in _EXT_PRIORITY:
        rel = Path("img") / "laca" / f"{codigo}.{ext}"
        if (public_dir / rel).exists():
            return f"/{rel.as_posix()}"
    return PLACEHOLDER_IMAGE
