#!/usr/bin/env python3
"""
Phase 0: Data Foundation - merge_db.py
Imports INDB.xlsx into SQLite nutrition.db with ONE table only: indb_recipes
"""

import pandas as pd
import sqlite3
import os
from pathlib import Path

def main():
    # Change to project root
    project_root = Path(__file__).parent.parent.parent
    os.chdir(project_root)
    
    print("=== Phase 0: Data Foundation - merge_db.py ===")
    
    # Step A - Inspect and print raw columns
    print("Step A: Inspecting INDB.xlsx structure...")
    df = pd.read_excel("data/INDB.xlsx", sheet_name=0)
    print(f"INDB shape: {df.shape}")
    print(f"INDB columns: {df.columns.tolist()}")
    
    # Step B - Rename columns to match DB schema
    print("\nStep B: Renaming columns to match DB schema...")
    rename_map = {
        "energy_kcal": "calories",
        "carb_g": "carbs_g", 
        "protein_g": "protein_g",  # already correct
        "fat_g": "fat_g",          # already correct
    }
    
    # Only rename columns that exist
    actual_renames = {}
    for old_col, new_col in rename_map.items():
        if old_col in df.columns:
            actual_renames[old_col] = new_col
    
    if actual_renames:
        df = df.rename(columns=actual_renames)
        print(f"Renamed columns: {actual_renames}")
    else:
        print("No columns needed renaming")
    
    # Step C - Normalise recipe names to title case
    print("\nStep C: Normalising recipe names...")
    if 'name' in df.columns:
        df["name"] = df["name"].str.strip().str.title()
        print("Recipe names normalised to title case")
    else:
        print("ERROR: 'name' column not found!")
        return
    
    # Step D - Print all recipe names for manual verification
    print("\nStep D: All INDB recipe names (sorted):")
    print("=" * 50)
    for name in sorted(df["name"].tolist()):
        print(name)
    print("=" * 50)
    
    # Step E - Create data/nutrition.db with ONE table only
    print("\nStep E: Creating SQLite database...")
    
    # Remove existing DB if it exists
    if os.path.exists("data/nutrition.db"):
        os.remove("data/nutrition.db")
        print("Removed existing nutrition.db")
    
    # Create database connection
    conn = sqlite3.connect("data/nutrition.db", check_same_thread=False)
    cursor = conn.cursor()
    
    # Create indb_recipes table ONLY
    cursor.execute('''
        CREATE TABLE indb_recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            calories REAL,
            protein_g REAL,
            carbs_g REAL,
            fat_g REAL
        )
    ''')
    
    # Insert only rows where all four macro columns are non-null
    required_columns = ['calories', 'protein_g', 'carbs_g', 'fat_g']
    available_columns = [col for col in required_columns if col in df.columns]
    
    if len(available_columns) != 4:
        print(f"ERROR: Missing macro columns. Available: {available_columns}")
        conn.close()
        return
    
    # Filter out rows with null values in any macro column
    df_clean = df.dropna(subset=required_columns)
    print(f"Filtered from {len(df)} to {len(df_clean)} rows with complete macro data")
    
    # Insert data
    insert_columns = ['name'] + required_columns
    df_to_insert = df_clean[insert_columns]
    
    df_to_insert.to_sql('indb_recipes', conn, if_exists='append', index=False)
    
    # Verify insertion
    cursor.execute("SELECT COUNT(*) FROM indb_recipes")
    count = cursor.fetchone()[0]
    print(f"Inserted {count} recipes into indb_recipes")
    
    # Print sample data
    cursor.execute("SELECT * FROM indb_recipes LIMIT 5")
    sample = cursor.fetchall()
    print("\nSample data:")
    for row in sample:
        print(row)
    
    conn.commit()
    conn.close()
    
    print("\n✅ Phase 0 merge_db.py completed successfully!")
    print(f"Database created: data/nutrition.db")
    print(f"Table: indb_recipes with {count} rows")

if __name__ == "__main__":
    main()
