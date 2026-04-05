#!/usr/bin/env python3
"""
Phase 0 Test: Data Foundation
Validates that all Phase 0 requirements are met
"""

import os
import sqlite3
import json
from pathlib import Path

def test_phase0():
    print("=== Phase 0 Test: Data Foundation ===")
    
    # Change to project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: data/INDB.xlsx exists
    tests_total += 1
    print("\n1. Testing data/INDB.xlsx exists...")
    if Path("data/INDB.xlsx").exists():
        print("✅ data/INDB.xlsx exists")
        tests_passed += 1
    else:
        print("❌ data/INDB.xlsx does not exist")
    
    # Test 2: data/nutrition.db exists
    tests_total += 1
    print("\n2. Testing data/nutrition.db exists...")
    if Path("data/nutrition.db").exists():
        print("✅ data/nutrition.db exists")
        tests_passed += 1
    else:
        print("❌ data/nutrition.db does not exist")
    
    # Test 3: nutrition.db has table indb_recipes with > 0 rows
    tests_total += 1
    print("\n3. Testing indb_recipes table exists and has data...")
    try:
        conn = sqlite3.connect("data/nutrition.db", check_same_thread=False)
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='indb_recipes'")
        table_exists = cursor.fetchone() is not None
        
        if table_exists:
            # Check row count
            cursor.execute("SELECT COUNT(*) FROM indb_recipes")
            row_count = cursor.fetchone()[0]
            
            if row_count > 0:
                print(f"✅ indb_recipes table exists with {row_count} rows")
                tests_passed += 1
            else:
                print("❌ indb_recipes table exists but has 0 rows")
        else:
            print("❌ indb_recipes table does not exist")
        
        conn.close()
    except Exception as e:
        print(f"❌ Error checking database: {e}")
    
    # Test 4: indb_recipes has correct columns
    tests_total += 1
    print("\n4. Testing indb_recipes table schema...")
    try:
        conn = sqlite3.connect("data/nutrition.db", check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(indb_recipes)")
        columns = [row[1] for row in cursor.fetchall()]
        
        expected_columns = ['id', 'name', 'calories', 'protein_g', 'carbs_g', 'fat_g']
        missing_columns = [col for col in expected_columns if col not in columns]
        
        if not missing_columns:
            print(f"✅ indb_recipes has correct columns: {columns}")
            tests_passed += 1
        else:
            print(f"❌ indb_recipes missing columns: {missing_columns}")
            print(f"   Found columns: {columns}")
        
        conn.close()
    except Exception as e:
        print(f"❌ Error checking table schema: {e}")
    
    # Test 5: nutrition.db does NOT have ifct_ingredients table
    tests_total += 1
    print("\n5. Testing ifct_ingredients table does NOT exist...")
    try:
        conn = sqlite3.connect("data/nutrition.db", check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ifct_ingredients'")
        ifct_table_exists = cursor.fetchone() is not None
        
        if not ifct_table_exists:
            print("✅ ifct_ingredients table correctly does NOT exist")
            tests_passed += 1
        else:
            print("❌ ifct_ingredients table exists (should NOT exist)")
        
        conn.close()
    except Exception as e:
        print(f"❌ Error checking for ifct_ingredients table: {e}")
    
    # Test 6: No food_label_map.json exists anywhere in the repo
    tests_total += 1
    print("\n6. Testing food_label_map.json does NOT exist...")
    food_label_map_files = list(Path(".").rglob("food_label_map.json"))
    
    if not food_label_map_files:
        print("✅ food_label_map.json correctly does NOT exist")
        tests_passed += 1
    else:
        print(f"❌ food_label_map.json found at: {food_label_map_files}")
    
    # Test 7: models/ folder exists
    tests_total += 1
    print("\n7. Testing models/ folder exists...")
    if Path("models").exists() and Path("models").is_dir():
        print("✅ models/ folder exists")
        tests_passed += 1
    else:
        print("❌ models/ folder does not exist")
    
    # Summary
    print(f"\n=== Phase 0 Test Summary ===")
    print(f"Tests passed: {tests_passed}/{tests_total}")
    
    if tests_passed == tests_total:
        print("🎉 All Phase 0 tests PASSED!")
        return True
    else:
        print("❌ Some Phase 0 tests FAILED!")
        return False

if __name__ == "__main__":
    success = test_phase0()
    exit(0 if success else 1)
