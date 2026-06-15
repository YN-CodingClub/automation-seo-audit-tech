from __future__ import annotations

import math

import pandas as pd
import pytest

from audit_engine import (
    load_screaming_frog_csv,
    parse_locale_number,
    resolve_columns,
)


def test_load_screaming_frog_csv_detects_header_row_delimiter_and_drops_empty_columns(
    uploaded_bytes_factory,
) -> None:
    uploaded = uploaded_bytes_factory(
        "Export Screaming Frog\n"
        "Generated for tests\n"
        "Adresse;Code HTTP;Title 1;Empty\n"
        "https://example.com/a;200;Homepage;\n"
        "https://example.com/b;404;Missing;\n"
    )

    df = load_screaming_frog_csv(uploaded)

    assert list(df.columns) == ["Adresse", "Code HTTP", "Title 1"]
    assert df.shape == (2, 3)
    assert df.loc[0, "Adresse"] == "https://example.com/a"


def test_load_screaming_frog_csv_rejects_empty_upload(uploaded_bytes_factory) -> None:
    with pytest.raises(ValueError, match="Le fichier CSV est vide"):
        load_screaming_frog_csv(uploaded_bytes_factory(""))


def test_resolve_columns_accepts_french_and_english_aliases() -> None:
    df = pd.DataFrame(
        columns=[
            "Adresse",
            "Status Code",
            "Indexabilité",
            "Canonical Link Element 1",
        ]
    )

    resolved = resolve_columns(df)

    assert resolved["url"] == "Adresse"
    assert resolved["status_code"] == "Status Code"
    assert resolved["indexability"] == "Indexabilité"
    assert resolved["canonical_1"] == "Canonical Link Element 1"


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("1,23", 1.23),
        ("1 234,5%", 1234.5),
        ("1\xa0234,5", 1234.5),
    ],
)
def test_parse_locale_number_handles_french_formats(raw_value: str, expected: float) -> None:
    assert parse_locale_number(raw_value) == expected


@pytest.mark.parametrize("raw_value", ["n/a", "abc", "", None])
def test_parse_locale_number_returns_nan_for_empty_or_non_numeric_values(raw_value) -> None:
    assert math.isnan(parse_locale_number(raw_value))
