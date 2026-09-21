"""Serlaca API source adapter (spec 0009), split in two stages:

    Stage 1 — fetch_all_serlaca_pages(): download RAW, untransformed data.
    Stage 2 — raw_to_cost_rows(): filter + map a raw dump into `CostRow`s.

Reference: docs/serlaca-api.md (in renovarte-catalogo). Runs LOCALLY or in
CI — never as part of any web runtime. `api_key` comes from `.env`/
`.env.local` (`SERLACA_API_KEY`).
"""

import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from pipeline.models import CostRow
from pipeline.sources.html import clean_name, format_size, html_to_text

_ENDPOINT = "https://api.serlaca.com/Products/ReadProducts"
# Las imágenes NO están en api.serlaca.com — se sirven desde el sitio de LACA.
DEFAULT_IMAGE_BASE = "https://www.laboratoriolaca.com"
_PLACEHOLDER_IMAGE = "/img/placeholder.svg"


# ---------------------------------------------------------------------------
# Stage 1 — download raw
# ---------------------------------------------------------------------------


@dataclass
class RawDump:
    data_objects: list[Any]
    total_items: int
    pages: int


def fetch_all_serlaca_pages(
    api_key: str,
    laca_id: str,
    category_ids: list[int] | None = None,
    client: httpx.Client | None = None,
    timeout_s: float = 15.0,
    max_retries: int = 2,
    retry_base_s: float = 0.5,
) -> RawDump:
    """Walk every page of `Products/ReadProducts` and return the
    concatenated `dataObjects` **exactly as the API returns them** — no
    filtering, no field validation, no mapping (that is the transform
    stage). Only the envelope is checked. Raises on auth failure, an error
    envelope, an unexpected shape, or exhausted retries.
    """
    if not api_key:
        raise ValueError("falta SERLACA_API_KEY")
    if not laca_id:
        raise ValueError("falta SERLACA_LACA_ID")

    owns_client = client is None
    http = client or httpx.Client(timeout=timeout_s)
    try:
        data_objects: list[Any] = []
        page = 1
        total_pages = 1

        while page <= total_pages:
            payload = _fetch_page(http, api_key, laca_id, category_ids or [], page, max_retries, retry_base_s)
            raw_total_pages = payload.get("totalPages")
            total_pages = raw_total_pages if isinstance(raw_total_pages, int) and raw_total_pages > 0 else 1
            data_objects.extend(payload["dataObjects"])
            page += 1

        return RawDump(data_objects=data_objects, total_items=len(data_objects), pages=total_pages)
    finally:
        if owns_client:
            http.close()


def _fetch_page(
    http: httpx.Client,
    api_key: str,
    laca_id: str,
    category_ids: list[int],
    current_page: int,
    max_retries: int,
    retry_base_s: float,
) -> dict[str, Any]:
    body = {
        "currentPage": current_page,
        "productLineCodes": [],
        "productCompositionIds": [],
        "productNecessityIds": [],
        "productCategoryIds": category_ids,
        "productUseInIds": [],
        "searchText": "",
        "lacaId": laca_id,
    }
    headers = {
        "content-type": "application/json",
        "accept": "application/json",
        "apikey": api_key,
        "username": laca_id,
        "origin": "https://www.serlaca.com",
        "referer": "https://www.serlaca.com/",
    }

    attempt = 1
    while True:
        try:
            res = http.post(_ENDPOINT, json=body, headers=headers)
        except httpx.RequestError as error:
            if attempt > max_retries:
                raise RuntimeError(f"error de red pidiendo la página {current_page}: {error}") from error
            _backoff(attempt, retry_base_s)
            attempt += 1
            continue

        if res.status_code in (401, 403):
            raise RuntimeError(f"serlaca respondió {res.status_code}: SERLACA_API_KEY inválida, vencida o sin permisos")
        if (res.status_code == 429 or res.status_code >= 500) and attempt <= max_retries:
            _backoff(attempt, retry_base_s)
            attempt += 1
            continue
        if res.status_code >= 400:
            raise RuntimeError(f"serlaca respondió {res.status_code} en la página {current_page}")

        envelope = res.json()
        if envelope.get("error") is not None:
            raise RuntimeError(f"serlaca devolvió un error: {envelope['error']!r}")
        payload = envelope.get("payload")
        if not isinstance(payload, dict) or not isinstance(payload.get("dataObjects"), list):
            raise RuntimeError(f"respuesta inesperada en la página {current_page}: falta payload.dataObjects")
        return payload


def _backoff(attempt: int, base_s: float) -> None:
    time.sleep(base_s * (2 ** (attempt - 1)))


# ---------------------------------------------------------------------------
# Stage 2 — transform raw -> CostRow
# ---------------------------------------------------------------------------


def assert_serlaca_product(value: Any, index: int) -> None:
    """Validate the fields the transform reads; raise naming the first bad one."""
    if not isinstance(value, dict):
        raise ValueError(f"producto {index}: no es un objeto")
    for key in ("productCode", "name"):
        if not isinstance(value.get(key), str) or value[key] == "":
            raise ValueError(f'producto {index}: falta el campo "{key}"')
    price = value.get("price")
    if not isinstance(price, int | float) or isinstance(price, bool):
        raise ValueError(f'producto {index}: "price" ausente o no numérico')
    product_line = value.get("productLine")
    if not isinstance(product_line, dict) or not isinstance(product_line.get("name"), str):
        raise ValueError(f'producto {index}: falta "productLine.name"')
    if not isinstance(value.get("professionalExclusive"), bool):
        raise ValueError(f'producto {index}: falta "professionalExclusive"')


def map_to_cost_row(product: dict[str, Any], image_base: str) -> CostRow:
    """One raw Serlaca product -> one `CostRow`. Assumes
    `assert_serlaca_product` passed.
    """
    size = product.get("productSize") or {}
    image_url = product.get("imageURL")
    return CostRow(
        codigo=product["productCode"].strip(),
        nombre=clean_name(product["name"]),
        categoria=product["productLine"]["name"].strip(),
        presentacion=format_size(size.get("size"), size.get("measurementCode")),
        descripcion=html_to_text(product.get("detail")),
        # `price` IS RenovArte's cost; the margin is added later in build_catalog.
        precio_costo=product["price"],
        en_oferta=False,
        tags=[],
        imagen=f"{image_base}{image_url}" if image_url else _PLACEHOLDER_IMAGE,
    )


def group_ids_by_product_code(samples: dict[str, list[Any]]) -> dict[str, list[str]]:
    """Spec 0001: de los mismos `samples` que arma
    `pipeline.ingest.verify_category_groups.fetch_category_group_samples`
    (id `"1"`/`"2"`/`"3"` -> `dataObjects` crudos que ese id devolvió),
    arma `productCode -> lista ordenada de ids donde apareció`.

    Pura, sin red. Un producto puede legítimamente aparecer en más de un
    id — Serlaca no garantiza que `productCategoryIds` sea mutuamente
    excluyente por producto (verificado contra la API real 2026-09-17, ver
    `docs/serlaca-api.md`) — eso ya no es un error, es el dato real que
    `ingest` persiste para que `transform` arme `codCategoria`.
    """
    groups_by_code: dict[str, set[str]] = {}
    for group_id, objects in samples.items():
        for obj in objects:
            if not isinstance(obj, dict):
                continue
            code = obj.get("productCode")
            if not isinstance(code, str) or not code.strip():
                continue
            groups_by_code.setdefault(code.strip(), set()).add(group_id)
    return {code: sorted(groups) for code, groups in groups_by_code.items()}


@dataclass
class RawToCostRowsResult:
    rows: list[CostRow]
    warnings: list[str] = field(default_factory=list)


def raw_to_cost_rows(data_objects: list[Any], image_base: str = DEFAULT_IMAGE_BASE) -> RawToCostRowsResult:
    """A raw Serlaca dump -> `CostRow`s: validate each object, drop
    professional-exclusive products, map the rest.
    """
    warnings: list[str] = []
    rows: list[CostRow] = []
    excluded = 0

    for index, obj in enumerate(data_objects):
        assert_serlaca_product(obj, index)
        if obj["professionalExclusive"]:
            excluded += 1
            continue
        rows.append(map_to_cost_row(obj, image_base))

    if excluded > 0:
        warnings.append(f"{excluded} producto(s) profesional-exclusivo(s) excluido(s) del catálogo")
    if not rows:
        raise ValueError("el crudo no tiene productos publicables (¿todo profesional-exclusivo?)")

    return RawToCostRowsResult(rows=rows, warnings=warnings)
