"""Existing macro math and prompt rules, independent of provider IO."""

from .policy import GOALS, CONDITIONS, MODIFIERS, resolve_condition, resolve_goal


class NutritionRules:
    GOAL_MACRO_SPLITS = GOALS
    HEALTH_CONDITIONS = CONDITIONS
    CONDITION_MACRO_MODIFIERS = MODIFIERS
    _resolve_condition_key = staticmethod(resolve_condition)

    def calculate_macros(self, goal: str, target_calories: int, health_condition: str = "none") -> dict:
        """
        Calculate macro targets based on goal, calorie target, and health condition.

        Args:
            goal: One of 'weight_loss', 'muscle_gain', 'maintenance', 'endurance'
            target_calories: Daily calorie target
            health_condition: Health condition name or key from HEALTH_CONDITIONS

        Returns:
            Dictionary with macro breakdown
        """
        goal_lower = resolve_goal(goal)
        condition_key = self._resolve_condition_key(health_condition)

        # Default to maintenance if goal not recognized
        macro_split = self.GOAL_MACRO_SPLITS.get(goal_lower, self.GOAL_MACRO_SPLITS["maintenance"])

        # Get condition modifiers
        modifiers = self.CONDITION_MACRO_MODIFIERS.get(condition_key, self.CONDITION_MACRO_MODIFIERS["none"])

        # Apply health condition modifiers to macro percentages
        total_mod = (
            macro_split["carbs_percent"] * modifiers["carbs"]
            + macro_split["protein_percent"] * modifiers["protein"]
            + macro_split["fat_percent"] * modifiers["fat"]
        )

        carbs_pct = round((macro_split["carbs_percent"] * modifiers["carbs"]) / total_mod * 100)
        protein_pct = round((macro_split["protein_percent"] * modifiers["protein"]) / total_mod * 100)
        fat_pct = 100 - carbs_pct - protein_pct  # Ensure it sums to 100

        # Calculate grams (calories per gram: carbs=4, protein=4, fat=9)
        carbs_g = round((target_calories * carbs_pct / 100) / 4)
        protein_g = round((target_calories * protein_pct / 100) / 4)
        fat_g = round((target_calories * fat_pct / 100) / 9)

        # Build description with health condition context
        description = macro_split["description"]
        condition_info = self.HEALTH_CONDITIONS.get(condition_key)
        if condition_info and condition_key != "none":
            description += f" | Adapted for {condition_info['name']}: {condition_info['description']}"

        return {
            "goal": macro_split["name"],
            "goal_key": goal_lower,
            "target_calories": target_calories,
            "carbs_g": carbs_g,
            "protein_g": protein_g,
            "fat_g": fat_g,
            "carbs_percent": carbs_pct,
            "protein_percent": protein_pct,
            "fat_percent": fat_pct,
            "description": description,
            "health_condition": condition_info["name"] if condition_info else "None",
            "health_condition_key": condition_key,
        }

    def _build_prompt(self, detected_foods: list, user_goal: str, health_condition: str = "none") -> str:
        """
        Build the prompt for the LLM.

        Args:
            detected_foods: List of detected food items with nutrition info
            user_goal: User's dietary goal
            health_condition: User's health condition

        Returns:
            Prompt string for the LLM
        """
        food_descriptions = []
        for food in detected_foods:
            display_name = food.get("display_name", food.get("food_label", "Unknown"))
            calories = "Unknown"
            if food.get("macros"):
                calories = f"{round(food['macros'].get('calories', 0))} kcal"
            food_descriptions.append(f"- {display_name} ({calories})")

        foods_str = "\n".join(food_descriptions)

        # Get condition-specific dietary guidance
        condition_info = self.HEALTH_CONDITIONS.get(health_condition, self.HEALTH_CONDITIONS["none"])
        condition_guidance = ""
        if health_condition != "none":
            condition_guidance = (
                f"\n\nThe user has the following health condition: {condition_info['name']}. "
                f"Dietary consideration: {condition_info['description']}. "
                f"Please ensure your recommendations are compatible with this condition."
            )

        prompt = (
            f"The user just scanned the following food item(s) and their goal is '{user_goal}'."
            f"{condition_guidance}"
            f"\n\nScanned foods:\n{foods_str}"
            f"\n\nGive me exactly 3 simple bullet points of advice for what else they should eat today "
            f"to balance this meal out and stay on track with their goal and health needs. "
            f"Keep it realistic to Indian or global food options. "
            f"Be encouraging and practical. Do not include any markdown formatting, "
            f"just return the 3 bullet points with each on a new line starting with '- '."
        )

        return prompt
