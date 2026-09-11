"""Compare original and deployment inference in separate CPU processes."""
import argparse
import asyncio
import gc
from io import BytesIO
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import types

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


async def worker(mode, samples):
    import psutil
    process = psutil.Process()
    peak = [process.memory_info().rss]
    stop = threading.Event()
    def measure():
        while not stop.wait(0.02):
            peak[0] = max(peak[0], process.memory_info().rss)
    monitor = threading.Thread(target=measure, daemon=True)
    monitor.start()
    start = time.monotonic()
    from PIL import Image
    os.environ["YOLO_MODEL_PATH"] = "results_after_discontinuation/yolo11s_indian_food_best.pt"
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    if mode == "baseline":
        source = subprocess.check_output(["git", "show", "HEAD:backend/services/vision_service.py"], cwd=ROOT, text=True, encoding="utf-8")
        module = types.ModuleType("baseline_vision")
        module.__file__ = str(ROOT / "backend/services/vision_service.py")
        exec(compile(source, module.__file__, "exec"), module.__dict__)
        import torch
        torch.set_num_threads(1)
        service = module.VisionService()
        await service.initialize()
        service.model.overrides["device"] = "cpu"
        async def analyze(content):
            return service.analyze_image(content, conf=0.25, iou=0.45)
    else:
        from backend.services.inference_runtime import InferenceRuntime
        runtime = InferenceRuntime()
        analyze = runtime.analyze
    results = []
    for name in [*samples, "multidish", "blank"]:
        if name == "blank":
            buffer = BytesIO()
            Image.new("RGB", (640, 640), "white").save(buffer, format="PNG")
            content = buffer.getvalue()
        elif name == "multidish":
            buffer = BytesIO()
            combined = Image.new("RGB", (1280, 640), "white")
            for index, path in enumerate(samples[:2]):
                with Image.open(ROOT / path) as image:
                    combined.paste(image.convert("RGB").resize((640, 640)), (index * 640, 0))
            combined.save(buffer, format="PNG")
            content = buffer.getvalue()
        else:
            content = (ROOT / name).read_bytes()
        result = await analyze(content)
        results.append({"sample": name, "result": result})
    if mode != "baseline":
        from backend.services.inference_runtime import InvalidImage
        for invalid in (b"bad", b"\xff\xd8\xffbroken", b"\x89PNG\r\n\x1a\nbroken"):
            try:
                await runtime.analyze(invalid)
            except InvalidImage:
                pass
            else:
                raise AssertionError("Invalid image accepted after Ultralytics loaded")
        runtime.close()
    stop.set()
    monitor.join()
    print("REPORT:" + json.dumps({"seconds": round(time.monotonic() - start, 2), "peak_mib": round(peak[0] / 1024**2, 1), "results": results}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", choices=["baseline", "deployment"])
    parser.add_argument("samples", nargs="*")
    args = parser.parse_args()
    samples = args.samples or ["data/food_dataset/valid/images/valid2282-aloo_gobi.jpg", "data/food_dataset/valid/images/valid0027-rajma_curry.jpg"]
    if args.worker:
        asyncio.run(worker(args.worker, samples))
        return
    reports = {}
    for mode in ("baseline", "deployment"):
        completed = subprocess.run([sys.executable, __file__, "--worker", mode, *samples], cwd=ROOT,
                                   env={**os.environ, "PYTHONIOENCODING": "utf-8"}, capture_output=True, text=True, encoding="utf-8", timeout=120)
        if completed.returncode:
            raise RuntimeError(completed.stderr[-3000:] + completed.stdout[-1000:])
        reports[mode] = json.loads(next(line[7:] for line in completed.stdout.splitlines() if line.startswith("REPORT:")))
    reports["parity"] = reports["baseline"]["results"] == reports["deployment"]["results"]
    output = ROOT / ".deployment" / "inference-verification.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(reports, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({mode: {k: v for k, v in report.items() if k != "results"} for mode, report in reports.items() if isinstance(report, dict)}))
    print(f"Exact CPU parity: {reports['parity']}; report: {output}")
    if not reports["parity"]:
        raise SystemExit("Detection outputs changed")


if __name__ == "__main__":
    main()
