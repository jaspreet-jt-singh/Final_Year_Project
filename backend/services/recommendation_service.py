"""
AI Recommendation Service for dietary guidance based on scanned food and user goals.
"""

import os
import logging
from typing import Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()


class RecommendationService:
    """
    Service that generates AI-powered dietary recommendations based on
    detected food items and user goals.
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
    
    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY", "")
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    
    def calculate_macros(self, goal: str, target_calories: int) -> dict:
        """
        Calculate macro targets based on goal and calorie target.
        
        Args:
            goal: One of 'weight_loss', 'muscle_gain', 'maintenance', 'endurance'
            target_calories: Daily calorie target
            
        Returns:
            Dictionary with macro breakdown
        """
        goal_lower = goal.lower().replace(" ", "_")
        
        # Default to maintenance if goal not recognized
        macro_split = self.GOAL_MACRO_SPLITS.get(goal_lower, self.GOAL_MACRO_SPLITS["maintenance"])
        
        # Calculate grams (calories per gram: carbs=4, protein=4, fat=9)
        carbs_g = round((target_calories * macro_split["carbs_percent"] / 100) / 4)
        protein_g = round((target_calories * macro_split["protein_percent"] / 100) / 4)
        fat_g = round((target_calories * macro_split["fat_percent"] / 100) / 9)
        
        return {
            "goal": macro_split["name"],
            "goal_key": goal_lower,
            "target_calories": target_calories,
            "carbs_g": carbs_g,
            "protein_g": protein_g,
            "fat_g": fat_g,
            "carbs_percent": macro_split["carbs_percent"],
            "protein_percent": macro_split["protein_percent"],
            "fat_percent": macro_split["fat_percent"],
            "description": macro_split["description"]
        }
    
    def _build_prompt(self, detected_foods: list, user_goal: str) -> str:
        """
        Build the prompt for the LLM.
        
        Args:
            detected_foods: List of detected food items with nutrition info
            user_goal: User's dietary goal
            
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
        
        prompt = (
            f"The user just scanned the following food item(s) and their goal is '{user_goal}'. "
            f"\n\nScanned foods:\n{foods_str}"
            f"\n\nGive me exactly 3 simple bullet points of advice for what else they should eat today "
            f"to balance this meal out and stay on track with their goal. "
            f"Keep it realistic to Indian or global food options. "
            f"Be encouraging and practical. Do not include any markdown formatting, "
            f"just return the 3 bullet points with each on a new line starting with '- '."
        )
        
        return prompt
    
    async def get_recommendations(self, detected_foods: list, user_goal: str) -> dict:
        """
        Get AI-powered dietary recommendations.
        
        Args:
            detected_foods: List of detected food items
            user_goal: User's dietary goal
            
        Returns:
            Dictionary with recommendations
        """
        prompt = self._build_prompt(detected_foods, user_goal)
        
        # Try different LLM providers in order of preference
        recommendation = None
        
        # Try Groq first (fastest, free tier available)
        if self.groq_api_key:
            try:
                recommendation = await self._call_groq(prompt)
                if recommendation:
                    return {"recommendations": recommendation, "source": "groq"}
            except Exception as e:
                logger.warning(f"Groq failed: {e}, trying next provider")
        
        # Try OpenAI
        if self.openai_api_key:
            try:
                recommendation = await self._call_openai(prompt)
                if recommendation:
                    return {"recommendations": recommendation, "source": "openai"}
            except Exception as e:
                logger.warning(f"OpenAI failed: {e}, trying next provider")
        
        # Try Ollama (local)
        try:
            recommendation = await self._call_ollama(prompt)
            if recommendation:
                return {"recommendations": recommendation, "source": "ollama"}
        except Exception as e:
            logger.warning(f"Ollama failed: {e}")
        
        # Fallback to hardcoded recommendations
        return {
            "recommendations": self._get_fallback_recommendations(detected_foods, user_goal),
            "source": "fallback"
        }
    
    async def _call_groq(self, prompt: str) -> Optional[list]:
        """Call Groq API for recommendations."""
        try:
            from groq import Groq
            client = Groq(api_key=self.groq_api_key)
            
            response = client.chat.completions.create(
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
            )
            
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
        """Parse LLM response into a list of recommendations."""
        if not content:
            return []
        
        recommendations = []
        lines = content.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("- ") or line.startswith("* ") or line.startswith("• "):
                recommendations.append(line[2:])
            elif line and len(recommendations) < 3:
                recommendations.append(line)
        
        return recommendations[:3]  # Return max 3 recommendations
    
    def _get_fallback_recommendations(self, detected_foods: list, user_goal: str) -> list:
        """
        Fallback recommendations when LLM is not available.
        Provides generic but useful advice based on goal.
        """
        goal_lower = user_goal.lower().replace(" ", "_")
        
        # Get detected food names for context
        food_names = [f.get("display_name", f.get("food_label", "food")) for f in detected_foods]
        food_str = ", ".join(food_names[:2])  # Mention first 2 foods
        
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