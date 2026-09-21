# Specs — Spec-Driven Development

Este folder es la fuente de verdad de *qué* construimos y *por qué*, antes del
código. Convención liviana, sin CLI externa — espeja la de
[`renovarte-catalogo/specs/`](https://github.com/gucastillo-personal/renovarte-catalogo/tree/main/specs).

## Layout

```
specs/
├── constitution.md          # invariantes no negociables (seguridad, arquitectura, calidad)
├── README.md                # este archivo: workflow + índice + matriz de trazabilidad
└── NNNN-slug/
    ├── spec.md               # QUÉ y POR QUÉ — acceptance criteria citando RF/RNF
    ├── plan.md                # CÓMO — archivos, módulos, forma de datos, cómo se testea
    └── tasks.md               # checkboxes [ ] ordenados, cada uno verificable solo
```

Features en backlog llevan solo `spec.md`; `plan.md` y `tasks.md` se escriben
cuando arranca el trabajo de diseño.

## Workflow

1. **Specify** — `spec.md`: acceptance criteria, cada una citando un
   requirement ID (`RF-0x`/`RNF-0x`) de `docs/PRD/`. Sin detalle de
   implementación.
2. **Plan** — `plan.md`: archivos concretos, módulos reusados, forma de
   datos, cómo se testea cada AC. Chequeado contra
   [`constitution.md`](./constitution.md).
3. **Tasks** — `tasks.md`: pasos chicos y ordenados, cada uno con un
   resultado chequeable. Incluye una sección de estimación (tamaño +
   rango de tiempo + riesgos).
4. **Implement** — se trabajan las tareas de arriba a abajo, tildándolas.
5. **Verify** — se demuestra cada acceptance criterion (test nombrado o paso
   manual explícito). Se actualiza la matriz de abajo a `Done`.

Este flujo lo corren, en `renovarte-parent`, los subagentes `product-agent`
(fases 1-2), `developer-agent` (fases 2-4) y `tester-agent` (fase 5) — ver
`.claude/agents/` y el skill `/feature` ahí.

## Feature index

| ID | Feature | Status |
|----|---------|--------|
| [0001](./0001-agrupacion-alto-nivel-categorias/spec.md) | `codCategoria` (`list[str]`, uno o más ids reales de `productCategoryIds` de Serlaca: `"1"` Cuidado facial / `"2"` Cuidado corporal / `"3"` Cosmética / `"4"` fallback — un producto puede pertenecer a más de un grupo a la vez, ver decisión del CTO/CEO 2026-09-18) en `products.json`, más `data/reference/serlaca_category_groups.json` (mapeo id→nombre, committed acá y también publicado por PR a `renovarte-catalogo` vía `publish`), para que `renovarte-catalogo` ofrezca un filtro de dos niveles | **Built** (18 tests nuevos + 4 archivos de test existentes actualizados, 151 tests totales en verde — `make check` 0). `ingest` real (434 crudos) + `transform` real (384 publicados) + `publish --dry-run` contra un clon descartable, todos corridos de punta a punta 2026-09-18 |

## Traceability matrix (PRD requirement → spec → status)

Ver [`docs/PRD/PRD-pipeline-renovarte.md`](../docs/PRD/PRD-pipeline-renovarte.md)
para el detalle de cada `RF-`/`RNF-` (primer PRD formal de este repo,
2026-09-17 — documenta lo ya construido en la migración más el primer
requisito nuevo).

| Requirement | Summary | Spec(s) | Status |
|-------------|---------|---------|--------|
| RF-01 a RF-08, RNF-01 a RNF-05 | Ingesta, pricing, PDF, ofertas, publicación por PR, leak-check, schema, determinismo — ya construidos en la migración desde `renovarte-catalogo` | — (construidos antes de este spec-kit; sin `spec.md` propio todavía) | Done (en producción) |
| RF-09 | `codCategoria` (`list[str]`, id(s) de grupo de alto nivel real(es) de Serlaca por producto) + JSON de mapeo a nombre de grupo, publicados en `products.json` | 0001 | Done — construido y verificado (AC-1 a AC-7 demostrados, ver `tasks.md`) |
