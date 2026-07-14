import pandas as pd

from src.utils import data_utils


def test_get_flag_emoji_supports_arabic_english_and_unknown_values():
    assert data_utils.get_flag_emoji("عامل مصري") == "🇪🇬"
    assert data_utils.get_flag_emoji("Kenya") == "🇰🇪"
    assert data_utils.get_flag_emoji("Unknown") == "🏁"


def test_auto_translate_skips_when_ui_language_does_not_match(monkeypatch):
    monkeypatch.setattr(data_utils.st, "session_state", {"lang": "ar"})

    assert data_utils.auto_translate("مرحبا", target_lang="en") == "مرحبا"
    assert data_utils.auto_translate("", target_lang="en") == ""


def test_clean_date_display_only_changes_date_columns():
    frame = pd.DataFrame(
        {
            "Contract End Date": ["2026-07-14 10:30", "invalid"],
            "تاريخ التسجيل": ["٢٠٢٦-٠٧-١٤", None],
            "Name": ["2026-01-01", "Worker"],
        }
    )

    result = data_utils.clean_date_display(frame.copy())

    assert result["Contract End Date"].tolist() == ["2026-07-14", "invalid"]
    assert result["تاريخ التسجيل"].tolist() == ["2026-07-14", ""]
    assert result["Name"].tolist() == ["2026-01-01", "Worker"]


def test_style_df_adds_flag_and_gender_presentation(monkeypatch):
    monkeypatch.setattr(data_utils.st, "session_state", {"lang": "ar"})
    frame = pd.DataFrame(
        {
            "Nationality": ["Indian"],
            "Gender": ["Female"],
            "Score": [5],
        }
    )

    styled = data_utils.style_df(frame)

    assert styled.data["🚩_Nationality"].iloc[0].endswith("/in.svg")
    assert styled.data["Gender"].iloc[0] == "🚺 Female"
    assert frame.columns.tolist() == ["Nationality", "Gender", "Score"]
