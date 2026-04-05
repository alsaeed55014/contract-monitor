"""
Verification script for enhanced compound Arabic search.
Tests TranslationManager.analyze_query() and SmartSearchEngine.search()
with a variety of Arabic queries.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from src.core.translation import TranslationManager
from src.core.search import SmartSearchEngine


def test_translation():
    print("=" * 60)
    print("TEST 1: TranslationManager.analyze_query()")
    print("=" * 60)
    
    tm = TranslationManager()
    
    test_cases = [
        # (query, description, expected_bundle_count)
        ("شيف", "Single job - Chef", 1),
        ("باريستا", "Single job - Barista", 1),
        ("فلبيني", "Single nationality - Filipino", 1),
        ("ذكر", "Single gender - Male", 1),
        ("نظافة", "Single job - Cleaner", 1),
        ("عامل نظافة", "Multi-word phrase - Cleaner", 1),
        ("عاملة منزلية", "Multi-word phrase - Housemaid", 1),
        ("بدكير منكير", "Multi-word phrase - Pedicure Manicure", 1),
        ("صالون نسائي", "Multi-word phrase - Ladies Salon", 1),
        ("صالون", "Single word - Salon", 1),
        ("باريستا فلبيني ذكر", "Compound: Barista + Filipino + Male", 3),
        ("خادمة فلبينية", "Compound: Housemaid + Filipino", 2),
        ("افريقي", "African trigger - should expand to all nationalities", 1),
        ("باريستا افريقي", "Compound: Barista + African (OR group)", 2),
        ("خادمة افريقية", "Compound: Housemaid + African (OR group)", 2),
        ("+966 59 422 3552", "Phone number with spaces (not analyzed)", None),
    ]
    
    passed = 0
    failed = 0
    
    for query, desc, expected_bundles in test_cases:
        bundles = tm.analyze_query(query)
        status = ""
        
        if expected_bundles is not None:
            if len(bundles) == expected_bundles:
                status = "PASS"
                passed += 1
            else:
                status = f"FAIL (expected {expected_bundles} bundles, got {len(bundles)})"
                failed += 1
        else:
            status = "SKIP (phone query)"
            passed += 1
        
        print(f"\n[{status}] {desc}")
        print(f"  Query: '{query}'")
        print(f"  Bundles ({len(bundles)}): {bundles}")
        
        # Check African expansion
        if "افريق" in query or "أفريق" in query:
            for b in bundles:
                if any("nigerian" in s.lower() or "kenyan" in s.lower() for s in b):
                    print(f"  African expansion: {len(b)} nationalities in OR bundle")
    
    print(f"\n{'='*40}")
    print(f"Translation Tests: {passed} passed, {failed} failed")
    return failed == 0


def test_search_engine():
    print("\n" + "=" * 60)
    print("TEST 2: SmartSearchEngine.search()")
    print("=" * 60)
    
    # Create test data
    test_data = pd.DataFrame({
        '__sheet_row': [2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
        'Full Name:': ['Ahmad', 'Maria', 'John', 'Fatima', 'Ali', 'Jane', 'Omar', 'Rosa', 'Hassan', 'Lina'],
        'Nationality': ['Saudi', 'Filipino', 'American', 'Ethiopian', 'Saudi', 'Kenyan', 'Saudi', 'Filipino', 'Pakistani', 'Nigerian'],
        'Gender': ['Male', 'Female', 'Male', 'Female', 'Male', 'Female', 'Male', 'Female', 'Male', 'Female'],
        'Phone Number': ['0501234567', '0594223552', '0551112222', '0559998888', '0507777777', '0508888888', '0509999999', '0501010101', '0502020202', '0503030303'],
        'Which job are you looking for': ['Driver', 'Barista', 'Chef', 'Housemaid', 'Cleaner', 'Salon', 'Driver', 'Barista', 'Cook', 'Housemaid'],
        '__sheet_row_backup': [2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
    })

    eng = SmartSearchEngine(test_data)
    
    test_cases = [
        # (query, description, expected_count, expected_names)
        ("شيف", "Chef search", 1, ["John"]),
        ("chef", "Chef in English", 1, ["John"]),
        ("باريستا", "Barista search", 2, ["Maria", "Rosa"]),
        ("فلبيني", "Filipino search", 2, ["Maria", "Rosa"]),
        ("باريستا فلبيني", "Filipino Barista (AND)", 2, ["Maria", "Rosa"]),
        ("ذكر", "Male search", 5, None),
        ("انثى", "Female search", 5, None),
        ("افريقي", "African (OR group)", 3, ["Fatima", "Jane", "Lina"]),
        ("خادمة افريقية", "African Housemaid", 2, ["Fatima", "Lina"]),
        ("+966 59 422 3552", "Phone with spaces", 1, ["Maria"]),
        ("0594223552", "Phone without spaces", 1, ["Maria"]),
        ("Ahmad", "Name search", 1, ["Ahmad"]),
        ("", "Empty query", 10, None),
        ("Driver", "English job", 2, ["Ahmad", "Omar"]),
    ]
    
    passed = 0
    failed = 0
    
    for query, desc, expected_count, expected_names in test_cases:
        res = eng.search(query)
        actual_count = len(res)
        actual_names = res['Full Name:'].tolist() if not res.empty else []
        
        count_ok = (actual_count == expected_count)
        names_ok = True
        if expected_names is not None:
            names_ok = set(expected_names) == set(actual_names)
        
        if count_ok and names_ok:
            status = "PASS"
            passed += 1
        else:
            status = "FAIL"
            failed += 1
        
        print(f"\n[{status}] {desc}")
        print(f"  Query: '{query}'")
        print(f"  Expected: {expected_count} rows", end="")
        if expected_names:
            print(f" {expected_names}", end="")
        print()
        print(f"  Got:      {actual_count} rows {actual_names}")
        if not count_ok:
            print(f"  >>> COUNT MISMATCH!")
        if not names_ok:
            print(f"  >>> NAMES MISMATCH!")
        
        # Show debug info
        debug = eng.last_debug
        if debug.get('bundles'):
            print(f"  Bundles: {debug['bundles']}")

    print(f"\n{'='*40}")
    print(f"Search Tests: {passed} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    t_ok = test_translation()
    s_ok = test_search_engine()
    
    print("\n" + "=" * 60)
    if t_ok and s_ok:
        print("ALL TESTS PASSED!")
    else:
        print("SOME TESTS FAILED - review output above")
    print("=" * 60)
