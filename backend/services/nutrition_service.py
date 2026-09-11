"""
Nutrition Service for Food Data Lookup - Version 2 with Normalized Matching
SQLite database lookup with INDB data only
"""

import re
import logging
import aiosqlite
from difflib import SequenceMatcher
import unicodedata
from collections import OrderedDict
from copy import deepcopy
from backend.settings import Settings

from backend.utils.food_normalizer import normalize_food_name, get_food_variations, find_best_match

logger = logging.getLogger(__name__)


class NutritionService:
    def __init__(self, database_path=None):
        self.db_path = database_path or Settings.from_environment().database_path
        self._results = OrderedDict()
        self._cached_foods = None
        self._yolo_mappings = {}  # Cache for YOLO to DB mappings

    def normalize_text(self, text: str) -> str:
        """Normalize text for better matching"""
        text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
        text = text.lower()
        text = re.sub(r"[^a-z0-9\s]", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def similarity_score(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings"""
        norm1 = self.normalize_text(str1)
        norm2 = self.normalize_text(str2)
        return SequenceMatcher(None, norm1, norm2).ratio()

    async def initialize(self):
        """Initialize database connection and load mappings"""
        try:
            if not self.db_path.exists():
                raise FileNotFoundError(f"Database not found at {self.db_path}")

            async with aiosqlite.connect(self.db_path.resolve().as_uri() + "?mode=ro", uri=True) as db:
                # Get food count
                cursor = await db.execute("SELECT COUNT(*) FROM indb_foods")
                await cursor.fetchone()
                logger.debug("Nutrition lookup step")

                # Cache all food names with their normalized forms
                cursor = await db.execute("SELECT name, normalized_name FROM indb_foods")
                rows = await cursor.fetchall()
                self._cached_foods = {row[0]: row[1] for row in rows}
                logger.debug("Nutrition lookup step")

                # Load YOLO mappings if table exists
                try:
                    cursor = await db.execute("SELECT yolo_class, matched_food_name, match_score FROM yolo_mappings")
                    mappings = await cursor.fetchall()
                    for yolo_class, matched_name, score in mappings:
                        self._yolo_mappings[yolo_class] = {"matched_food_name": matched_name, "match_score": score}
                    logger.debug("Nutrition lookup step")
                except Exception:
                    logger.debug("Nutrition lookup step")

        except Exception:
            logger.debug("Nutrition lookup step")
            raise

    async def get_nutrition_for_food(self, food_label: str) -> dict | None:
        if food_label in self._results:
            self._results.move_to_end(food_label)
            return deepcopy(self._results[food_label])
        result = await self._lookup_nutrition(food_label)
        self._results[food_label] = deepcopy(result)
        self._results.move_to_end(food_label)
        while len(self._results) > 256:
            self._results.popitem(last=False)
        return result

    async def _lookup_nutrition(self, food_label: str) -> dict | None:
        """
        Get nutrition information using normalized name matching
        Returns the ACTUAL database food name that was matched
        """
        try:
            logger.debug("Nutrition lookup step")

            if not self._cached_foods:
                logger.debug("Nutrition lookup step")
                return None

            # Step 1: Check if we have a pre-computed YOLO mapping
            if food_label in self._yolo_mappings:
                mapped_name = self._yolo_mappings[food_label]["matched_food_name"]
                score = self._yolo_mappings[food_label]["match_score"]
                logger.debug("Nutrition lookup step")

                # Get nutrition for the mapped food
                async with aiosqlite.connect(self.db_path.resolve().as_uri() + "?mode=ro", uri=True) as db:
                    return await self._get_nutrition_by_name(db, mapped_name, food_label)

            # Step 2: Try normalized name matching
            normalized_input = normalize_food_name(food_label)
            logger.debug("Nutrition lookup step")

            # Try exact match on normalized names
            for db_name, db_normalized in self._cached_foods.items():
                if normalized_input == db_normalized:
                    logger.debug("Nutrition lookup step")
                    async with aiosqlite.connect(self.db_path.resolve().as_uri() + "?mode=ro", uri=True) as db:
                        return await self._get_nutrition_by_name(db, db_name, food_label)

            # Step 3: Try partial/fuzzy matching on normalized names
            best_match = None
            best_score = 0

            for db_name, db_normalized in self._cached_foods.items():
                # Check if one is contained in the other
                if normalized_input in db_normalized or db_normalized in normalized_input:
                    score = min(len(normalized_input), len(db_normalized)) / max(
                        len(normalized_input), len(db_normalized)
                    )
                    if score > best_score and score >= 0.5:
                        best_score = score
                        best_match = db_name

            if best_match:
                logger.debug("Nutrition lookup step")
                async with aiosqlite.connect(self.db_path.resolve().as_uri() + "?mode=ro", uri=True) as db:
                    return await self._get_nutrition_by_name(db, best_match, food_label)

            # Step 4: Try similarity matching with variations
            variations = get_food_variations(food_label)
            logger.debug("Nutrition lookup step")

            for variation in variations:
                for db_name, db_normalized in self._cached_foods.items():
                    if variation in db_normalized or db_normalized in variation:
                        logger.debug("Nutrition lookup step")
                        async with aiosqlite.connect(self.db_path.resolve().as_uri() + "?mode=ro", uri=True) as db:
                            return await self._get_nutrition_by_name(db, db_name, food_label)

            # Fuzzy matching
            db_names = list(self._cached_foods.keys())
            matched_name, score = find_best_match(food_label, db_names)

            if matched_name and score >= 0.4:  # Lower threshold for last resort
                logger.debug("Nutrition lookup step")
                async with aiosqlite.connect(self.db_path.resolve().as_uri() + "?mode=ro", uri=True) as db:
                    return await self._get_nutrition_by_name(db, matched_name, food_label)

            logger.debug("Nutrition lookup step")
            return None

        except Exception:
            logger.debug("Nutrition lookup step")
            raise

    async def _get_nutrition_by_name(self, db, db_food_name: str, original_label: str) -> dict:
        """Get nutrition data by exact database food name"""
        cursor = await db.execute(
            """
            SELECT name, calories, protein_g, carbs_g, fat_g, source, source_url
            FROM indb_foods
            WHERE name = ?
            """,
            (db_food_name,),
        )
        row = await cursor.fetchone()

        if row:
            name, calories, protein, carbs, fat, source, source_url = row
            return {
                "food_label": original_label,
                "display_name": name,  # Return the ACTUAL database food name
                "found": True,
                "macros": {
                    "calories": float(calories),
                    "protein_g": float(protein),
                    "carbs_g": float(carbs),
                    "fat_g": float(fat),
                },
                "macros_unit": "per_100g",
                "nutrition_source": source or "INDB",
                "nutrition_source_url": source_url or None,
                "food_not_found": False,
            }
        return None

    async def get_all_foods(self) -> list:
        """Get all available foods (for debugging/testing)"""
        try:
            async with aiosqlite.connect(self.db_path.resolve().as_uri() + "?mode=ro", uri=True) as db:
                cursor = await db.execute("SELECT name, normalized_name FROM indb_foods ORDER BY name")
                rows = await cursor.fetchall()
                return [{"name": row[0], "normalized": row[1]} for row in rows]
        except Exception:
            logger.debug("Nutrition lookup step")
            raise


# Backwards compatibility - can be imported directly
NutritionServiceV2 = NutritionService
