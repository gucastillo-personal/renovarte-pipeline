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
| — | (ninguna feature todavía — este repo recién suma su propio spec-kit) | — |

## Traceability matrix (PRD requirement → spec → status)

| Requirement | Summary | Spec(s) | Status |
|-------------|---------|---------|--------|
| — | Se completa cuando exista un PRD en `docs/PRD/` con IDs `RF-`/`RNF-` | — | — |
