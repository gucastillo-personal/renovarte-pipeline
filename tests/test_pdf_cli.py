import argparse
import json
from pathlib import Path

from pipeline.pdf_cli import cmd_pdf_apply_decisions


def _args(file: str, out: str) -> argparse.Namespace:
    return argparse.Namespace(file=file, out=out)


def test_apply_decisions_missing_file_errors_without_touching_out(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    out = tmp_path / "precio_pdf_decisiones.json"
    out.write_text('{"001": {"fuente": "abc", "valor": 1300}}\n', encoding="utf-8")

    exit_code = cmd_pdf_apply_decisions(_args(str(tmp_path / "no-existe.json"), str(out)))

    assert exit_code == 1
    assert "no existe" in capsys.readouterr().err
    # A bad --file must never overwrite real, already-applied decisions.
    assert json.loads(out.read_text(encoding="utf-8"))["001"]["valor"] == 1300


def test_apply_decisions_expands_tilde(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("HOME", str(tmp_path))
    downloads = tmp_path / "Downloads"
    downloads.mkdir()
    (downloads / "precio_pdf_decisiones.json").write_text(
        '{"001": {"fuente": "catalogo", "valor": 1500}}\n', encoding="utf-8"
    )
    out = tmp_path / "out.json"

    exit_code = cmd_pdf_apply_decisions(_args("~/Downloads/precio_pdf_decisiones.json", str(out)))

    assert exit_code == 0
    assert json.loads(out.read_text(encoding="utf-8"))["001"]["valor"] == 1500
