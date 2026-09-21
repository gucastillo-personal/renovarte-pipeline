"""Verificación / spot-check manual de `codCategoria` contra la API real de
Serlaca (spec 0001, AC-1, `tasks.md` Tarea 1).

El mapeo de negocio ya está decidido por el CTO/CEO (`"1"` Cuidado facial,
`"2"` Cuidado corporal, `"3"` Cosmética, sin match `"4"` fallback).
`fetch_category_group_samples()` es además la pieza que `ingest`
(`pipeline.ingest.serlaca_download.run`) reusa en cada corrida normal para
persistir el grupo real de cada producto en el crudo — este módulo sigue
existiendo como herramienta de inspección manual/CLI
(`verify-category-groups`), separada de ese flujo automático.

**Actualización 2026-09-18:** la corrida real (2026-09-17) mostró que 11
de 24 categorías específicas (`productLine`) aparecen repartidas entre más
de un grupo — el CTO/CEO decidió que esto es un resultado válido y
esperado (`codCategoria` es una lista, ver `pipeline.transform.category_groups`),
no un error a resolver acá. `CategoryGroupReport.conflicts` sigue
existiendo como dato informativo (qué categorías se reparten y entre qué
grupos) para spot-checks manuales, pero ya no es una condición de "parar".

Separado en dos etapas, mismo patrón que `pipeline.sources.serlaca_api`
(Stage 1/Stage 2):

    fetch_category_group_samples() — red real, NO se unit-testea.
    build_category_group_report()  — pura, se unit-testea con fixtures.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from pipeline.sources.serlaca_api import fetch_all_serlaca_pages
from pipeline.transform.categories import clean_category

GROUP_IDS: tuple[str, ...] = ("1", "2", "3")

DEFAULT_RAW_DUMP_PATH = Path("data") / "input" / "serlaca-raw.json"
DEFAULT_REPORT_OUT_PATH = Path("data") / "input" / "category-group-report.json"


# ---------------------------------------------------------------------------
# Red real — no unit-testeado
# ---------------------------------------------------------------------------


def fetch_category_group_samples(
    env: dict[str, str | None], client: httpx.Client | None = None
) -> dict[str, list[Any]]:
    """`productCategoryIds` `"1"`/`"2"`/`"3"` -> los `dataObjects` crudos que
    cada uno devuelve, pidiéndolos por separado contra la API real. Reusa
    `fetch_all_serlaca_pages` tres veces (una por id). Red real — no se
    unit-testea, solo se corre manualmente con credenciales reales
    (constitution §II.6).
    """
    api_key = env.get("SERLACA_API_KEY") or ""
    laca_id = env.get("SERLACA_LACA_ID") or ""

    owns_client = client is None
    http = client or httpx.Client(timeout=15.0)
    try:
        samples: dict[str, list[Any]] = {}
        for group_id in GROUP_IDS:
            dump = fetch_all_serlaca_pages(
                api_key=api_key,
                laca_id=laca_id,
                category_ids=[int(group_id)],
                client=http,
            )
            samples[group_id] = dump.data_objects
        return samples
    finally:
        if owns_client:
            http.close()


# ---------------------------------------------------------------------------
# Pura — unit-testeada con fixtures
# ---------------------------------------------------------------------------


@dataclass
class CategoryGroupReport:
    categoria_to_groups: dict[str, set[str]]  # categoría limpia -> ids donde apareció
    conflicts: list[str]  # categorías que aparecieron en más de un id
    unclassified: list[str]  # categorías conocidas que no aparecieron en ningún id
    suggested_map: dict[str, str]  # categoría -> id único, solo para las sin conflicto


def build_category_group_report(
    samples: dict[str, list[Any]],
    known_categorias: set[str] | None = None,
) -> CategoryGroupReport:
    """Pura, sin red — se unit-testea con fixtures.

    `samples`: id (`"1"`/`"2"`/`"3"`) -> `dataObjects` crudos devueltos por
    ese filtro (ver `fetch_category_group_samples`). Agrupa por
    `productLine.name` limpio con el mismo `clean_category` que usa
    `transform`, ignorando `professionalExclusive: true` (esos productos ya
    se excluyen del catálogo publicado — spec 0001, pregunta abierta 4; no
    deberían distorsionar la clasificación de las categorías que sí se
    publican).

    `known_categorias` (opcional): el universo de categorías específicas
    hoy cargadas (p. ej. derivado del crudo ya bajado por `ingest`, con
    `productCategoryIds: []`) — se usa solo para poblar `unclassified`
    (categorías que no aparecen en ninguno de los samples de `"1"`/`"2"`/
    `"3"`). Sin este dato, `samples` por sí solo no alcanza para saber si
    falta una categoría: toda categoría que aparece en `samples` apareció,
    por construcción, en al menos un id.
    """
    categoria_to_groups: dict[str, set[str]] = {}
    for group_id, objects in samples.items():
        for obj in objects:
            if not isinstance(obj, dict):
                continue
            if obj.get("professionalExclusive") is True:
                continue
            product_line = obj.get("productLine")
            if not isinstance(product_line, dict) or not isinstance(product_line.get("name"), str):
                continue
            categoria = clean_category(product_line["name"])
            categoria_to_groups.setdefault(categoria, set()).add(group_id)

    conflicts = sorted(categoria for categoria, groups in categoria_to_groups.items() if len(groups) > 1)
    suggested_map = {
        categoria: next(iter(groups)) for categoria, groups in categoria_to_groups.items() if len(groups) == 1
    }
    unclassified = sorted((known_categorias or set()) - categoria_to_groups.keys())

    return CategoryGroupReport(
        categoria_to_groups=categoria_to_groups,
        conflicts=conflicts,
        unclassified=unclassified,
        suggested_map=suggested_map,
    )


# ---------------------------------------------------------------------------
# Orquestación (usada por el subcomando `verify-category-groups` en cli.py)
# ---------------------------------------------------------------------------


def load_known_categorias(raw_dump_path: str | Path) -> set[str]:
    """Categorías específicas (limpias) presentes en un dump crudo ya
    bajado por `ingest` (`data/input/serlaca-raw.json`, gitignored). Si el
    archivo no existe todavía, devuelve un set vacío — `unclassified` queda
    sin poblar en vez de romper la verificación.
    """
    path = Path(raw_dump_path)
    if not path.exists():
        return set()
    dump = json.loads(path.read_text(encoding="utf-8"))
    data_objects = dump.get("dataObjects")
    if not isinstance(data_objects, list):
        return set()
    categorias: set[str] = set()
    for obj in data_objects:
        if not isinstance(obj, dict) or obj.get("professionalExclusive") is True:
            continue
        product_line = obj.get("productLine")
        if isinstance(product_line, dict) and isinstance(product_line.get("name"), str):
            categorias.add(clean_category(product_line["name"]))
    return categorias


def print_report(report: CategoryGroupReport) -> None:
    print(f"Categorías clasificadas: {len(report.categoria_to_groups)}")
    for categoria in sorted(report.categoria_to_groups):
        groups = ", ".join(sorted(report.categoria_to_groups[categoria]))
        print(f"  {categoria!r} -> {groups}")

    if report.conflicts:
        print(
            f"\nℹ {len(report.conflicts)} categoría(s) repartida(s) entre más de un grupo "
            "(esperado — codCategoria es una lista, ver spec 0001):"
        )
        for categoria in report.conflicts:
            print(f"  {categoria!r}: {sorted(report.categoria_to_groups[categoria])}")
    else:
        print("\n✓ Cada categoría cayó en un solo grupo.")

    if report.unclassified:
        print(f"\n⚠ Categorías cargadas hoy sin match en ningún grupo 1/2/3 ({len(report.unclassified)}):")
        for categoria in report.unclassified:
            print(f"  {categoria!r}")

    print("\nCategorías sin repartir (un único grupo, informativo):")
    for categoria, group_id in sorted(report.suggested_map.items()):
        print(f'  "{categoria}": "{group_id}"')


def run(
    env: dict[str, str | None],
    known_categorias_path: str | Path = DEFAULT_RAW_DUMP_PATH,
    report_out_path: str | Path | None = DEFAULT_REPORT_OUT_PATH,
) -> CategoryGroupReport:
    """Corre la verificación completa: red real (Stage 1) + reporte (Stage
    2), imprime el resultado y opcionalmente escribe el JSON crudo del
    reporte en `data/input/` (gitignored, no público) para inspección
    manual. Puramente informativo — el flujo automático que de verdad
    alimenta `codCategoria` es `pipeline.ingest.serlaca_download.run`
    (que reusa `fetch_category_group_samples` en cada corrida de
    `ingest`, no solo acá).
    """
    samples = fetch_category_group_samples(env)
    known_categorias = load_known_categorias(known_categorias_path)
    report = build_category_group_report(samples, known_categorias=known_categorias)
    print_report(report)

    if report_out_path is not None:
        out = Path(report_out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(
                {
                    "categoria_to_groups": {
                        categoria: sorted(groups) for categoria, groups in report.categoria_to_groups.items()
                    },
                    "conflicts": report.conflicts,
                    "unclassified": report.unclassified,
                    "suggested_map": report.suggested_map,
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"\nReporte crudo (gitignored) → {out}")

    return report
