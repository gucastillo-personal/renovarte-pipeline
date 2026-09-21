"""`codCategoria` (spec 0001): agrupación de alto nivel por producto.

Se deriva en `ingest` a partir de tres llamadas reales a la API de Serlaca
(`productCategoryIds: ["1"]` / `["2"]` / `["3"]`, ver
`pipeline.ingest.verify_category_groups` y `pipeline.sources.serlaca_api`),
persistida por `productCode` en el crudo. Un producto puede pertenecer a
más de un grupo simultáneamente — verificado contra la API real
(2026-09-17): 11 de 24 `productLine` no son mutuamente excluyentes entre
grupos (ver `docs/serlaca-api.md`), así que `codCategoria` es una
**lista**, no un único id (decisión del CTO/CEO 2026-09-18, reemplaza el
diseño original que asumía una tabla estática `categoría específica →
grupo`).

Este módulo NO decide la clasificación (eso ya se resolvió en `ingest`,
que persiste el resultado real de la API) — solo normaliza esa lista a la
forma pública (ordenada, sin duplicados, nunca vacía) y aplica el
fallback `"4"` cuando un producto no apareció en ninguno de los tres
grupos.
"""

FALLBACK_COD_CATEGORIA = "4"


def resolve_cod_categoria(raw_group_ids: list[str] | None) -> list[str]:
    """Ids reales devueltos por Serlaca para este producto (0, 1 o más) ->
    forma pública de `codCategoria`: ordenada, sin duplicados, nunca
    vacía. `None`/lista vacía (el producto no apareció en ninguna de las
    tres llamadas por grupo) -> `["4"]` (fallback).
    """
    if not raw_group_ids:
        return [FALLBACK_COD_CATEGORIA]
    return sorted(set(raw_group_ids))
