#!/usr/bin/env python3
"""
Phase 0 Test Suite - Data Foundation Validation
Verifies all required files exist and data is properly structured
"""

import os
import json
import sqlite3
from pathlib import Path

def test_file_exists(file_path, description):
    """Test if a file exists"""
    if file_path.exists():
        print(f"✅ PASS: {description}")
        return True
    else:
        print(f"❌ FAIL: {description} - File not found: {file_path}")
        return False

def test_directory_exists(dir_path, description):
    """Test if a directory exists"""
    if dir_path.exists() and dir_path.is_dir():
        print(f"✅ PASS: {description}")
        return True
    else:
        print(f"❌ FAIL: {description} - Directory not found: {dir_path}")
        return False

def test_food_label_map():
    """Test food_label_map.json structure and content"""
    print("\n=== Testing food_label_map.json ===")
    
    project_root = Path(__file__).parent.parent
    json_path = project_root / "data" / "food_label_map.json"
    
    if not test_file_exists(json_path, "food_label_map.json exists"):
        return False
    
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        # Check it's a dictionary
        if not isinstance(data, dict):
            print(f"❌ FAIL: food_label_map.json is not a dictionary")
            return False
        
        # Check required entries (30 Indian foods)
        required_foods = [
            "biryani", "butter_chicken", "chapati", "chole_bhature", "dal_makhani", "dal_tadka",
            "dosa", "gulab_jamun", "idli", "jalebi", "kadai_paneer", "kathi_roll", "kheer", "kulfi",
            "masala_dosa", "medu_vada", "naan", "pakoda", "palak_paneer", "paneer_butter_masala",
            "pav_bhaji", "poha", "puri", "rasgulla", "ras_malai", "samosa", "shahi_paneer",
            "uttapam", "vada_pav", "momos"
        ]
        
        missing_foods = []
        for food in required_foods:
            if food not in data:
                missing_foods.append(food)
        
        if missing_foods:
            print(f"❌ FAIL: Missing food entries: {missing_foods}")
            return False
        
        # Check structure of each entry
        for food_name, food_data in data.items():
            if not isinstance(food_data, dict):
                print(f"❌ FAIL: {food_name} entry is not a dictionary")
                return False
            
            required_keys = ["indb_name", "source", "density", "serving_g"]
            for key in required_keys:
                if key not in food_data:
                    print(f"❌ FAIL: {food_name} missing required key: {key}")
                    return False
            
            # Check specific values
            if food_name == "momos":
                if food_data["source"] != "usda" or food_data["indb_name"] is not None:
                    print(f"❌ FAIL: momos should have source='usda' and indb_name=null")
                    return False
            else:
                if food_data["source"] != "indb":
                    print(f"❌ FAIL: {food_name} should have source='indb'")
                    return False
        
        print(f"✅ PASS: food_label_map.json has all {len(data)} required entries with correct structure")
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ FAIL: food_label_map.json is not valid JSON: {e}")
        return False
    except Exception as e:
        print(f"❌ FAIL: Error reading food_label_map.json: {e}")
        return False

def test_nutrition_database():
    """Test nutrition.db structure and content"""
    print("\n=== Testing nutrition.db ===")
    
    project_root = Path(__file__).parent.parent
    db_path = project_root / "data" / "nutrition.db"
    
    if not test_file_exists(db_path, "nutrition.db exists"):
        return False
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        required_tables = ["indb_recipes", "ifct_ingredients"]
        missing_tables = [table for table in required_tables if table not in tables]
        
        if missing_tables:
            print(f"❌ FAIL: Missing tables: {missing_tables}")
            conn.close()
            return False
        
        # Check table structure
        for table_name in required_tables:
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = [row[1] for row in cursor.fetchall()]
            
            required_columns = ["id", "name", "calories", "protein_g", "carbs_g", "fat_g"]
            missing_columns = [col for col in required_columns if col not in columns]
            
            if missing_columns:
                print(f"❌ FAIL: {table_name} missing columns: {missing_columns}")
                conn.close()
                return False
        
        # Check if tables have data
        for table_name in required_tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
            count = cursor.fetchone()[0]
            
            if count == 0:
                print(f"❌ FAIL: {table_name} table is empty")
                conn.close()
                return False
            
            print(f"✅ PASS: {table_name} has {count} rows")
        
        conn.close()
        print("✅ PASS: nutrition.db has correct structure and data")
        return True
        
    except sqlite3.Error as e:
        print(f"❌ FAIL: Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ FAIL: Error accessing nutrition.db: {e}")
        return False

def test_excel_files():
    """Test Excel data files exist"""
    print("\n=== Testing Excel Data Files ===")
    
    project_root = Path(__file__).parent.parent
    data_dir = project_root / "data"
    
    files_to_check = [
        (data_dir / "INDB.xlsx", "INDB.xlsx"),
        (data_dir / "NIN_fct.xlsx", "NIN_fct.xlsx"),
        (data_dir / "IFCT_fallback.xlsx", "IFCT_fallback.xlsx (fallback)")
    ]
    
    all_passed = True
    for file_path, description in files_to_check:
        if file_path.exists():
            if not test_file_exists(file_path, description):
                all_passed = False
        else:
            # Only fail if both NIN_fct.xlsx and IFCT_fallback.xlsx are missing
            if "NIN_fct" in description or "IFCT_fallback" in description:
                if not (data_dir / "NIN_fct.xlsx").exists() and not (data_dir / "IFCT_fallback.xlsx").exists():
                    print(f"❌ FAIL: Neither NIN_fct.xlsx nor IFCT_fallback.xlsx found")
                    all_passed = False
            else:
                if not test_file_exists(file_path, description):
                    all_passed = False
    
    return all_passed

def test_models_directory():
    """Test models directory exists"""
    print("\n=== Testing Models Directory ===")
    
    project_root = Path(__file__).parent.parent
    models_dir = project_root / "models"
    
    return test_directory_exists(models_dir, "models directory exists")

def main():
    """Run all Phase 0 tests"""
    print("=" * 60)
    print("PHASE 0 - DATA FOUNDATION TEST SUITE")
    print("=" * 60)
    
    tests = [
        ("Food Label Map", test_food_label_map),
        ("Nutrition Database", test_nutrition_database),
        ("Excel Data Files", test_excel_files),
        ("Models Directory", test_models_directory)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ FAIL: {test_name} - Unexpected error: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("PHASE 0 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Phase 0 is complete.")
        return True
    else:
        print("💥 Some tests failed. Please fix the issues before proceeding.")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
