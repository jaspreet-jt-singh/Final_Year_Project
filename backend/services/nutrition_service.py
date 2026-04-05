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
                cursor = await db.execute("SELECT COUNT(*) FROM indb_recipes")
                count = await cursor.fetchone()
                logger.info(f"✅ Connected to nutrition database with {count[0]} recipes")
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize nutrition service: {e}")
            raise
    
    async def get_nutrition_for_food(self, food_label: str) -> dict:
        """
        Get nutrition information for a food label
        Handles both snake_case and PascalCase YOLO labels
        """
        try:
            # Handle different YOLO label formats
            if "_" in food_label:
                # snake_case → Title Case
                display_name = food_label.replace("_", " ").title()
            else:
                # PascalCase → Title Case (add spaces before capital letters)
                import re
                display_name = re.sub(r'([a-z])([A-Z])', r'\1 \2', food_label)
                display_name = display_name.title()
            
            async with aiosqlite.connect(str(self.db_path)) as db:
                # Case-insensitive lookup
                cursor = await db.execute(
                    "SELECT name, calories, protein_g, carbs_g, fat_g FROM indb_recipes WHERE LOWER(name) = LOWER(?)",
                    (display_name,)
                )
                row = await cursor.fetchone()
                
                if row is None:
                    logger.warning(f"Food not found in database: {display_name} (from YOLO: {food_label})")
                    return None
                
                # Extract nutrition data (per 100g as stored in DB)
                name, calories, protein_g, carbs_g, fat_g = row
                
                nutrition_data = {
                    "display_name": name,
                    "macros": {
                        "calories": float(calories),
                        "protein_g": float(protein_g),
                        "carbs_g": float(carbs_g),
                        "fat_g": float(fat_g)
                    }
                }
                
                logger.info(f"Found nutrition data for {name}")
                return nutrition_data
                
        except Exception as e:
            logger.error(f"❌ Error getting nutrition for {food_label}: {e}")
            raise
    
    async def search_foods(self, query: str, limit: int = 10) -> list:
        """Search for foods by name (for future features)"""
        try:
            async with aiosqlite.connect(str(self.db_path)) as db:
                cursor = await db.execute(
                    "SELECT name, calories, protein_g, carbs_g, fat_g FROM indb_recipes WHERE name LIKE ? ORDER BY name LIMIT ?",
                    (f"%{query}%", limit)
                )
                rows = await cursor.fetchall()
                
                results = []
                for row in rows:
                    name, calories, protein_g, carbs_g, fat_g = row
                    results.append({
                        "name": name,
                        "macros": {
                            "calories": float(calories),
                            "protein_g": float(protein_g),
                            "carbs_g": float(carbs_g),
                            "fat_g": float(fat_g)
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
                cursor = await db.execute("SELECT name FROM indb_recipes ORDER BY name")
                rows = await cursor.fetchall()
                return [row[0] for row in rows]
                
        except Exception as e:
            logger.error(f"❌ Error getting all foods: {e}")
            raise
