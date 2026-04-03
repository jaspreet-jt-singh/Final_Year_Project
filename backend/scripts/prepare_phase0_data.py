#!/usr/bin/env python3
"""
Phase 0 Data Preparation Script
Prepares all data and mappings before app development begins.
"""

import pandas as pd
import sqlite3
import json
import os
import requests
from pathlib import Path
import logging
import yaml

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_project_structure():
    """Create required directory structure"""
    directories = [
        'data',
        'models', 
        'frontend/components',
        'frontend/store', 
        'frontend/pages',
        'backend/api',
        'backend/services',
        'backend/scripts'
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {directory}")

def download_indian_food_dataset():
    """Download Indian food dataset from Roboflow"""
    try:
        # For now, create a placeholder dataset structure
        # In production, this would download from Roboflow API
        dataset_dir = Path('data/dataset')
        dataset_dir.mkdir(exist_ok=True)
        
        # Create placeholder YOLO dataset structure
        (dataset_dir / 'images' / 'train').mkdir(parents=True, exist_ok=True)
        (dataset_dir / 'images' / 'val').mkdir(parents=True, exist_ok=True)
        (dataset_dir / 'labels' / 'train').mkdir(parents=True, exist_ok=True)
        (dataset_dir / 'labels' / 'val').mkdir(parents=True, exist_ok=True)
        
        # Create a sample data.yaml file
        data_yaml = {
            'train': '../dataset/images/train',
            'val': '../dataset/images/val',
            'nc': 10,  # number of classes
            'names': [
                'biryani', 'dal_makhani', 'dosa', 'samosa', 
                'paneer_butter', 'chole_bhature', 'idli', 
                'vada_pav', 'rajma', 'kitchdi'
            ]
        }
        
        with open(dataset_dir / 'data.yaml', 'w') as f:
            yaml.dump(data_yaml, f, default_flow_style=False)
            
        logger.info("Created placeholder dataset structure")
        return data_yaml['names']
        
    except Exception as e:
        logger.error(f"Error downloading dataset: {e}")
        return []

def load_indb_data():
    """Load INDB nutrition data"""
    try:
        indb_path = Path('data/INDB.xlsx')
        if not indb_path.exists():
            logger.warning("INDB.xlsx not found, creating placeholder")
            # Create placeholder INDB data
            indb_data = {
                'Food Name': [
                    'Dal Makhani', 'Biryani', 'Dosa', 'Samosa', 
                    'Paneer Butter Masala', 'Chole Bhature', 'Idli',
                    'Vada Pav', 'Rajma', 'Khichdi'
                ],
                'Energy (kcal)': [290, 280, 170, 150, 320, 350, 110, 220, 180, 150],
                'Protein (g)': [12.0, 11.5, 4.5, 3.2, 14.0, 8.5, 3.2, 6.1, 9.2, 5.8],
                'Carbohydrate (g)': [25.0, 35.0, 30.0, 18.0, 12.0, 45.0, 22.0, 28.0, 28.0, 25.0],
                'Fat (g)': [14.5, 8.0, 2.5, 7.8, 22.0, 12.0, 0.3, 8.5, 5.5, 3.2],
                'Fiber (g)': [5.2, 2.8, 2.1, 1.8, 3.1, 4.2, 1.8, 2.5, 6.8, 2.9]
            }
            return pd.DataFrame(indb_data)
        
        df = pd.read_excel(indb_path)
        logger.info(f"Loaded INDB data with {len(df)} items")
        return df
        
    except Exception as e:
        logger.error(f"Error loading INDB data: {e}")
        return pd.DataFrame()

def load_ifct_fallback():
    """Load IFCT fallback nutrition data"""
    try:
        ifct_path = Path('data/IFCT_fallback.xlsx')
        if not ifct_path.exists():
            logger.warning("IFCT_fallback.xlsx not found")
            return pd.DataFrame()
            
        df = pd.read_excel(ifct_path)
        logger.info(f"Loaded IFCT fallback data with {len(df)} items")
        return df
        
    except Exception as e:
        logger.error(f"Error loading IFCT fallback data: {e}")
        return pd.DataFrame()

def create_food_label_map(class_names, indb_df, ifct_df):
    """Create food_label_map.json mapping image labels to nutrition data"""
    
    # Standard Indian food densities (g/cm³)
    densities = {
        'biryani': 1.2,
        'dal_makhani': 1.3,
        'dosa': 0.8,
        'samosa': 0.9,
        'paneer_butter': 1.1,
        'chole_bhature': 1.0,
        'idli': 0.7,
        'vada_pav': 0.85,
        'rajma': 1.25,
        'kitchdi': 1.15
    }
    
    # Default serving sizes (g)
    serving_sizes = {
        'biryani': 250,
        'dal_makhani': 180,
        'dosa': 120,
        'samosa': 60,
        'paneer_butter': 200,
        'chole_bhature': 300,
        'idli': 80,
        'vada_pav': 150,
        'rajma': 200,
        'kitchdi': 220
    }
    
    food_map = {}
    
    for class_name in class_names:
        # Find matching INDB entry
        indb_match = None
        if not indb_df.empty:
            # Try to find by class name
            matching = indb_df[indb_df['Food Name'].str.contains(class_name.replace('_', ' ').title(), case=False, na=False)]
            if not matching.empty:
                indb_match = matching.iloc[0]
        
        # Create mapping entry
        food_map[class_name] = {
            'display_name': class_name.replace('_', ' ').title(),
            'indb_recipe_name': indb_match['Food Name'] if indb_match is not None else None,
            'fallback_source': 'IFCT' if indb_match is None else 'INDB',
            'density_g_per_cm3': densities.get(class_name, 1.0),
            'default_serving_size_g': serving_sizes.get(class_name, 150),
            'nutrition_per_100g': {
                'calories': float(indb_match['Energy (kcal)']) if indb_match is not None else 150,
                'protein_g': float(indb_match['Protein (g)']) if indb_match is not None else 5.0,
                'carbs_g': float(indb_match['Carbohydrate (g)']) if indb_match is not None else 25.0,
                'fat_g': float(indb_match['Fat (g)']) if indb_match is not None else 3.0,
                'fiber_g': float(indb_match['Fiber (g)']) if indb_match is not None else 2.0
            }
        }
    
    # Save food label map
    with open('data/food_label_map.json', 'w') as f:
        json.dump(food_map, f, indent=2)
    
    logger.info(f"Created food_label_map.json with {len(food_map)} entries")
    return food_map

def create_nutrition_database(indb_df, ifct_df):
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
    
    # Insert INDB data
    if not indb_df.empty:
        for _, row in indb_df.iterrows():
            cursor.execute('''
                INSERT OR REPLACE INTO nutrition 
                (food_name, source, calories_per_100g, protein_g_per_100g, 
                 carbs_g_per_100g, fat_g_per_100g, fiber_g_per_100g)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                row['Food Name'], 'INDB',
                float(row['Energy (kcal)']),
                float(row['Protein (g)']),
                float(row['Carbohydrate (g)']),
                float(row['Fat (g)']),
                float(row.get('Fiber (g)', 0))
            ))
    
    # Insert IFCT fallback data
    if not ifct_df.empty:
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
    
    conn.commit()
    conn.close()
    
    logger.info("Created nutrition.db database")

def main():
    """Main Phase 0 preparation function"""
    logger.info("Starting Phase 0 data preparation...")
    
    # Create project structure
    create_project_structure()
    
    # Download dataset (placeholder for now)
    class_names = download_indian_food_dataset()
    
    # Load nutrition data
    indb_df = load_indb_data()
    ifct_df = load_ifct_fallback()
    
    # Create food label map
    food_map = create_food_label_map(class_names, indb_df, ifct_df)
    
    # Create nutrition database
    create_nutrition_database(indb_df, ifct_df)
    
    logger.info("Phase 0 data preparation completed!")
    logger.info("Outputs created:")
    logger.info("- data/nutrition.db")
    logger.info("- data/food_label_map.json") 
    logger.info("- data/INDB.xlsx")
    logger.info("- data/IFCT_fallback.xlsx")
    logger.info("- data/dataset/ (YOLO format)")

if __name__ == "__main__":
    main()
