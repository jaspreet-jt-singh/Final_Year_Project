"""
Nutrition Service for Food Data Lookup
Phase 1: SQLite database lookup with INDB data only
"""

import sqlite3
import asyncio
import re
from pathlib import Path
import logging
import aiosqlite

logger = logging.getLogger(__name__)

class NutritionService:
    def __init__(self):
        self.db_path = None
        
    async def initialize(self):
        """Initialize database connection"""
        try:
            # Get database path
            project_root = Path(__file__).parent.parent.parent
            self.db_path = project_root / "data" / "nutrition.db"
            
            if not self.db_path.exists():
                raise FileNotFoundError(f"Database not found at {self.db_path}")
            
            # Test database connection
            async with aiosqlite.connect(str(self.db_path)) as db:
                cursor = await db.execute("SELECT COUNT(*) FROM indb_foods")
                count = await cursor.fetchone()
                logger.info(f"✅ Connected to nutrition database with {count[0]} food items")
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize nutrition service: {e}")
            raise
    
    async def get_nutrition_for_food(self, food_label: str) -> dict:
        """
        Get nutrition information for a food label
        Comprehensive mapping for all YOLO classes
        """
        try:
            # Comprehensive mapping for all YOLO classes to database names
            comprehensive_mappings = {
                # Exact matches (should work directly)
                "Biryani": "Biryani",
                "Chai": "Chai",
                "Dal": "Dal",
                "Dosa": "Dosa",
                "Samosa": "Samosa",
                "Idli": "Idli",
                "Jalebi": "Jalebi",
                "Kheer": "Kheer",
                "Poha": "Poha",
                
                # Special case mappings
                "WhiteRice": "White Rice",
                "whiterice": "White Rice",
                "White rice": "White Rice",
                
                # PascalCase → Title Case with variations
                "AlooGobi": "Aloo Gobi",
                "AlooMasala": "Aloo Masala", 
                "Bhatura": "Bhatura",
                "BhindiMasala": "Bhindi Masala",
                "Chole": "Chole",
                "CoconutChutney": "Coconut Chutney",
                "DumAloo": "Dum Aloo",
                "FishCurry": "Fish Curry",
                "Ghevar": "Ghevar",
                "GreenChutney": "Green Chutney",
                "GulabJamun": "Gulab Jamun",
                "Kebab": "Kebab",
                "Kulfi": "Kulfi",
                "Lassi": "Lassi",
                "MuttonCurry": "Mutton Curry",
                "OnionPakoda": "Onion Pakoda",
                "PalakPaneer": "Palak Paneer",
                "RajmaCurry": "Rajma Curry",
                "RasMalai": "Ras Malai",
                "ShahiPaneer": "Shahi Paneer",
                "VadaPav": "Vada Pav"
            }
            
            # Get the mapped name
            display_name = comprehensive_mappings.get(food_label, food_label)
            
            # If no specific mapping, apply default normalization
            if display_name == food_label:
                if "_" in food_label:
                    display_name = food_label.replace("_", " ").title()
                else:
                    display_name = re.sub(r'([a-z])([A-Z])', r'\1 \2', food_label)
                    display_name = display_name.title()
            
            logger.info(f"YOLO: '{food_label}' → Mapped: '{display_name}'")
            
            async with aiosqlite.connect(str(self.db_path)) as db:
                # Strategy 1: Exact case-insensitive match
                cursor = await db.execute(
                    "SELECT name, calories, protein_g, carbs_g, fat_g FROM indb_foods WHERE LOWER(name) = LOWER(?)",
                    (display_name,)
                )
                row = await cursor.fetchone()
                logger.info(f"Strategy 1 - Looking for: '{display_name}' → Found: {row is not None}")
                
                if row is None:
                    # Strategy 2: Try without spaces
                    no_space_name = display_name.replace(" ", "")
                    cursor = await db.execute(
                        "SELECT name, calories, protein_g, carbs_g, fat_g FROM indb_foods WHERE LOWER(name) = LOWER(?)",
                        (no_space_name,)
                    )
                    row = await cursor.fetchone()
                    logger.info(f"Strategy 2 - Looking for: '{no_space_name}' → Found: {row is not None}")
                
                if row is None:
                    # Strategy 3: Try partial match with better selection
                    first_word = display_name.split()[0]
                    cursor = await db.execute(
                        "SELECT name, calories, protein_g, carbs_g, fat_g FROM indb_foods WHERE LOWER(name) LIKE LOWER(?) || '%' ORDER BY LENGTH(name) ASC LIMIT 5",
                        (first_word,)
                    )
                    rows = await cursor.fetchall()
                    if rows:
                        # Prefer shorter, more relevant matches
                        best_match = min(rows, key=lambda x: len(x[0]))
                        if len(best_match[0]) <= len(first_word) + 5:
                            row = best_match
                            logger.info(f"Strategy 3 - Selected best match: '{row[0]}' from {len(rows)} options")
                
                if row is None:
                    # Strategy 4: Try original YOLO label
                    cursor = await db.execute(
                        "SELECT name, calories, protein_g, carbs_g, fat_g FROM indb_foods WHERE LOWER(name) = LOWER(?)",
                        (food_label,)
                    )
                    row = await cursor.fetchone()
                    logger.info(f"Strategy 4 - Looking for: '{food_label}' → Found: {row is not None}")
                
                if row is None:
                    logger.warning(f"Food not found in database: {display_name} (from YOLO: {food_label})")
                    return None
                
                # Extract nutrition data (per 100g as stored in DB)
                name, calories, protein_g, carbs_g, fat_g = row
                
                # Validate nutrition values are reasonable
                if calories <= 0 or protein_g < 0 or carbs_g < 0 or fat_g < 0:
                    logger.warning(f"Invalid nutrition values for {name}: calories={calories}, protein={protein_g}, carbs={carbs_g}, fat={fat_g}")
                
                nutrition_data = {
                    "display_name": name,
                    "macros": {
                        "calories": float(calories),
                        "protein_g": float(protein_g),
                        "carbs_g": float(carbs_g),
                        "fat_g": float(fat_g)
                    }
                }
                
                logger.info(f"Found nutrition data for {name}: {calories:.1f} cal, {protein_g:.1f}g protein, {carbs_g:.1f}g carbs, {fat_g:.1f}g fat")
                
                # Double-check the values being returned
                final_nutrition = {
                    "display_name": name,
                    "macros": {
                        "calories": float(calories),
                        "protein_g": float(protein_g),
                        "carbs_g": float(carbs_g),
                        "fat_g": float(fat_g)
                    }
                }
                
                logger.info(f"FINAL NUTRITION DATA: {final_nutrition}")
                return final_nutrition
                
        except Exception as e:
            logger.error(f"❌ Error getting nutrition for {food_label}: {e}")
            raise
    
    async def search_foods(self, query: str, limit: int = 10) -> list:
        """Search for foods by name (for future features)"""
        try:
            async with aiosqlite.connect(str(self.db_path)) as db:
                cursor = await db.execute(
                    "SELECT name, calories, protein_g, carbs_g, fat_g FROM indb_foods WHERE name LIKE ? ORDER BY name LIMIT ?",
                    (f"%{query}%", limit)
                )
                rows = await cursor.fetchall()
                
                results = []
                for row in rows:
                    name, calories, protein, carbs, fat = row
                    results.append({
                        "name": name,
                        "macros": {
                            "calories": float(calories),
                            "protein_g": float(protein),
                            "carbs_g": float(carbs),
                            "fat_g": float(fat)
                        }
                    })
                
                return results
                
        except Exception as e:
            logger.error(f"❌ Error searching foods: {e}")
            raise
    
    async def get_all_foods(self) -> list:
        """Get all available foods (for debugging/testing)"""
        try:
            async with aiosqlite.connect(str(self.db_path)) as db:
                cursor = await db.execute("SELECT name FROM indb_foods ORDER BY name")
                rows = await cursor.fetchall()
                return [row[0] for row in rows]
                
        except Exception as e:
            logger.error(f"❌ Error getting all foods: {e}")
            raise
