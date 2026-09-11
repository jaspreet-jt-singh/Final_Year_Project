"""Vercel build hook: export Next.js into CDN-served public files."""
from pathlib import Path
import os
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    npm = "npm.cmd" if os.name == "nt" else "npm"
    frontend = ROOT / "frontend"
    env = {**os.environ, "NEXT_TELEMETRY_DISABLED": "1"}
    subprocess.run([npm, "ci", "--include=dev"], cwd=frontend, env=env, check=True)
    subprocess.run([npm, "run", "build"], cwd=frontend, env=env, check=True)
    output = frontend / "out"
    if not (output / "index.html").is_file():
        raise RuntimeError("Next.js did not export index.html")
    shutil.copytree(output, ROOT / "public", dirs_exist_ok=True)
    print("Frontend exported to public/ for Vercel CDN")


if __name__ == "__main__":
    main()
