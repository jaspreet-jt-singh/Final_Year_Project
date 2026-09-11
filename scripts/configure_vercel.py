"""Upload only the selected backend secret via stdin, never command arguments."""
from pathlib import Path
import os
import subprocess
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
PROJECT = "food-recognition-nutrition"
SCOPE = "jaspreet-jt-singh"


def main():
    values = {
        "APP_ENV": "production",
        "VERCEL_SUPPORT_LARGE_FUNCTIONS": "1",
        "VERCEL_FASTAPI_STATIC_CDN": "1",
        "YOLO_MODEL_PATH": "results_after_discontinuation/yolo11s_indian_food_best.pt",
        "RATE_LIMIT_PER_MINUTE": "10",
        "GROQ_MODEL": "openai/gpt-oss-20b",
    }
    key = dotenv_values(ROOT / ".env").get("GROQ_API_KEY")
    if not key:
        raise SystemExit("GROQ_API_KEY is missing; configure it privately before publication")
    values["GROQ_API_KEY"] = key
    npx = "npx.cmd" if os.name == "nt" else "npx"
    for name, value in values.items():
        args = [npx, "--yes", "vercel@latest", "env", "add", name, "preview,production", "--yes",
                "--project", PROJECT, "--scope", SCOPE,
                "--sensitive" if name == "GROQ_API_KEY" else "--no-sensitive"]
        result = subprocess.run(args, input=value, text=True, capture_output=True, cwd=ROOT)
        # Never echo provider output on failure: only variable names/status.
        if result.returncode:
            raise SystemExit(f"Vercel could not configure {name}; exit {result.returncode}")
        print(f"Configured {name}", flush=True)


if __name__ == "__main__":
    main()
