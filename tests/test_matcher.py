import pandas as pd

from src.core.matcher import (
    CandidateMatcher,
    _find_city_region,
    _fuzzy_match,
    _normalize,
    _resolve_region,
    format_match_result,
)


def test_matching_helpers_normalize_translate_and_resolve_locations():
    assert _normalize("  الإقامة  ") == "اقامه"
    assert _fuzzy_match("Barista", "باريستا") is True
    assert _fuzzy_match("Waiter", "باريستا") is False
    assert _find_city_region("Riyadh") == "الوسطى"
    assert _find_city_region("Unknown") is None

    is_region, region, cities_ar, cities_en = _resolve_region("Eastern")
    assert is_region is True
    assert region == "الشرقية"
    assert "الدمام" in cities_ar
    assert "dammam" in cities_en


def test_match_finds_local_and_nearby_candidates():
    candidates = pd.DataFrame(
        [
            {
                "Name": "Local",
                "Nationality": "Filipino",
                "Gender": "Female",
                "City": "Riyadh",
                "Job": "Barista",
            },
            {
                "Name": "Nearby",
                "Nationality": "Filipino",
                "Gender": "Female",
                "City": "Al Kharj",
                "Job": "Barista",
            },
            {
                "Name": "Wrong job",
                "Nationality": "Filipino",
                "Gender": "Female",
                "City": "Riyadh",
                "Job": "Driver",
            },
        ]
    )
    matcher = CandidateMatcher(candidates)

    result = matcher.match(
        {
            "Required nationality": "Filipino",
            "Specify the required category": "Female",
            "Work location": "Riyadh",
            "Nature of the worker's work": "Barista",
        }
    )

    assert result["status"] == "found_local"
    assert result["local_results"]["Name"].tolist() == ["Local"]
    assert result["expanded_results"][0]["city"] == "الخرج"
    assert result["expanded_results"][0]["candidates"]["Name"].tolist() == ["Nearby"]


def test_match_returns_not_found_when_basic_requirements_fail():
    candidates = pd.DataFrame(
        [
            {
                "Name": "Candidate",
                "Nationality": "Indian",
                "Gender": "Male",
                "City": "Riyadh",
                "Job": "Driver",
            }
        ]
    )

    result = CandidateMatcher(candidates).match(
        {
            "Required nationality": "Filipino",
            "Specify the required category": "Female",
            "Work location": "Riyadh",
            "Nature of the worker's work": "Barista",
        }
    )

    assert result["status"] == "not_found"
    assert result["local_results"].empty
    assert result["expanded_results"] == []


def test_format_match_result_for_not_found_result():
    result = {
        "criteria": {
            "nationality": "Filipino",
            "gender": "Female",
            "location": "Riyadh",
            "job": "Barista",
        },
        "geo_scope": {
            "original_location": "Riyadh",
            "is_region": False,
        },
        "status": "not_found",
    }

    summary, status, alternatives, candidates = format_match_result(
        result, lang="en"
    )

    assert "Filipino" in summary
    assert "No candidates" in status
    assert alternatives == ""
    assert candidates.empty
