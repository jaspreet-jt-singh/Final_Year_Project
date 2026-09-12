"""Create a minimal release tree; optionally commit it to vercel-live.

Never checks out or stages the research working tree. Release updates are normal
commits in an isolated repository and fast-forward updates to the local branch.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    "pyproject.toml", "uv.lock", ".python-version", "package.json", "vercel.json", ".vercelignore",
    "data/nutrition.db", "results_after_discontinuation/yolo11s_indian_food_best.pt",
    "scripts/build_frontend.py", "DEPLOYMENT.md",
    "frontend/package.json", "frontend/package-lock.json", "frontend/next.config.js",
    "frontend/tsconfig.json", "frontend/next-env.d.ts", "frontend/postcss.config.js",
    "frontend/tailwind.config.js", "frontend/tailwind.config.ts", "frontend/eslint.config.mjs",
]


def git(*args, cwd=ROOT):
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


def prepare(commit=False):
    if git("status", "--porcelain", "--untracked-files=normal"):
        raise RuntimeError("Commit or separately preserve all source changes before generating a release. A release must identify its exact clean source commit.")
    required = (
        "backend/domain/nutrition_policy.json",
        "frontend/lib/generated/api.d.ts",
        "frontend/lib/generated/nutritionPolicy.ts",
        "frontend/lib/generated/supportedFoods.ts",
    )
    if any(not (ROOT / name).is_file() for name in required):
        raise RuntimeError("Generate API contracts, nutrition policy, and supported-food catalog before preparing a release")
    parent = ROOT / ".deployment"
    parent.mkdir(exist_ok=True)
    destination = Path(tempfile.mkdtemp(prefix="release-", dir=parent))
    paths = {ROOT / name for name in FILES if (ROOT / name).is_file()}
    for folder in ("backend", "frontend/app", "frontend/components", "frontend/lib", "frontend/public"):
        for path in (ROOT / folder).rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix.lower() in {
                ".py", ".ts", ".tsx", ".css", ".json", ".svg", ".png", ".jpg", ".ico", ".woff2"
            }:
                paths.add(path)
    tracked = set(git("ls-files").splitlines())
    paths = {path for path in paths if path.relative_to(ROOT).as_posix() in tracked}
    if any(name not in tracked for name in (*required, "data/nutrition.db", "results_after_discontinuation/yolo11s_indian_food_best.pt")):
        raise RuntimeError("Required release assets must be tracked in the clean source commit")
    manifest = {"source_commit": git("rev-parse", "HEAD"), "files": {}}
    for source in sorted(paths):
        relative = source.relative_to(ROOT)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        manifest["files"][relative.as_posix()] = hashlib.sha256(source.read_bytes()).hexdigest()
    (destination / "release-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    total = sum(path.stat().st_size for path in destination.rglob("*") if path.is_file())
    if total >= 95_000_000:
        raise RuntimeError("Release source exceeds the conservative 95 MB upload limit")
    print(f"Release directory: {destination}\nSource size: {total / 1_000_000:.2f} MB")
    if commit:
        # Build the tree using a separate index/object database; no main/dev staging.
        git("init", "--quiet", str(destination))
        git("add", "--all", cwd=destination)
        tree = git("write-tree", cwd=destination)
        existing = subprocess.run(["git", "rev-parse", "--verify", "refs/heads/vercel-live"], cwd=ROOT, capture_output=True, text=True)
        parent_args = []
        if existing.returncode == 0:
            git("fetch", "--quiet", str(ROOT), "refs/heads/vercel-live", cwd=destination)
            parent_args = ["-p", existing.stdout.strip()]
        name = git("config", "user.name")
        email = git("config", "user.email")
        commit_id = git("-c", f"user.name={name}", "-c", f"user.email={email}", "commit-tree", tree,
                        *parent_args, "-m", f"Deploy food recognition from {manifest['source_commit'][:12]}", cwd=destination)
        git("update-ref", "refs/heads/vercel-live", commit_id, cwd=destination)
        git("symbolic-ref", "HEAD", "refs/heads/vercel-live", cwd=destination)
        git("fetch", "--quiet", str(destination), "refs/heads/vercel-live:refs/heads/vercel-live")
        print(f"Local vercel-live commit: {commit_id}")
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit", action="store_true", help="Create/update local vercel-live; does not push")
    prepare(parser.parse_args().commit)
