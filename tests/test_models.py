from pipeline.models import CostRow, Product


def test_cost_row_round_trip() -> None:
    row = CostRow(
        codigo="545300004",
        nombre="Esmalte semipermanente",
        categoria="Uñas",
        presentacion="15ml",
        descripcion="",
        precio_costo=1000.0,
        en_oferta=False,
        tags=[],
        imagen="/img/laca/545300004.svg",
    )
    assert row.codigo == "545300004"
    assert row.precio_costo == 1000.0


def test_product_to_public_dict_omits_absent_offer_fields() -> None:
    product = Product(
        id="545300004",
        proveedor="LACA",
        categoria="Uñas",
        nombre="Esmalte semipermanente",
        presentacion="15ml",
        descripcion="",
        precio_venta=1200,
        imagen="/img/laca/545300004.svg",
        en_oferta=False,
        tags=[],
    )
    public = product.to_public_dict()
    assert "precio_regular" not in public
    assert "descuento_pct" not in public
    assert "precio_costo" not in public  # never part of Product at all


def test_product_keeps_offer_fields_when_present() -> None:
    product = Product(
        id="545300004",
        proveedor="LACA",
        categoria="Uñas",
        nombre="Esmalte semipermanente",
        presentacion="15ml",
        descripcion="",
        precio_venta=1080,
        imagen="/img/laca/545300004.svg",
        en_oferta=True,
        tags=[],
        precio_regular=1200,
        descuento_pct=10,
    )
    public = product.to_public_dict()
    assert public["precio_regular"] == 1200
    assert public["descuento_pct"] == 10
