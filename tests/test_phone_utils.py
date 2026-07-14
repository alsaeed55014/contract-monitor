import pandas as pd
import pytest

from src.utils.phone_utils import (
    create_pasha_whatsapp_excel,
    format_phone_number,
    mask_phone,
    normalize_ar,
    validate_numbers,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, None),
        ("", None),
        ("abc", None),
        ("+966 50 123 4567", "+966501234567"),
        ("0501234567", "+966501234567"),
        ("501234567", "+966501234567"),
        ("03001234567", "+923001234567"),
        ("9123456789", "+919123456789"),
        ("0712345678", "+962712345678"),
        ("51234567", "+96551234567"),
        ("12345678901", "+12345678901"),
        ("12345", None),
    ],
)
def test_format_phone_number(raw, expected):
    assert format_phone_number(raw) == expected


def test_validate_numbers_tracks_valid_and_invalid_entries():
    valid, invalid_count, total_count = validate_numbers(
        "0501234567, invalid; +966501111111"
    )

    assert valid == ["+966501234567", "+966501111111"]
    assert invalid_count == 1
    assert total_count == 3


def test_validate_numbers_handles_empty_input():
    assert validate_numbers("") == ([], 0, 0)


def test_arabic_normalization_and_phone_masking():
    assert normalize_ar("  أإآةى  ") == "اااهي"
    assert normalize_ar(123) == ""
    assert mask_phone("+96650") == "******"
    assert mask_phone("---") == "---"
    assert mask_phone("") == "---"


def test_create_whatsapp_excel_filters_invalid_rows_and_hidden_columns():
    candidates = pd.DataFrame(
        [
            {
                "Candidate Name": "A",
                "Mobile Number": "0501234567",
                "__sheet_row": 2,
            },
            {
                "Candidate Name": "B",
                "Mobile Number": "invalid",
                "__sheet_row": 3,
            },
        ]
    )

    workbook, exported = create_pasha_whatsapp_excel(candidates, lang="en")

    assert workbook.getbuffer().nbytes > 0
    assert exported.to_dict("records") == [
        {"Candidate Name": "A", "Mobile Number": "+966501234567"}
    ]


def test_create_whatsapp_excel_returns_none_without_exportable_rows():
    assert create_pasha_whatsapp_excel(pd.DataFrame(), lang="en") is None
    invalid = pd.DataFrame([{"Candidate Name": "A", "Mobile Number": "invalid"}])
    assert create_pasha_whatsapp_excel(invalid, lang="en") is None
