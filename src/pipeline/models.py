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

from pydantic import BaseModel, Field, model_validator


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

    # Field order matches the committed `public/data/products.json` byte for
    # byte (parity gate, PLAN.md Fase 1) — precio_regular/descuento_pct sit
    # right after precio_venta, not at the end.
    id: str
    proveedor: str
    categoria: str
    # High-level grouping (spec 0001, RFC-0001 §2.4 amended 2026-09-17,
    # type updated 2026-09-18): one or more of Serlaca's real
    # productCategoryIds ("1"/"2"/"3"), or ["4"] (fallback) when the
    # product didn't match any of them. A product can belong to more than
    # one group at once — verified against the real API 2026-09-17 (see
    # docs/serlaca-api.md), so this is a list, never a bare string.
    codCategoria: list[str]
    nombre: str
    presentacion: str
    descripcion: str
    precio_venta: int
    precio_regular: int | None = Field(default=None)
    descuento_pct: int | None = Field(default=None)
    imagen: str
    en_oferta: bool
    tags: list[str]

    @model_validator(mode="after")
    def _check_cod_categoria(self) -> "Product":
        """`codCategoria` (spec 0001, AC-2/AC-3): nunca vacío, y cada id
        tiene que ser uno de los cuatro válidos — falla rápido ante un bug
        de `ingest`/`transform`, no solo ante el campo ausente.
        """
        if not self.codCategoria:
            raise ValueError("codCategoria no puede ser una lista vacía")
        allowed = {"1", "2", "3", "4"}
        invalid = [cod for cod in self.codCategoria if cod not in allowed]
        if invalid:
            raise ValueError(
                f"codCategoria contiene id(s) inválido(s): {invalid} (válidos: {sorted(allowed)})"
            )
        return self

    @model_validator(mode="after")
    def _check_offer_fields(self) -> "Product":
        """Mirrors `isProduct`'s offer-pricing checks (spec 0007).

        `precio_regular`/`descuento_pct` must appear together, the discount
        must be an integer percentage in 1..99, and the regular price must
        be strictly greater than the (already discounted) `precio_venta`.
        """
        has_regular = self.precio_regular is not None
        has_discount = self.descuento_pct is not None
        if has_regular != has_discount:
            raise ValueError("precio_regular y descuento_pct deben aparecer juntos")
        if has_regular and has_discount:
            assert self.descuento_pct is not None
            assert self.precio_regular is not None
            if not (1 <= self.descuento_pct <= 99):
                raise ValueError(f"descuento_pct fuera de rango (1..99): {self.descuento_pct}")
            if self.precio_regular <= self.precio_venta:
                raise ValueError(
                    f"precio_regular ({self.precio_regular}) debe ser mayor que "
                    f"precio_venta ({self.precio_venta})"
                )
        return self

    def to_public_dict(self) -> dict[str, object]:
        """Serialize for `products.json`, omitting absent optional fields."""
        return self.model_dump(exclude_none=True)


def validate_products(raw: object) -> list[Product]:
    """Parse a raw JSON value into a typed `Product` list.

    Mirrors `src/lib/types.ts`'s `validateProducts` in `renovarte-catalogo`:
    raises with a precise message if `raw` is not a list or any row fails
    the `Product` contract, so a bad data file fails loud instead of
    shipping broken pages.
    """
    if not isinstance(raw, list):
        raise ValueError(f"products data must be an array, got {type(raw).__name__}")
    products: list[Product] = []
    for index, row in enumerate(raw):
        try:
            products.append(Product.model_validate(row))
        except Exception as error:
            raise ValueError(f"products data: row {index} is not a valid Product: {row!r}") from error
    return products
