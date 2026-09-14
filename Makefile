# renovarte-pipeline — atajos para los comandos más usados.
# `make help` lista los targets.

RAW_DIR := data/raw
CATALOG ?= ../renovarte-catalogo/public/data/products.json
REVIEW_HTML := data/private/pdf_review.html

# Si no pasaste PDF=... y hay exactamente un .pdf en data/raw/, se usa ese.
# Si hay más de uno, queda vacío a propósito — _require-pdf-args corta con
# la lista de candidatos en vez de adivinar cuál procesar.
PDF_CANDIDATES := $(wildcard $(RAW_DIR)/*.pdf)
ifndef PDF
ifeq ($(words $(PDF_CANDIDATES)),1)
PDF := $(PDF_CANDIDATES)
endif
endif

# Fuente por defecto derivada del nombre de archivo (ej. "Septiembre.pdf" ->
# "LACA Septiembre"). Sobreescribible: FUENTE="LACA Septiembre 2026".
FUENTE ?= LACA $(basename $(notdir $(PDF)))

.PHONY: help install test lint typecheck check ingest transform publish publish-live \
        pdf-extract pdf-review pdf-workflow pdf-apply-decisions _require-pdf-args _require-catalogo-checkout

help:
	@echo "renovarte-pipeline — targets disponibles:"
	@echo ""
	@echo "  make install                            uv sync"
	@echo "  make check                               lint + typecheck + test"
	@echo "  make ingest                              etapa 1: descarga cruda de Serlaca"
	@echo "  make transform                           etapa 2: crudo -> products.json"
	@echo ""
	@echo "  make pdf-extract [PDF=...] [FUENTE=...]  extrae el PDF de LACA (spec 0008)"
	@echo "  make pdf-review  [PDF=...] [FUENTE=...] [CATALOG=...]"
	@echo "                                            genera el reporte y lo abre en el navegador"
	@echo "  make pdf-workflow [PDF=...] [FUENTE=...] extract + review en un solo paso"
	@echo "  make pdf-apply-decisions FILE=...        aplica el JSON descargado del reporte"
	@echo ""
	@echo "  make publish CATALOGO_CHECKOUT=<clon dedicado>       dry-run: prepara la rama, no pushea"
	@echo "  make publish-live CATALOGO_CHECKOUT=<clon dedicado>  pushea y abre el PR de verdad"
	@echo ""
	@echo "  PDF y FUENTE son opcionales si hay un solo .pdf en $(RAW_DIR)/."
	@echo "  CATALOG por defecto: $(CATALOG)"
	@echo "  CATALOGO_CHECKOUT: SIEMPRE un clon descartable, NUNCA tu carpeta"
	@echo "  de trabajo de renovarte-catalogo — publish le hace reset --hard."

install:
	uv sync

test:
	uv run pytest -q

lint:
	uv run ruff check .

typecheck:
	uv run mypy

check: lint typecheck test

ingest:
	uv run renovarte-pipeline ingest

transform:
	uv run renovarte-pipeline transform

_require-pdf-args:
	@if [ -z "$(PDF)" ]; then \
		echo "✗ Especificá PDF=<ruta> — PDF(s) encontrado(s) en $(RAW_DIR)/:"; \
		ls $(RAW_DIR)/*.pdf 2>/dev/null | sed 's/^/    /' || echo "    (ninguno)"; \
		exit 1; \
	fi
	@if [ ! -f "$(PDF)" ]; then \
		echo "✗ No existe: $(PDF)"; \
		exit 1; \
	fi

pdf-extract: _require-pdf-args
	uv run renovarte-pipeline pdf extract --pdf "$(PDF)" --fuente "$(FUENTE)"

pdf-review: _require-pdf-args
	uv run renovarte-pipeline pdf review --pdf "$(PDF)" --fuente "$(FUENTE)" --catalog "$(CATALOG)"
	@open "$(REVIEW_HTML)" 2>/dev/null || xdg-open "$(REVIEW_HTML)" 2>/dev/null \
		|| echo "  (no pude abrirlo solo — abrí $(REVIEW_HTML) a mano)"

pdf-workflow: pdf-extract pdf-review

pdf-apply-decisions:
	@if [ -z "$(FILE)" ]; then \
		echo '✗ Especificá FILE=<precio_pdf_decisiones.json descargado>, ej:'; \
		echo '    make pdf-apply-decisions FILE=~/Downloads/precio_pdf_decisiones.json'; \
		exit 1; \
	fi
	uv run renovarte-pipeline pdf apply-decisions "$(FILE)"

_require-catalogo-checkout:
	@if [ -z "$(CATALOGO_CHECKOUT)" ]; then \
		echo '✗ Especificá CATALOGO_CHECKOUT=<clon dedicado de renovarte-catalogo>.'; \
		echo '  Tiene que ser un clon DESCARTABLE (publish le hace reset --hard),'; \
		echo '  nunca tu carpeta de trabajo real. Ej.: git clone <url> /tmp/catalogo-publish'; \
		exit 1; \
	fi

publish: _require-catalogo-checkout
	uv run renovarte-pipeline publish --catalogo "$(CATALOGO_CHECKOUT)"

publish-live: _require-catalogo-checkout
	uv run renovarte-pipeline publish --catalogo "$(CATALOGO_CHECKOUT)" --live
