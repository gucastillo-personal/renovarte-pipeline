"""Data models shared across the ingest -> transform pipeline.

`Product` mirrors the public schema owned by `renovarte-catalogo`
(RFC-0001 §2.4, amended by spec 0007 with the offer-pricing fields). These
are the only keys allowed in the `products.json` this pipeline publishes.
Real cost, applied margin and LACA list price must never appear here.

`CostRow` is the normalised, source-agnostic intermediate every source
adapter (`pipeline.sources.*`) produces; `pipeline.transform` turns those
into public `Product`s. `precio_costo` is consumed internally and never
emitted to `products.json`.
"""

from pydantic import BaseModel, Field


class CostRow(BaseModel):
    codigo: str
    nombre: str
    categoria: str
    presentacion: str
    descripcion: str
    # What the product costs RenovArte (con IVA, cuenta de distribuidora).
    # The margin is added on top. Never emitted to `products.json`.
    precio_costo: float
    en_oferta: bool
    tags: list[str]
    # Local `/img/...` path or a remote `https://...` URL.
    imagen: str


class Product(BaseModel):
    """Public product schema. See module docstring."""

    id: str
    proveedor: str
    categoria: str
    nombre: str
    presentacion: str
    descripcion: str
    precio_venta: int
    imagen: str
    en_oferta: bool
    tags: list[str]
    precio_regular: int | None = Field(default=None)
    descuento_pct: int | None = Field(default=None)

    def to_public_dict(self) -> dict[str, object]:
        """Serialize for `products.json`, omitting absent optional fields."""
        return self.model_dump(exclude_none=True)
