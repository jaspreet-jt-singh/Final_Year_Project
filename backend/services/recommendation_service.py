"""
AI Recommendation Service for dietary guidance based on scanned food and user goals.
Supports health conditions (diabetic, hypertension, etc.) for personalized advice.
"""

import os
import logging
import asyncio
from typing import Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()


class RecommendationService:
    """
    Service that generates AI-powered dietary recommendations based on
    detected food items, user goals, and health conditions.
    """
    
    # Hardcoded macro splits for different goals (Phase 2)
    GOAL_MACRO_SPLITS = {
        "weight_loss": {
            "name": "Weight Loss",
            "carbs_percent": 40,
            "protein_percent": 35,
            "fat_percent": 25,
            "description": "Higher protein, moderate carbs, lower fat for satiety and muscle preservation"
        },
        "muscle_gain": {
            "name": "Muscle Gain",
            "carbs_percent": 40,
            "protein_percent": 30,
            "fat_percent": 30,
            "description": "Balanced macros with adequate protein for muscle synthesis"
        },
        "maintenance": {
            "name": "Maintenance",
            "carbs_percent": 50,
            "protein_percent": 25,
            "fat_percent": 25,
            "description": "Balanced nutrition for maintaining current weight"
        },
        "endurance": {
            "name": "Endurance",
            "carbs_percent": 55,
            "protein_percent": 20,
            "fat_percent": 20,
            "description": "Higher carbs for sustained energy during endurance activities"
        }
    }

    # Health condition definitions with dietary guidance
    HEALTH_CONDITIONS = {
        "none": {
            "name": "None",
            "description": "No specific health conditions"
        },
        "diabetic": {
            "name": "Diabetic",
            "description": "Focus on low glycemic index foods, manage blood sugar spikes"
        },
        "hypertension": {
            "name": "Hypertension (High BP)",
            "description": "Low sodium diet, avoid processed foods, focus on potassium-rich foods"
        },
        "heart_disease": {
            "name": "Heart Disease",
            "description": "Low saturated fat, low cholesterol, increase omega-3 fatty acids"
        },
        "high_cholesterol": {
            "name": "High Cholesterol",
            "description": "Low saturated and trans fats, high fiber, plant-based proteins preferred"
        },
        "digestive_issues": {
            "name": "Digestive Issues",
            "description": "Easily digestible foods, avoid spicy/oily food, small frequent meals"
        },
        "kidney_disease": {
            "name": "Kidney Disease",
            "description": "Low potassium, low phosphorus, controlled protein intake"
        },
        "anemia": {
            "name": "Anemia",
            "description": "Iron-rich foods, vitamin C to aid absorption, avoid tea/coffee with meals"
        },
        "thyroid": {
            "name": "Thyroid Disorder",
            "description": "Iodine balance, selenium-rich foods, limit goitrogenic foods raw"
        }
    }

    # Macro modifiers per health condition (multipliers on top of goal splits)
    # e.g., diabetics reduce carbs %, heart patients reduce fat %
    CONDITION_MACRO_MODIFIERS = {
        "none":            {"carbs": 1.0, "protein": 1.0, "fat": 1.0},
        "diabetic":        {"carbs": 0.8, "protein": 1.15, "fat": 1.0},   # Lower carbs, higher protein
        "hypertension":    {"carbs": 1.0, "protein": 1.0, "fat": 0.9},    # Slightly lower fat
        "heart_disease":   {"carbs": 1.05, "protein": 1.0, "fat": 0.8},   # Lower fat, slightly higher carbs
        "high_cholesterol":{"carbs": 1.05, "protein": 1.1, "fat": 0.75},  # Much lower fat, higher fiber
        "digestive_issues":{"carbs": 1.0, "protein": 0.9, "fat": 0.85},   # Lower fat and protein
        "kidney_disease":  {"carbs": 1.15, "protein": 0.6, "fat": 1.0},   # Controlled protein
        "anemia":          {"carbs": 1.0, "protein": 1.1, "fat": 0.9},    # Higher protein for iron
        "thyroid":         {"carbs": 1.0, "protein": 1.05, "fat": 1.0},   # Slightly higher protein
    }
    
    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY", "")
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.ollama_host = os.getenv("OLLAMA_HOST", "")
        self.production = os.getenv("APP_ENV") == "production" or bool(os.getenv("VERCEL"))
    
    def _resolve_condition_key(self, condition: str) -> str:
        """
        Resolve a condition name (display name like 'Diabetic' or 'Hypertension (High BP)')
        to its internal key (like 'diabetic' or 'hypertension').
        Also handles keys that are already correct.
        """
        cleaned = condition.lower().replace(" ", "_").replace("(", "").replace(")", "")
        # Check if we already have a direct match
        if cleaned in self.HEALTH_CONDITIONS:
            return cleaned
        
        # Build reverse lookup from name -> key
        name_to_key = {v["name"]: k for k, v in self.HEALTH_CONDITIONS.items()}
        
        # Try exact name match
        if condition in name_to_key:
            return name_to_key[condition]
        
        # Try partial name match (e.g., "Diabetic" in "Hypertension" won't match, but handles typos)
        for name, key in name_to_key.items():
            if condition.lower() in name.lower() or name.lower() in condition.lower():
                return key
        
        return "none"
    
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
        goal_lower = goal.lower().replace(" ", "_")
        condition_key = self._resolve_condition_key(health_condition)
        
        # Default to maintenance if goal not recognized
        macro_split = self.GOAL_MACRO_SPLITS.get(goal_lower, self.GOAL_MACRO_SPLITS["maintenance"])
        
        # Get condition modifiers
        modifiers = self.CONDITION_MACRO_MODIFIERS.get(condition_key, self.CONDITION_MACRO_MODIFIERS["none"])
        
        # Apply health condition modifiers to macro percentages
        total_mod = (macro_split["carbs_percent"] * modifiers["carbs"] +
                     macro_split["protein_percent"] * modifiers["protein"] +
                     macro_split["fat_percent"] * modifiers["fat"])
        
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
            "health_condition_key": condition_key
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
    
    async def get_recommendations(self, detected_foods: list, user_goal: str, health_condition: str = "none") -> dict:
        """
        Get AI-powered dietary recommendations.
        
        Args:
            detected_foods: List of detected food items
            user_goal: User's dietary goal
            health_condition: User's health condition (e.g., 'Diabetic', 'Hypertension (High BP)')
            
        Returns:
            Dictionary with recommendations
        """
        condition_key = self._resolve_condition_key(health_condition)
        prompt = self._build_prompt(detected_foods, user_goal, condition_key)
        
        # Try different LLM providers in order of preference
        recommendation = None
        
        # Try Groq first (fastest, free tier available)
        if self.groq_api_key:
            try:
                recommendation = await self._call_groq(prompt)
                if recommendation:
                    return {"recommendations": recommendation, "source": "groq", "health_condition": condition_key}
            except Exception as e:
                logger.warning(f"Groq failed: {e}, trying next provider")
        
        # Try OpenAI
        if self.openai_api_key and not self.production:
            try:
                recommendation = await self._call_openai(prompt)
                if recommendation:
                    return {"recommendations": recommendation, "source": "openai", "health_condition": condition_key}
            except Exception as e:
                logger.warning(f"OpenAI failed: {e}, trying next provider")
        
        # Try Ollama (local)
        try:
            recommendation = await self._call_ollama(prompt) if self.ollama_host and not self.production else None
            if recommendation:
                return {"recommendations": recommendation, "source": "ollama", "health_condition": condition_key}
        except Exception as e:
            logger.warning(f"Ollama failed: {e}")
        
        # Fallback to hardcoded recommendations
        return {
            "recommendations": self._get_fallback_recommendations(detected_foods, user_goal, condition_key),
            "source": "fallback",
            "health_condition": condition_key
        }
    
    async def _call_groq(self, prompt: str) -> Optional[list]:
        """Call Groq API for recommendations."""
        try:
            from groq import AsyncGroq
            client = AsyncGroq(api_key=self.groq_api_key, timeout=20.0, max_retries=0)
            
            async with client:
                response = await asyncio.wait_for(client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful nutrition advisor. Provide practical, encouraging dietary advice. Return exactly 3 bullet points."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                    max_tokens=300
                ), timeout=20.0)
            
            content = response.choices[0].message.content.strip()
            return self._parse_recommendations(content)
        except ImportError:
            logger.warning("Groq package not installed")
            return None
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            return None
    
    async def _call_openai(self, prompt: str) -> Optional[list]:
        """Call OpenAI API for recommendations."""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.openai_api_key)
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful nutrition advisor. Provide practical, encouraging dietary advice. Return exactly 3 bullet points."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=300
            )
            
            content = response.choices[0].message.content.strip()
            return self._parse_recommendations(content)
        except ImportError:
            logger.warning("OpenAI package not installed")
            return None
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return None
    
    async def _call_ollama(self, prompt: str) -> Optional[list]:
        """Call local Ollama for recommendations."""
        try:
            import requests
            
            response = requests.post(
                f"{self.ollama_host}/api/generate",
                json={
                    "model": "llama2",
                    "prompt": prompt,
                    "stream": False
                },
                timeout=60
            )
            
            if response.status_code == 200:
                content = response.json().get("response", "").strip()
                return self._parse_recommendations(content)
        except ImportError:
            logger.warning("Requests package not installed")
            return None
        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            return None
        
        return None
    
    def _parse_recommendations(self, content: str) -> list:
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
    
    def _get_fallback_recommendations(self, detected_foods: list, user_goal: str, health_condition: str = "none") -> list:
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
                "Consider a small walk after meals — even 10 minutes helps with blood sugar management."
            ],
            "hypertension": [
                f"Your {food_str} is noted — avoid adding extra salt to your next meals. Use herbs, lemon, or masala instead.",
                "Include potassium-rich foods like banana, spinach, or yogurt in your diet today to help balance sodium.",
                "Stay away from packaged snacks and pickles for the rest of the day as they're high in hidden sodium."
            ],
            "heart_disease": [
                f"Balance your {food_str} with omega-3 rich foods like flaxseeds, walnuts, or fatty fish in your next meal.",
                "Choose cooking methods like steaming, boiling, or light sautéing over deep frying for heart health.",
                "Add a serving of leafy greens or colorful vegetables to increase heart-protective antioxidants."
            ],
            "high_cholesterol": [
                f"After {food_str}, focus on high-fiber foods like oats, barley, or apple for your next snack to help lower cholesterol.",
                "Include plant-based proteins like dal, chickpeas, or soy instead of red meat for the rest of the day.",
                "Add a tablespoon of soaked flaxseeds or nuts to your meals for healthy omega-3 fats."
            ],
            "digestive_issues": [
                f"Your {food_str} is fine — for your next meal, choose easily digestible foods like khichdi, curd rice, or clear soups.",
                "Avoid spicy, oily, or raw foods for the rest of the day. Stick to warm, cooked meals.",
                "Eat smaller, more frequent meals rather than large portions to ease digestion."
            ],
            "kidney_disease": [
                f"After {food_str}, keep your next meal low in potassium — avoid bananas, potatoes, and tomatoes in large amounts.",
                "Control protein portion sizes — a palm-sized serving of dal or paneer is sufficient per meal.",
                "Stay hydrated with plain water, but avoid packaged juices and coconut water which may be high in potassium."
            ],
            "anemia": [
                f"Pair your {food_str} with iron-rich foods like spinach, beetroot, or jaggery in your next meal.",
                "Include vitamin C sources like lemon, amla, or oranges with your meals to improve iron absorption.",
                "Avoid drinking tea or coffee within an hour of meals as tannins reduce iron absorption."
            ],
            "thyroid": [
                f"Your {food_str} is good — for your next meal include selenium-rich foods like brazil nuts, eggs, or sunflower seeds.",
                "Limit raw cruciferous vegetables like cabbage and broccoli; cook them thoroughly instead.",
                "Ensure adequate iodine through iodized salt or seaweed, but don't over-supplement without advice."
            ]
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
                "Stay hydrated! Sometimes thirst is mistaken for hunger. Drink water before reaching for snacks."
            ]
        elif goal_lower in ["muscle_gain", "muscle gain"]:
            return [
                f"Pair your {food_str} with a protein source like grilled chicken, paneer, or a protein shake to support muscle growth.",
                "Add complex carbs like brown rice, roti, or sweet potato to your next meal for sustained energy.",
                "Don't forget healthy fats from nuts, seeds, or avocado to support hormone production."
            ]
        elif goal_lower in ["endurance"]:
            return [
                f"Balance your {food_str} with complex carbs like oats or whole grains for sustained energy release.",
                "Include electrolyte-rich foods like banana or coconut water, especially if you're active.",
                "Plan small, frequent meals throughout the day to maintain energy levels."
            ]
        else:  # maintenance or unknown
            return [
                f"Your {food_str} fits well in a balanced diet. Just watch portion sizes.",
                "Aim for a colorful plate with vegetables of different colors for diverse nutrients.",
                "Listen to your body's hunger cues and eat mindfully throughout the day."
            ]
