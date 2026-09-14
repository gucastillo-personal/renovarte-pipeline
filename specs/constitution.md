# Constitution — RenovArte Pipeline

Non-negotiable principles for this project. Every spec, plan, PR and review is
checked against this file. Amending it requires a note in the PR description
explaining why.

Source of truth: [`renovarte-parent/PLAN.md`](../../PLAN.md) (arquitectura de
la separación catálogo/pipeline) and
[RFC-0001 §2.4 de `renovarte-catalogo`](https://github.com/gucastillo-personal/renovarte-catalogo/blob/main/docs/rfc/0001-arquitectura-catalogo.md)
(schema público que este repo produce).

Mirror de [`renovarte-catalogo/specs/constitution.md`](https://github.com/gucastillo-personal/renovarte-catalogo/blob/main/specs/constitution.md)
del lado de la ingesta — este repo es responsable de la mitad "origen" de las
mismas invariantes de seguridad.

---

## I. Security invariants (business-critical)

1. **No cost, no margin, no LACA list price in anything public.** El costo
   real de compra (`precio_profesional` / `costo`), el margen aplicado, y el
   precio de lista de LACA nunca aparecen en `public/`, en
   `data/reference/*` público, ni cruzan a `renovarte-catalogo` salvo ya
   convertidos en `precio_venta` (y, en oferta, `precio_regular`/`descuento_pct`).
2. **Datos crudos y credenciales nunca se commitean.** `data/raw/`,
   `data/input/`, `.env`/`.env.local` están gitignored — contienen costo real
   y credenciales de Serlaca/LACA.
3. **`public/data/products.json` solo se publica vía Pull Request** a
   `renovarte-catalogo`, nunca push directo a su `main`. El merge queda a
   revisión humana — nunca auto-merge.
4. **Leak check antes de publicar.** `pipeline/publish/leak_check.py` corre
   antes de abrir el PR (defensa en origen) — espeja `check-leak.mjs` de
   `renovarte-catalogo` (defensa en destino). Un `publish --live` sin
   leak-check verde no es "done".
5. **El `CATALOGO_PAT` (o equivalente) está scoped solo a `renovarte-catalogo`,
   nunca "todos los repos".** Nunca se pega ni se loguea el token.

## II. Architecture

6. **`ingest`, `transform` y `pdf-extract` son siempre manuales**, corridos
   por el admin en su máquina. La GitHub Action de este repo corre
   únicamente `publish` (cron + `workflow_dispatch`) — nunca genera datos.
7. **Salida = schema público exacto (RFC-0001 §2.4 de `renovarte-catalogo`).**
   Claves en español (`proveedor, categoria, nombre, presentacion,
   descripcion, precio_venta, imagen, en_oferta, tags`, más los opcionales
   de oferta `precio_regular`/`descuento_pct`). Agregar una clave requiere
   enmendar el RFC **en ambos repos**.
8. **Multi-fuente por diseño, single-source activo.** El campo `proveedor`
   existe desde el día uno; hoy solo LACA/Serlaca están cargados. Una fuente
   nueva es un adaptador nuevo bajo `pipeline/sources/`, no un cambio al
   modelo público.
9. **$0 infraestructura.** Solo free tier de GitHub Actions; sin backend ni
   base de datos propios.
10. **Determinístico.** Correr `transform` dos veces sobre el mismo input
    produce el mismo `products.json` byte a byte (orden de claves estable).

## III. Code quality

11. **Python 3.13 + `uv`.** `ruff` (lint), `mypy` (types), `pytest` (tests) —
    los tres tienen que estar verdes antes de decir que algo está "done"
    (`make check`).
12. **Pydantic para todo modelo de datos cruzando un límite** (fuente
    externa → `CostRow` interno, `CostRow` → `Product` público) — no dicts
    sueltos pasando por la lógica de negocio.
13. **Tests gatean features.** Cada módulo nuevo porta o suma su cobertura de
    test antes de mergear (ver el precedente de la migración 1:1 desde
    `renovarte-catalogo`: 0009 sola migró con 98 tests).

## IV. Spec-Driven Development workflow

14. **Spec before code.** No se escribe código de feature antes de que su
    `spec.md` (acceptance criteria citando IDs `RF-0x`/`RNF-0x`) y `tasks.md`
    existan y estén aprobados.
15. **Traceability.** [`specs/README.md`](./README.md) mantiene la matriz
    requirement → spec → status.
16. **Tareas chicas, ordenadas, verificables.** Cada ítem de `tasks.md`
    termina en un resultado chequeable (build pasa, un test nombrado pasa a
    verde, una corrida real produce el output esperado).
17. **Done significa demostrado.** Una feature está lista solo cuando todas
    sus tareas están tildadas y sus acceptance criteria fueron mostrados
    cumplidos — no autoreportado, verificado.
