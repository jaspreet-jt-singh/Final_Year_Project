"""
Food Name Normalizer - Standardizes food names for better matching
Converts various formats (camelCase, snake_case, Title Case) to normalized form
"""

import re
import json
from pathlib import Path


def _load_food_aliases() -> dict:
    """Load food aliases from config file dynamically"""
    config_path = Path(__file__).parent.parent / "config" / "food_aliases.json"
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


# Load aliases dynamically at module load time
_FOOD_ALIASES = _load_food_aliases()

def normalize_food_name(name: str) -> str:
    """
    Normalize food name for matching:
    - 'AlooGobi' → 'aloogobi'
    - 'Onion Pakoda' → 'onionpakoda'
    - 'Samosa (Aloo)' → 'samosaaloo'
    - 'Fish curry (Machli)' → 'fishcurrymachli'
    
    Returns lowercase string with only alphanumeric characters
    """
    if not name:
        return ""
    
    # Convert to string and lowercase
    name = str(name).lower()
    
    # Insert space before uppercase letters (for camelCase)
    # e.g., 'AlooGobi' → 'Aloo Gobi'
    name = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
    
    # Replace underscores and hyphens with space
    name = name.replace('_', ' ').replace('-', ' ')
    
    # Remove parentheses and their contents (descriptions)
    # 'Samosa (Aloo)' → 'Samosa'
    name = re.sub(r'\s*\([^)]*\)', '', name)
    
    # Remove all non-alphanumeric characters
    name = re.sub(r'[^a-z0-9]', '', name)
    
    return name


def get_food_variations(name: str) -> list:
    """
    Generate multiple search variations for a food name
    Returns list of normalized variations to try
    """
    variations = set()

    # Base normalized form
    base = normalize_food_name(name)
    if base:
        variations.add(base)

    # Load aliases dynamically
    food_aliases = _load_food_aliases()

    # Check if any alias matches our base name
    for key, aliases in food_aliases.items():
        if key in base:
            # Add the key itself
            variations.add(key)
            # Add all aliases
            for alias in aliases:
                variations.add(alias)
            # Add combinations
            for alias in aliases:
                variations.add(base.replace(key, alias))

    # Also check reverse - if alias is in base
    for key, aliases in food_aliases.items():
        for alias in aliases:
            if alias in base:
                variations.add(key)
                variations.add(base.replace(alias, key))

    return list(variations)


def find_best_match(yolo_label: str, db_foods: list) -> tuple:
    """
    Find best matching food from database
    Returns: (matched_food_name, match_score) or (None, 0)
    """
    yolo_normalized = normalize_food_name(yolo_label)
    yolo_variations = get_food_variations(yolo_label)
    
    best_match = None
    best_score = 0
    
    for db_food in db_foods:
        db_normalized = normalize_food_name(db_food)
        
        # Exact match
        if yolo_normalized == db_normalized:
            return (db_food, 1.0)
        
        # Check if any variation matches
        for var in yolo_variations:
            if var in db_normalized or db_normalized in var:
                # Calculate similarity score based on length ratio
                score = min(len(var), len(db_normalized)) / max(len(var), len(db_normalized))
                if score > best_score and score >= 0.5:  # Minimum 50% match
                    best_score = score
                    best_match = db_food
    
    return (best_match, best_score) if best_match else (None, 0)


if __name__ == "__main__":
    # Test the normalizer
    test_cases = [
        "AlooGobi",
        "Onion Pakoda",
        "Samosa (Aloo ka samosa)",
        "Fish curry (Machli curry)",
        "PalakPaneer",
        "Mutton_biryani",
        "Green-Chutney",
        "Kheer",
    ]
    
    print("Food Name Normalizer Tests:")
    print("=" * 60)
    for test in test_cases:
        normalized = normalize_food_name(test)
        variations = get_food_variations(test)
        print(f"\nInput: {test}")
        print(f"  Normalized: {normalized}")
        print(f"  Variations: {variations[:5]}{'...' if len(variations) > 5 else ''}")
