"""Deterministic recommendation fallback and response parsing."""


def parse_recommendations(content: str) -> list:
    """
    Parse LLM response into a list of recommendations.
    Only extracts lines that are actual bullet points (starting with -, *, •).
    Skips any preamble or introductory text before the bullet points.
    """
    if not content:
        return []

    recommendations = []
    lines = content.split("\n")
    for line in lines:
        line = line.strip()
        # Only match lines that start with bullet point markers
        if line.startswith("- ") or line.startswith("* ") or line.startswith("• "):
            # Strip the bullet marker and any extra leading whitespace
            text = line[2:].strip()
            if text:
                recommendations.append(text)
        elif line.startswith("-") or line.startswith("*") or line.startswith("•"):
            # Handle cases where bullet marker has no space after it
            text = line[1:].strip()
            if text:
                recommendations.append(text)

    return recommendations[:3]  # Return max 3 recommendations


def fallback_recommendations(detected_foods: list, user_goal: str, health_condition: str = "none") -> list:
    """
    Fallback recommendations when LLM is not available.
    Provides generic but useful advice based on goal and health condition.
    """
    goal_lower = user_goal.lower().replace(" ", "_")

    # Get detected food names for context
    food_names = [f.get("display_name", f.get("food_label", "food")) for f in detected_foods]
    food_str = ", ".join(food_names[:2])  # Mention first 2 foods

    # Health condition specific base recommendations
    condition_recommendations = {
        "diabetic": [
            f"After having {food_str}, pair it with a protein or fiber source like roasted chana or salad to slow glucose absorption.",
            "Opt for whole grains like brown rice, millets, or whole wheat roti for your next meal to keep blood sugar stable.",
            "Consider a small walk after meals — even 10 minutes helps with blood sugar management.",
        ],
        "hypertension": [
            f"Your {food_str} is noted — avoid adding extra salt to your next meals. Use herbs, lemon, or masala instead.",
            "Include potassium-rich foods like banana, spinach, or yogurt in your diet today to help balance sodium.",
            "Stay away from packaged snacks and pickles for the rest of the day as they're high in hidden sodium.",
        ],
        "heart_disease": [
            f"Balance your {food_str} with omega-3 rich foods like flaxseeds, walnuts, or fatty fish in your next meal.",
            "Choose cooking methods like steaming, boiling, or light sautéing over deep frying for heart health.",
            "Add a serving of leafy greens or colorful vegetables to increase heart-protective antioxidants.",
        ],
        "high_cholesterol": [
            f"After {food_str}, focus on high-fiber foods like oats, barley, or apple for your next snack to help lower cholesterol.",
            "Include plant-based proteins like dal, chickpeas, or soy instead of red meat for the rest of the day.",
            "Add a tablespoon of soaked flaxseeds or nuts to your meals for healthy omega-3 fats.",
        ],
        "digestive_issues": [
            f"Your {food_str} is fine — for your next meal, choose easily digestible foods like khichdi, curd rice, or clear soups.",
            "Avoid spicy, oily, or raw foods for the rest of the day. Stick to warm, cooked meals.",
            "Eat smaller, more frequent meals rather than large portions to ease digestion.",
        ],
        "kidney_disease": [
            f"After {food_str}, keep your next meal low in potassium — avoid bananas, potatoes, and tomatoes in large amounts.",
            "Control protein portion sizes — a palm-sized serving of dal or paneer is sufficient per meal.",
            "Stay hydrated with plain water, but avoid packaged juices and coconut water which may be high in potassium.",
        ],
        "anemia": [
            f"Pair your {food_str} with iron-rich foods like spinach, beetroot, or jaggery in your next meal.",
            "Include vitamin C sources like lemon, amla, or oranges with your meals to improve iron absorption.",
            "Avoid drinking tea or coffee within an hour of meals as tannins reduce iron absorption.",
        ],
        "thyroid": [
            f"Your {food_str} is good — for your next meal include selenium-rich foods like brazil nuts, eggs, or sunflower seeds.",
            "Limit raw cruciferous vegetables like cabbage and broccoli; cook them thoroughly instead.",
            "Ensure adequate iodine through iodized salt or seaweed, but don't over-supplement without advice.",
        ],
    }

    # If specific condition recommendations exist, use them
    if health_condition in condition_recommendations:
        base_recs = condition_recommendations[health_condition]
        # Add a goal-specific tip as the third point modifier if needed
        return base_recs

    # Goal-based fallback (no specific health condition)
    if goal_lower in ["weight_loss", "weight loss"]:
        return [
            f"Consider adding a protein-rich snack like Greek yogurt or roasted chana to stay full longer after your {food_str}.",
            "Include plenty of vegetables in your next meal - they're low in calories but high in fiber and nutrients.",
            "Stay hydrated! Sometimes thirst is mistaken for hunger. Drink water before reaching for snacks.",
        ]
    elif goal_lower in ["muscle_gain", "muscle gain"]:
        return [
            f"Pair your {food_str} with a protein source like grilled chicken, paneer, or a protein shake to support muscle growth.",
            "Add complex carbs like brown rice, roti, or sweet potato to your next meal for sustained energy.",
            "Don't forget healthy fats from nuts, seeds, or avocado to support hormone production.",
        ]
    elif goal_lower in ["endurance"]:
        return [
            f"Balance your {food_str} with complex carbs like oats or whole grains for sustained energy release.",
            "Include electrolyte-rich foods like banana or coconut water, especially if you're active.",
            "Plan small, frequent meals throughout the day to maintain energy levels.",
        ]
    else:  # maintenance or unknown
        return [
            f"Your {food_str} fits well in a balanced diet. Just watch portion sizes.",
            "Aim for a colorful plate with vegetables of different colors for diverse nutrients.",
            "Listen to your body's hunger cues and eat mindfully throughout the day.",
        ]
