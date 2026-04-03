#!/usr/bin/env python3
"""
Create nutrition.db SQLite database from nutrition sources
"""

import sqlite3
import json
import pandas as pd
from pathlib import Path

def create_nutrition_database():
    """Create SQLite nutrition database"""
    
    conn = sqlite3.connect('data/nutrition.db')
    cursor = conn.cursor()
    
    # Create nutrition table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS nutrition (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            food_name TEXT UNIQUE,
            source TEXT,
            calories_per_100g REAL,
            protein_g_per_100g REAL,
            carbs_g_per_100g REAL,
            fat_g_per_100g REAL,
            fiber_g_per_100g REAL,
            density_g_per_cm3 REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Load food label map
    with open('data/food_label_map.json', 'r') as f:
        food_map = json.load(f)
    
    # Insert data from food label map
    for food_key, food_data in food_map.items():
        nutrition = food_data['nutrition_per_100g']
        cursor.execute('''
            INSERT OR REPLACE INTO nutrition 
            (food_name, source, calories_per_100g, protein_g_per_100g, 
             carbs_g_per_100g, fat_g_per_100g, fiber_g_per_100g, density_g_per_cm3)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            food_data['display_name'],
            food_data['fallback_source'],
            nutrition['calories'],
            nutrition['protein_g'],
            nutrition['carbs_g'],
            nutrition['fat_g'],
            nutrition['fiber_g'],
            food_data['density_g_per_cm3']
        ))
    
    # Load and insert IFCT fallback data if exists
    if Path('data/IFCT_fallback.xlsx').exists():
        try:
            ifct_df = pd.read_excel('data/IFCT_fallback.xlsx')
            for _, row in ifct_df.iterrows():
                cursor.execute('''
                    INSERT OR REPLACE INTO nutrition 
                    (food_name, source, calories_per_100g, protein_g_per_100g, 
                     carbs_g_per_100g, fat_g_per_100g, fiber_g_per_100g, density_g_per_cm3)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row['Food Name'], 'IFCT',
                    float(row['Energy (kcal)']),
                    float(row['Protein (g)']),
                    float(row['Carbohydrate (g)']),
                    float(row['Fat (g)']),
                    float(row.get('Fiber (g)', 0)),
                    float(row.get('Density (g/cm³)', 1.0))
                ))
        except Exception as e:
            print(f"Error loading IFCT data: {e}")
    
    conn.commit()
    conn.close()
    
    print("Created nutrition.db database")

if __name__ == "__main__":
    create_nutrition_database()
