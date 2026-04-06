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
from difflib import SequenceMatcher
import unicodedata

logger = logging.getLogger(__name__)

class NutritionService:
    def __init__(self):
        self.db_path = None
        self._cached_foods = None  # Cache for dynamic matching
        
    def normalize_text(self, text: str) -> str:
        """Normalize text for better matching"""
        # Remove diacritics and convert to lowercase
        text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
        text = text.lower()
        # Remove extra spaces and special characters
        text = re.sub(r'[^a-z0-9\s]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def similarity_score(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings"""
        norm1 = self.normalize_text(str1)
        norm2 = self.normalize_text(str2)
        return SequenceMatcher(None, norm1, norm2).ratio()
        
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
                
                # Cache all food names for dynamic matching
                cursor = await db.execute("SELECT name FROM indb_foods ORDER BY name")
                rows = await cursor.fetchall()
                self._cached_foods = [row[0] for row in rows]
                logger.info(f"✅ Cached {len(self._cached_foods)} food names for dynamic matching")
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize nutrition service: {e}")
            raise
    
    async def get_nutrition_for_food(self, food_label: str) -> dict:
        """
        Get nutrition information for a food label using dynamic matching
        """
        try:
            logger.info(f"🔍 Looking up nutrition for YOLO label: '{food_label}'")
            
            if not self._cached_foods:
                logger.error("❌ Food cache not initialized")
                return None
            
            # Generate multiple search variations for the YOLO label
            search_variations = self._generate_search_variations(food_label)
            logger.info(f"📝 Generated {len(search_variations)} search variations")
            
            async with aiosqlite.connect(str(self.db_path)) as db:
                # Try each search variation with different strategies
                for i, search_term in enumerate(search_variations, 1):
                    logger.info(f"🔄 Strategy {i}: Trying '{search_term}'")
                    
                    # Strategy 1: Exact match
                    row = await self._try_exact_match(db, search_term)
                    if row:
                        logger.info(f"✅ Found exact match: '{row[0]}'")
                        return self._format_nutrition_result(row, food_label, row[0])
                    
                    # Strategy 2: Fuzzy match with high threshold
                    row = await self._try_fuzzy_match(db, search_term, threshold=0.8)
                    if row:
                        logger.info(f"✅ Found fuzzy match (high): '{row[0]}'")
                        return self._format_nutrition_result(row, food_label, row[0])
                
                # Strategy 3: Best fuzzy match with lower threshold
                logger.info("🔄 Final strategy: Best fuzzy match")
                best_match = await self._find_best_fuzzy_match(db, food_label, threshold=0.6)
                if best_match:
                    row, score = best_match
                    logger.info(f"✅ Found best fuzzy match: '{row[0]}' (score: {score:.2f})")
                    return self._format_nutrition_result(row, food_label, row[0])
                
                # Strategy 4: Partial word matching
                row = await self._try_partial_match(db, food_label)
                if row:
                    logger.info(f"✅ Found partial match: '{row[0]}'")
                    return self._format_nutrition_result(row, food_label, row[0])
                
                logger.warning(f"❌ No match found for '{food_label}'")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error getting nutrition for {food_label}: {e}")
            raise
    
    def _generate_search_variations(self, food_label: str) -> list:
        """Generate multiple search variations for a YOLO label"""
        variations = []
        
        # Original label
        variations.append(food_label)
        
        # Title case with spaces
        if "_" in food_label:
            variations.append(food_label.replace("_", " ").title())
        
        # PascalCase to Title Case
        spaced = re.sub(r'([a-z])([A-Z])', r'\1 \2', food_label)
        variations.append(spaced.title())
        
        # Lowercase versions
        variations.extend([v.lower() for v in variations])
        
        # Without spaces
        variations.extend([v.replace(" ", "") for v in variations])
        
        # Common food word mappings
        food_mappings = {
            'whiterice': 'White Rice',
            'browrice': 'Brown Rice',
            'ghevar': 'Ghevar',
            'jalebi': 'Jalebi',
            'samosa': 'Samosa',
            'dosa': 'Dosa',
            'idli': 'Idli',
            'chai': 'Chai',
            'tea': 'Tea',
            'coffee': 'Coffee'
        }
        
        normalized_label = self.normalize_text(food_label)
        for key, value in food_mappings.items():
            if key in normalized_label or normalized_label in key:
                variations.append(value)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_variations = []
        for v in variations:
            if v not in seen:
                seen.add(v)
                unique_variations.append(v)
        
        return unique_variations
    
    async def _try_exact_match(self, db, search_term: str):
        """Try exact case-insensitive match"""
        cursor = await db.execute(
            "SELECT name, calories, protein_g, carbs_g, fat_g FROM indb_foods WHERE LOWER(name) = LOWER(?)",
            (search_term,)
        )
        return await cursor.fetchone()
    
    async def _try_fuzzy_match(self, db, search_term: str, threshold: float = 0.8):
        """Try fuzzy matching with threshold"""
        if not self._cached_foods:
            return None
        
        best_match = None
        best_score = 0
        
        for food_name in self._cached_foods:
            score = self.similarity_score(search_term, food_name)
            if score >= threshold and score > best_score:
                best_score = score
                best_match = food_name
        
        if best_match:
            cursor = await db.execute(
                "SELECT name, calories, protein_g, carbs_g, fat_g FROM indb_foods WHERE name = ?",
                (best_match,)
            )
            return await cursor.fetchone()
        
        return None
    
    async def _find_best_fuzzy_match(self, db, food_label: str, threshold: float = 0.6):
        """Find the best fuzzy match above threshold"""
        if not self._cached_foods:
            return None
        
        best_match = None
        best_score = 0
        
        for food_name in self._cached_foods:
            score = self.similarity_score(food_label, food_name)
            if score >= threshold and score > best_score:
                best_score = score
                best_match = food_name
        
        if best_match:
            cursor = await db.execute(
                "SELECT name, calories, protein_g, carbs_g, fat_g FROM indb_foods WHERE name = ?",
                (best_match,)
            )
            row = await cursor.fetchone()
            return (row, best_score) if row else None
        
        return None
    
    async def _try_partial_match(self, db, food_label: str):
        """Try partial word matching"""
        words = food_label.lower().replace('_', ' ').split()
        
        for word in words:
            if len(word) < 3:  # Skip very short words
                continue
                
            cursor = await db.execute(
                "SELECT name, calories, protein_g, carbs_g, fat_g FROM indb_foods WHERE LOWER(name) LIKE ? ORDER BY LENGTH(name) ASC LIMIT 1",
                (f"%{word}%",)
            )
            row = await cursor.fetchone()
            
            if row:
                # Check if the match is reasonable (not too long)
                if len(row[0]) <= len(word) + 10:
                    return row
        
        return None
    
    def _format_nutrition_result(self, row, food_label: str, matched_name: str) -> dict:
        """Format the nutrition result"""
        name, calories, protein, carbs, fat = row
        
        return {
            "food_label": food_label,
            "display_name": matched_name,
            "found": True,
            "macros": {
                "calories": float(calories),
                "protein_g": float(protein),
                "carbs_g": float(carbs),
                "fat_g": float(fat)
            },
            "macros_unit": "per_100g",
            "nutrition_source": "INDB",
            "food_not_found": False
        }
    
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
