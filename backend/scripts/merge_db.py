#!/usr/bin/env python3
"""
Phase 0: Data Foundation - merge_db.py (UPDATED FOR NEW INDB)
Imports INDB.xlsx into SQLite nutrition.db with ONE table only: indb_foods
Correctly processes the actual INDB.xlsx structure
"""

import pandas as pd
import sqlite3
import os
import sys
from pathlib import Path

def main():
    try:
        # Change to project root
        project_root = Path(__file__).parent.parent.parent
        os.chdir(project_root)
        
        print("=== Phase 0: Data Foundation - merge_db.py (UPDATED FOR NEW INDB) ===")
        
        # Step A - Load the new INDB data from "Nutrient Data" sheet
        print("Step A: Loading new INDB.xlsx from 'Nutrient Data' sheet...")
        df = pd.read_excel("data/INDB.xlsx", sheet_name="Nutrient Data")
        print(f"INDB shape: {df.shape}")
        print(f"INDB columns: {df.columns.tolist()}")
        
        # Step B - Verify required columns exist
        print("\nStep B: Verifying required nutrition columns...")
        required_columns = ['food_name', 'energy_kcal', 'protein_g', 'carb_g', 'fat_g']
        available_columns = [col for col in required_columns if col in df.columns]
        
        if len(available_columns) != len(required_columns):
            print(f"❌ Missing columns. Required: {required_columns}")
            print(f"❌ Available: {available_columns}")
            return False
        
        print(f"✅ All required columns found: {available_columns}")
        
        # Step C - Clean and prepare data
        print("\nStep C: Cleaning and preparing data...")
        
        # Select only required columns
        df_clean = df[required_columns].copy()
        
        # Rename columns to match DB schema
        df_clean = df_clean.rename(columns={
            'food_name': 'name',
            'energy_kcal': 'calories',
            'carb_g': 'carbs_g'  # Fix: carb_g -> carbs_g
        })
        
        # Convert to numeric, handling any string values
        for col in ['calories', 'protein_g', 'carbs_g', 'fat_g']:
            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
        
        # Remove rows with missing nutrition data
        initial_count = len(df_clean)
        df_clean = df_clean.dropna(subset=['calories', 'protein_g', 'carbs_g', 'fat_g'])
        final_count = len(df_clean)
        
        print(f"Filtered from {initial_count} to {final_count} food items with complete nutrition data")
        
        # Step D - Show sample of YOLO-relevant foods
        print("\nStep D: YOLO-relevant foods found:")
        yolo_keywords = ['biryani', 'dal', 'dosa', 'samosa', 'palak', 'paneer', 'vada', 'chole', 
                       'aloo', 'idli', 'jalebi', 'gulab', 'kheer', 'lassi', 'poha', 
                       'bhatura', 'pakoda', 'kebab', 'fish', 'mutton', 'coconut', 'green', 
                       'ras', 'kulfi', 'ghevar', 'masala', 'bhindi', 'dum', 'onion']
        
        yolo_foods = []
        for _, row in df_clean.iterrows():
            food_name = str(row['name']).lower()
            if any(keyword in food_name for keyword in yolo_keywords):
                yolo_foods.append({
                    'name': row['name'],
                    'calories': row['calories'],
                    'protein_g': row['protein_g'],
                    'carbs_g': row['carb_g'],
                    'fat_g': row['fat_g']
                })
        
        print(f"Found {len(yolo_foods)} YOLO-relevant foods:")
        for food in yolo_foods[:10]:  # Show first 10
            print(f"  {food['name']:40} {food['calories']:3.0f} cal, {food['protein_g']:4.1f}g P, {food['carbs_g']:4.1f}g C, {food['fat_g']:4.1f}g F")
        if len(yolo_foods) > 10:
            print(f"  ... and {len(yolo_foods) - 10} more")
        
        # Step E - Create data/nutrition.db with ONE table only
        print("\nStep E: Creating SQLite database...")
        
        # Remove existing DB if it exists
        if os.path.exists("data/nutrition.db"):
            os.remove("data/nutrition.db")
            print("Removed existing nutrition.db")
        
        # Create database connection
        conn = sqlite3.connect("data/nutrition.db", check_same_thread=False)
        cursor = conn.cursor()
        
        # Create indb_foods table ONLY
        cursor.execute('''
            CREATE TABLE indb_foods (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                calories REAL,
                protein_g REAL,
                carbs_g REAL,
                fat_g REAL
            )
        ''')
        
        # Insert the cleaned nutrition data
        df_clean.to_sql('indb_foods', conn, if_exists='append', index=False)
        
        # Verify insertion
        cursor.execute("SELECT COUNT(*) FROM indb_foods")
        count = cursor.fetchone()[0]
        print(f"Inserted {count} food items into indb_foods")
        
        # Print sample data
        cursor.execute("SELECT * FROM indb_foods LIMIT 10")
        sample = cursor.fetchall()
        print("\nSample data from database:")
        for row in sample:
            print(f"  {row[1]:40} {row[2]:3.0f} cal, {row[3]:4.1f}g P, {row[4]:4.1f}g C, {row[5]:4.1f}g F")
        
        # Show nutrition statistics
        cursor.execute("SELECT calories, protein_g, carbs_g, fat_g FROM indb_foods")
        all_data = cursor.fetchall()
        
        if all_data:
            calories = [row[0] for row in all_data]
            proteins = [row[1] for row in all_data]
            carbs = [row[2] for row in all_data]
            fats = [row[3] for row in all_data]
            
            print(f"\nNutrition Statistics (per 100g):")
            print(f"Calories: min={min(calories):.0f}, max={max(calories):.0f}, avg={sum(calories)/len(calories):.0f}")
            print(f"Protein:  min={min(proteins):.1f}, max={max(proteins):.1f}, avg={sum(proteins)/len(proteins):.1f}")
            print(f"Carbs:    min={min(carbs):.1f}, max={max(carbs):.1f}, avg={sum(carbs)/len(carbs):.1f}")
            print(f"Fat:      min={min(fats):.1f}, max={max(fats):.1f}, avg={sum(fats)/len(fats):.1f}")
        
        conn.commit()
        conn.close()
        
        print("\n✅ Phase 0 merge_db.py completed successfully!")
        print(f"Database created: data/nutrition.db")
        print(f"Table: indb_foods with {count} rows")
        print(f"Found {len(yolo_foods)} YOLO-relevant foods")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in merge_db.py: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
    
    # Insert the cleaned nutrition data
    df_clean.to_sql('indb_recipes', conn, if_exists='append', index=False)
    
    # Verify insertion
    cursor.execute("SELECT COUNT(*) FROM indb_recipes")
    count = cursor.fetchone()[0]
    print(f"Inserted {count} recipes into indb_recipes")
    
    # Print sample data
    cursor.execute("SELECT * FROM indb_recipes LIMIT 10")
    sample = cursor.fetchall()
    print("\nSample data from database:")
    for row in sample:
        print(f"  {row[1]:40} {row[2]:3.0f} cal, {row[3]:4.1f}g P, {row[4]:4.1f}g C, {row[5]:4.1f}g F")
    
    # Show nutrition statistics
    cursor.execute("SELECT calories, protein_g, carbs_g, fat_g FROM indb_recipes")
    all_data = cursor.fetchall()
    
    if all_data:
        calories = [row[0] for row in all_data]
        proteins = [row[1] for row in all_data]
        carbs = [row[2] for row in all_data]
        fats = [row[3] for row in all_data]
        
        print(f"\nNutrition Statistics (per 100g):")
        print(f"Calories: min={min(calories):.0f}, max={max(calories):.0f}, avg={sum(calories)/len(calories):.0f}")
        print(f"Protein:  min={min(proteins):.1f}, max={max(proteins):.1f}, avg={sum(proteins)/len(proteins):.1f}")
        print(f"Carbs:    min={min(carbs):.1f}, max={max(carbs):.1f}, avg={sum(carbs)/len(carbs):.1f}")
        print(f"Fat:      min={min(fats):.1f}, max={max(fats):.1f}, avg={sum(fats)/len(fats):.1f}")
    
    conn.commit()
    conn.close()
    
    print("\n✅ Phase 0 merge_db.py completed successfully!")
    print(f"Database created: data/nutrition.db")
    print(f"Table: indb_recipes with {count} rows")
    print(f"Found {len(yolo_foods)} YOLO-relevant foods")

if __name__ == "__main__":
    main()
