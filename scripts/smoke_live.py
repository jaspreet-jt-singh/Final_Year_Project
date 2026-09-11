"""Smoke-test a deployed site without printing secrets or recommendation text."""
import argparse
from io import BytesIO
import json
from pathlib import Path
import re
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
import time
import httpx
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--skip-inference", action="store_true")
    parser.add_argument("--invalid-only", action="store_true")
    parser.add_argument("--protected", action="store_true", help="Use the project's existing Vercel automation bypass privately")
    args = parser.parse_args()
    headers = {}
    if args.protected:
        host = httpx.URL(args.url).host
        if not host.startswith("food-recognition-nutrition-") or not host.endswith("-jaspreet-jt-singh.vercel.app"):
            raise SystemExit("Refusing to send project credentials to an unrelated hostname")
        completed = subprocess.run(["npx.cmd" if os.name == "nt" else "npx", "--yes", "vercel@latest", "api",
                                    "/v9/projects/food-recognition-nutrition", "--scope", "jaspreet-jt-singh"],
                                   capture_output=True, text=True, check=True)
        project = json.loads(completed.stdout)
        token = next(key for key, value in project["protectionBypass"].items() if value["scope"] == "automation-bypass")
        headers["x-vercel-protection-bypass"] = token
    with httpx.Client(base_url=args.url.rstrip("/"), headers=headers, timeout=120, follow_redirects=False) as client:
        if args.invalid_only:
            response = client.post("/api/analyze-food", files={"file": ("invalid.jpg", b"not-image", "image/jpeg")})
            print({"status": response.status_code, "body": response.text[:500]})
            return
        home = client.get("/")
        home.raise_for_status()
        assert "Know your plate." in home.text and "Meal journal" in home.text, "Homepage is not the exported app"
        assets = set(re.findall(r'(?:src|href)="([^\"]+\.js[^\"]*)"', home.text))
        for asset in assets:
            assert asset.startswith("/") and not asset.startswith("//")
            response = client.get(asset)
            response.raise_for_status()
            assert "localhost:8000" not in response.text
        health = client.get("/api/health")
        health.raise_for_status()
        report = {"homepage": home.status_code, "assets": len(assets), "health_before": health.json()}
        for path in ("/api", "/api/user/goals", "/api/user/health-conditions"):
            response = client.get(path)
            response.raise_for_status()
        response = client.post("/api/user/calculate-macros", json={"goal": "Maintenance", "target_calories": 2000})
        response.raise_for_status()
        assert response.json()["target_calories"] == 2000
        if not args.skip_inference:
            sample = ROOT / "data/food_dataset/valid/images/valid2282-aloo_gobi.jpg"
            started = time.monotonic()
            response = client.post("/api/analyze-food", files={"file": ("food.jpg", sample.read_bytes(), "image/jpeg")})
            response.raise_for_status()
            result = response.json()
            assert result["detections"]
            report["first_scan_seconds"] = round(time.monotonic() - started, 2)
            report["labels"] = [d["food_label"] for d in result["detections"]]
            report["dimensions"] = [result["img_width"], result["img_height"]]
            response = client.post("/api/recommendations", json={"detected_foods": result["detections"], "user_goal": "Maintenance", "health_condition": "none"})
            response.raise_for_status()
            assert len(response.json()["recommendations"]) == 3
            report["recommendation_source"] = response.json()["source"]
            assert report["recommendation_source"] == "groq", "Groq did not succeed on the release candidate"
            combined = Image.new("RGB", (1280, 640), "white")
            for index, path in enumerate((sample, ROOT / "data/food_dataset/valid/images/valid0027-rajma_curry.jpg")):
                with Image.open(path) as image:
                    combined.paste(image.convert("RGB").resize((640, 640)), (index * 640, 0))
            multi = BytesIO()
            combined.save(multi, format="JPEG", quality=90)
            response = client.post("/api/analyze-food", files={"file": ("multidish.jpg", multi.getvalue(), "image/jpeg")})
            response.raise_for_status()
            assert len(response.json()["detections"]) >= 2
            report["multidish_count"] = len(response.json()["detections"])
            rotated = BytesIO()
            exif = combined.getexif()
            exif[274] = 6
            combined.save(rotated, format="JPEG", quality=90, exif=exif)
            response = client.post("/api/analyze-food", files={"file": ("rotated.jpg", rotated.getvalue(), "image/jpeg")})
            response.raise_for_status()
            assert [response.json()["img_width"], response.json()["img_height"]] == [640, 1280]
            report["rotated_dimensions"] = [640, 1280]
            def scan():
                return client.post("/api/analyze-food", files={"file": ("food.jpg", sample.read_bytes(), "image/jpeg")})
            with ThreadPoolExecutor(max_workers=2) as pool:
                parallel = list(pool.map(lambda _: scan(), range(2)))
            report["concurrent_statuses"] = [r.status_code for r in parallel]
            assert all(r.status_code == 200 for r in parallel)
            buffer = BytesIO()
            Image.new("RGB", (640, 640), "white").save(buffer, format="PNG")
            response = client.post("/api/analyze-food", files={"file": ("blank.png", buffer.getvalue(), "image/png")})
            response.raise_for_status()
            assert response.json()["food_not_found"]
            response = client.post("/api/analyze-food", files={"file": ("invalid.jpg", b"not-image", "image/jpeg")})
            assert response.status_code == 400, f"Invalid upload returned {response.status_code}: {response.text[:300]}; completed checks: {report}"
            report["health_after"] = client.get("/api/health").json()
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
