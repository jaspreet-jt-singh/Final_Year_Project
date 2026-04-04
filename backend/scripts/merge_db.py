import pandas as pd
import sqlite3
import os
from pathlib import Path

def merge_databases():
    """Merge INDB.xlsx and NIN_fct.xlsx into SQLite database"""
    
    # Paths
    project_root = Path(__file__).parent.parent.parent
    data_dir = project_root / "data"
    db_path = data_dir / "nutrition.db"
    
    print("=== Phase 0: Database Merge ===")
    
    # Read INDB.xlsx
    indb_path = data_dir / "INDB.xlsx"
    print(f"\nReading INDB.xlsx from: {indb_path}")
    
    if not indb_path.exists():
        print(f"ERROR: {indb_path} not found!")
        return False
    
    indb_df = pd.read_excel(indb_path, sheet_name=0)
    print("INDB.xlsx columns:")
    for i, col in enumerate(indb_df.columns):
        print(f"  {i}: {col}")
    
    # Read NIN_fct.xlsx (check both possible names)
    nin_path = data_dir / "NIN_fct.xlsx"
    if not nin_path.exists():
        nin_path = data_dir / "IFCT_fallback.xlsx"
    
    print(f"\nReading NIN/IFCT data from: {nin_path}")
    
    if not nin_path.exists():
        print(f"ERROR: {nin_path} not found!")
        return False
    
    nin_df = pd.read_excel(nin_path, sheet_name=0, engine='openpyxl')
    print("IFCT_fallback.xlsx columns:")
    for i, col in enumerate(nin_df.columns):
        print(f"  {i}: {col}")
    
    # Create SQLite database
    print(f"\nCreating SQLite database: {db_path}")
    
    # Ensure data directory exists
    data_dir.mkdir(exist_ok=True)
    
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS indb_recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            calories REAL,
            protein_g REAL,
            carbs_g REAL,
            fat_g REAL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ifct_ingredients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            calories REAL,
            protein_g REAL,
            carbs_g REAL,
            fat_g REAL
        )
    ''')
    
    # Process INDB data
    print("\nProcessing INDB data...")
    indb_inserted = 0
    
    # Try to find relevant columns (case-insensitive)
    indb_cols = {col.lower(): col for col in indb_df.columns}
    
    # Common column name variations for INDB
    name_col = 'recipe_name'  # Use recipe_name from INDB
    calories_col = None  # Will need to calculate or find
    protein_col = None
    carbs_col = None
    fat_col = None
    
    # Try to find nutrition columns in INDB
    for col in indb_df.columns:
        col_lower = col.lower()
        if 'calorie' in col_lower or 'energy' in col_lower:
            calories_col = col
        elif 'protein' in col_lower:
            protein_col = col
        elif 'carb' in col_lower or 'carbohyd' in col_lower:
            carbs_col = col
        elif 'fat' in col_lower or 'lipid' in col_lower:
            fat_col = col
    
    print(f"INDB column mapping:")
    print(f"  Name: {name_col}")
    print(f"  Calories: {calories_col}")
    print(f"  Protein: {protein_col}")
    print(f"  Carbs: {carbs_col}")
    print(f"  Fat: {fat_col}")
    
    if all([name_col, calories_col, protein_col, carbs_col, fat_col]):
        for _, row in indb_df.iterrows():
            try:
                cursor.execute('''
                    INSERT INTO indb_recipes (name, calories, protein_g, carbs_g, fat_g)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    str(row[name_col]) if pd.notna(row[name_col]) else "",
                    float(row[calories_col]) if pd.notna(row[calories_col]) else 0.0,
                    float(row[protein_col]) if pd.notna(row[protein_col]) else 0.0,
                    float(row[carbs_col]) if pd.notna(row[carbs_col]) else 0.0,
                    float(row[fat_col]) if pd.notna(row[fat_col]) else 0.0
                ))
                indb_inserted += 1
            except Exception as e:
                print(f"Error inserting INDB row: {e}")
    else:
        print("ERROR: Could not map all required INDB columns!")
        return False
    
    print(f"INDB recipes inserted: {indb_inserted}")
    
    # Process NIN FCT data
    print("\nProcessing NIN FCT data...")
    nin_inserted = 0
    
    # Try to find relevant columns for IFCT
    name_col = None
    calories_col = None
    protein_col = None
    carbs_col = None
    fat_col = None
    
    # Find columns in IFCT
    for col in nin_df.columns:
        col_lower = col.lower()
        if 'name' in col_lower or 'food' in col_lower:
            name_col = col
        elif 'calorie' in col_lower or 'energy' in col_lower:
            calories_col = col
        elif 'protein' in col_lower:
            protein_col = col
        elif 'carb' in col_lower or 'carbohyd' in col_lower:
            carbs_col = col
        elif 'fat' in col_lower or 'lipid' in col_lower:
            fat_col = col
    
    print(f"NIN column mapping:")
    print(f"  Name: {name_col}")
    print(f"  Calories: {calories_col}")
    print(f"  Protein: {protein_col}")
    print(f"  Carbs: {carbs_col}")
    print(f"  Fat: {fat_col}")
    
    if all([name_col, calories_col, protein_col, carbs_col, fat_col]):
        for _, row in nin_df.iterrows():
            try:
                cursor.execute('''
                    INSERT INTO ifct_ingredients (name, calories, protein_g, carbs_g, fat_g)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    str(row[name_col]) if pd.notna(row[name_col]) else "",
                    float(row[calories_col]) if pd.notna(row[calories_col]) else 0.0,
                    float(row[protein_col]) if pd.notna(row[protein_col]) else 0.0,
                    float(row[carbs_col]) if pd.notna(row[carbs_col]) else 0.0,
                    float(row[fat_col]) if pd.notna(row[fat_col]) else 0.0
                ))
                nin_inserted += 1
            except Exception as e:
                print(f"Error inserting NIN row: {e}")
    else:
        print("ERROR: Could not map all required NIN columns!")
        return False
    
    print(f"NIN ingredients inserted: {nin_inserted}")
    
    # Commit and close
    conn.commit()
    
    # Verify row counts
    cursor.execute("SELECT COUNT(*) FROM indb_recipes")
    indb_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM ifct_ingredients")
    nin_count = cursor.fetchone()[0]
    
    print(f"\n=== Database Summary ===")
    print(f"INDB recipes: {indb_count} rows")
    print(f"NIN ingredients: {nin_count} rows")
    print(f"Database created: {db_path}")
    
    conn.close()
    return True

if __name__ == "__main__":
    success = merge_databases()
    if success:
        print("\n✅ Database merge completed successfully!")
    else:
        print("\n❌ Database merge failed!")
