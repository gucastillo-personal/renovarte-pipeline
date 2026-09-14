"""Reporte HTML local de revisión (spec 0008, pt.3 y AC-3).

Página **local, no productiva**: nunca se despliega ni es parte del build
público de Next.js (mismo nivel de confianza que el resto de los scripts de
ingesta — tiene acceso a `precio_profesional`, que es costo). Se escribe a
una ruta gitignored (ver `.gitignore`: `data/private/`).

Es HTML+JS estático sin backend: el selector por fila corre en el
navegador, y el botón "Descargar decisiones" arma
`precio_pdf_decisiones.json` client-side (con `Math.round` sobre el precio
elegido) y lo ofrece para descargar. Aplicar esa descarga al repo es un paso
aparte: `renovarte-pipeline pdf apply-decisions <archivo descargado>`.
"""

import json
from pathlib import Path

from pipeline.transform.pdf_decisions import PdfDecision
from pipeline.transform.pdf_match import MatchResult

_TEMPLATE = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Revisión de precios PDF LACA</title>
<style>
  body { font-family: system-ui, sans-serif; margin: 2rem; color: #1a1a1a; }
  h1 { font-size: 1.25rem; }
  .meta { color: #555; margin-bottom: 1rem; }
  table { border-collapse: collapse; width: 100%; margin-bottom: 2rem; }
  th, td { border: 1px solid #ddd; padding: 0.4rem 0.6rem; text-align: right; font-size: 0.9rem; }
  th:nth-child(1), th:nth-child(2), td:nth-child(1), td:nth-child(2) { text-align: left; }
  th { background: #f4f4f4; }
  .margen-neg { color: #b00020; }
  select { font-size: 0.9rem; }
  .warn-list { color: #7a5b00; }
  #download { font-size: 1rem; padding: 0.5rem 1rem; margin-bottom: 1rem; cursor: pointer; }
</style>
</head>
<body>
<h1>Revisión de precios — PDF de LACA</h1>
<p class="meta" id="meta"></p>
<button id="download">Descargar precio_pdf_decisiones.json</button>
<table id="matched-table">
  <thead>
    <tr>
      <th>Código</th><th>Nombre</th><th>Precio venta actual</th>
      <th>Precio Profesional (costo, contexto)</th>
      <th>Precio ABC</th><th>Margen ABC</th>
      <th>Precio Catálogo</th><th>Margen Catálogo</th>
      <th>Elegir</th>
    </tr>
  </thead>
  <tbody></tbody>
</table>

<h2>Sin dato de PDF (<span id="count-sin-pdf"></span>)</h2>
<ul class="warn-list" id="list-sin-pdf"></ul>

<h2>Filas del PDF sin match en el catálogo (<span id="count-sin-match"></span>)</h2>
<ul class="warn-list" id="list-sin-match"></ul>

<script id="review-data" type="application/json">__DATA_JSON__</script>
<script>
const data = JSON.parse(document.getElementById("review-data").textContent);

document.getElementById("meta").textContent =
  `Fuente: ${data.fuente} — ${data.matched.length} matcheado(s), ` +
  `${data.catalogoSinPdf.length} sin dato de PDF, ${data.pdfSinMatch.length} sin match en catálogo.`;

const fmt = (n) => (n === null ? "—" : new Intl.NumberFormat("es-AR").format(Math.round(n)));
const pct = (n) => (n === null ? "—" : `${n.toFixed(1)}%`);
const ESCAPES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
const esc = (s) => s.replace(/[&<>"']/g, (c) => ESCAPES[c]);

const tbody = document.querySelector("#matched-table tbody");
for (const row of data.matched) {
  const tr = document.createElement("tr");
  const existing = data.existingDecisions[row.codigo];
  const negClass = (n) => (n !== null && n < 0 ? "margen-neg" : "");
  const priceFor = { abc: row.precioAbc, catalogo: row.precioCatalogo, actual: row.precioVentaActual };
  const fallbackOrder = ["abc", "catalogo", "actual"];
  const defaultFuente =
    existing && priceFor[existing.fuente] !== null && priceFor[existing.fuente] !== undefined
      ? existing.fuente
      : fallbackOrder.find((f) => priceFor[f] !== null);

  tr.innerHTML = `
    <td>${esc(row.codigo)}</td>
    <td>${esc(row.nombre)}</td>
    <td>${fmt(row.precioVentaActual)}</td>
    <td>${fmt(row.precioProfesional)}</td>
    <td>${fmt(row.precioAbc)}</td>
    <td class="${negClass(row.margenAbcPct)}">${pct(row.margenAbcPct)}</td>
    <td>${fmt(row.precioCatalogo)}</td>
    <td class="${negClass(row.margenCatalogoPct)}">${pct(row.margenCatalogoPct)}</td>
    <td>
      <select data-codigo="${row.codigo}">
        <option value="abc" ${row.precioAbc === null ? "disabled" : ""}>
          ABC (${fmt(row.precioAbc)})
        </option>
        <option value="catalogo" ${row.precioCatalogo === null ? "disabled" : ""}>
          Catálogo (${fmt(row.precioCatalogo)})
        </option>
        <option value="actual">Actual (${fmt(row.precioVentaActual)})</option>
      </select>
    </td>`;
  tr.querySelector("select").value = defaultFuente;
  tbody.appendChild(tr);
}

document.getElementById("count-sin-pdf").textContent = data.catalogoSinPdf.length;
document.getElementById("list-sin-pdf").innerHTML = data.catalogoSinPdf
  .map((p) => `<li>${esc(p.codigo)} — ${esc(p.nombre)}</li>`)
  .join("");

document.getElementById("count-sin-match").textContent = data.pdfSinMatch.length;
document.getElementById("list-sin-match").innerHTML = data.pdfSinMatch
  .map((p) => `<li>${esc(p.codigo)} — ${esc(p.nombrePdf)}</li>`)
  .join("");

document.getElementById("download").addEventListener("click", () => {
  const decisions = {};
  for (const row of data.matched) {
    const fuente = document.querySelector(`select[data-codigo="${row.codigo}"]`).value;
    const valor =
      fuente === "abc" ? row.precioAbc : fuente === "catalogo" ? row.precioCatalogo : row.precioVentaActual;
    decisions[row.codigo] = { fuente, valor: Math.round(valor) };
  }
  // Carry over decisions for codes not in this review, so re-downloading doesn't drop them.
  for (const [codigo, decision] of Object.entries(data.existingDecisions)) {
    if (!(codigo in decisions)) decisions[codigo] = decision;
  }
  const ordered = {};
  for (const codigo of Object.keys(decisions).sort()) ordered[codigo] = decisions[codigo];

  const blob = new Blob([JSON.stringify(ordered, null, 2) + "\\n"], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "precio_pdf_decisiones.json";
  a.click();
});
</script>
</body>
</html>
"""


def render_review_html(
    match: MatchResult,
    fuente: str,
    existing_decisions: dict[str, PdfDecision] | None = None,
) -> str:
    existing_decisions = existing_decisions or {}
    payload = {
        "fuente": fuente,
        "existingDecisions": {
            codigo: {"fuente": decision.fuente, "valor": decision.valor}
            for codigo, decision in existing_decisions.items()
        },
        "matched": [
            {
                "codigo": row.codigo,
                "nombre": row.nombre,
                "precioVentaActual": row.precio_venta_actual,
                "precioProfesional": row.precio_profesional,
                "precioAbc": row.precio_abc,
                "precioCatalogo": row.precio_catalogo,
                "margenAbcPct": row.margen_abc_pct,
                "margenCatalogoPct": row.margen_catalogo_pct,
            }
            for row in match.matched
        ],
        "catalogoSinPdf": [{"codigo": p.id, "nombre": p.nombre} for p in match.catalogo_sin_pdf],
        "pdfSinMatch": [{"codigo": r.codigo, "nombrePdf": r.nombre_pdf} for r in match.pdf_sin_match],
    }
    # </script> can't appear literally inside a script body.
    data_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return _TEMPLATE.replace("__DATA_JSON__", data_json)


def write_review_html(
    match: MatchResult,
    fuente: str,
    path: str | Path,
    existing_decisions: dict[str, PdfDecision] | None = None,
) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_review_html(match, fuente, existing_decisions), encoding="utf-8")
    return out
