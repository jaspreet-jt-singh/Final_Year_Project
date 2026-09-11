"""Validated deployment configuration; secrets never appear in repr/log output."""

import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field, SecretStr

ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseModel):
    production: bool = False
    model_path: Path = ROOT / "results_after_discontinuation/yolo11s_indian_food_best.pt"
    database_path: Path = ROOT / "data/nutrition.db"
    analysis_rate: int = Field(default=10, ge=1, le=1000)
    recommendation_rate: int = Field(default=5, ge=1, le=1000)
    provider_capacity: int = Field(default=2, ge=1, le=2)
    provider_timeout: float = 20.0
    groq_key: SecretStr = SecretStr("")
    groq_model: str = "openai/gpt-oss-20b"
    openai_key: SecretStr = SecretStr("")
    ollama_host: str = ""

    @classmethod
    def from_environment(cls):
        load_dotenv(ROOT / ".env", override=False)
        return cls(
            production=bool(os.getenv("VERCEL")) or os.getenv("APP_ENV") == "production",
            model_path=ROOT / os.getenv("YOLO_MODEL_PATH", str(cls.model_fields["model_path"].default)),
            analysis_rate=os.getenv("RATE_LIMIT_PER_MINUTE", "10"),
            recommendation_rate=os.getenv("RECOMMENDATION_RATE_PER_MINUTE", "5"),
            groq_key=os.getenv("GROQ_API_KEY", ""),
            groq_model=os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
            openai_key=os.getenv("OPENAI_API_KEY", ""),
            ollama_host=os.getenv("OLLAMA_HOST", ""),
        )

    def configure_runtime(self):
        if self.production:
            for key in ("YOLO_CONFIG_DIR", "MPLCONFIGDIR", "XDG_CACHE_HOME"):
                os.environ.setdefault(key, str(Path(tempfile.gettempdir()) / "food-recognition" / key.lower()))
        for key in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
            os.environ.setdefault(key, "1")
        os.environ.setdefault("YOLO_AUTOINSTALL", "false")
