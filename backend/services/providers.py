"""Async provider adapters. Local alternatives are never constructed in production."""

import asyncio

from backend.domain.recommendations import parse_recommendations


class GroqProvider:
    name = "groq"

    def __init__(self, settings):
        from groq import AsyncGroq

        self.client = AsyncGroq(
            api_key=settings.groq_key.get_secret_value(), timeout=settings.provider_timeout, max_retries=0
        )
        self.model = settings.groq_model
        self.timeout = settings.provider_timeout

    async def recommend(self, prompt):
        response = await asyncio.wait_for(
            self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful nutrition advisor. Provide practical, encouraging dietary advice. Return exactly 3 bullet points.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                reasoning_effort="low",
                max_completion_tokens=1024,
            ),
            timeout=self.timeout,
        )
        return parse_recommendations(response.choices[0].message.content or "")

    async def close(self):
        await self.client.close()


class OpenAIProvider:
    name = "openai"

    def __init__(self, settings):
        from openai import AsyncOpenAI

        self.client = AsyncOpenAI(api_key=settings.openai_key.get_secret_value(), timeout=20, max_retries=0)

    async def recommend(self, prompt):
        response = await asyncio.wait_for(
            self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful nutrition advisor. Provide practical, encouraging dietary advice. Return exactly 3 bullet points.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=300,
            ),
            timeout=20,
        )
        return parse_recommendations(response.choices[0].message.content or "")

    async def close(self):
        await self.client.close()


class OllamaProvider:
    name = "ollama"

    def __init__(self, settings):
        import httpx

        self.client = httpx.AsyncClient(base_url=settings.ollama_host, timeout=20)

    async def recommend(self, prompt):
        response = await asyncio.wait_for(
            self.client.post("/api/generate", json={"model": "llama2", "prompt": prompt, "stream": False}), timeout=20
        )
        response.raise_for_status()
        return parse_recommendations(response.json().get("response", ""))

    async def close(self):
        await self.client.aclose()
