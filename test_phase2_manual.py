#!/usr/bin/env python3
import os
from pathlib import Path

os.chdir(Path(__file__).parent)

print("=== Manual Phase 2 Test ===")

# Test 1: ImageOverlay component exists
print("\n1. Testing ImageOverlay component exists...")
overlay_path = Path("frontend/components/ImageOverlay.tsx")
if overlay_path.exists():
    print("✅ ImageOverlay component exists")
else:
    print("❌ ImageOverlay component not found")

# Test 2: ResultsPanel imports ImageOverlay
print("\n2. Testing ResultsPanel imports ImageOverlay...")
results_path = Path("frontend/components/ResultsPanel.tsx")
if results_path.exists():
    with open(results_path, 'r') as f:
        content = f.read()
    if "import ImageOverlay" in content:
        print("✅ ResultsPanel imports ImageOverlay")
    else:
        print("❌ ResultsPanel does not import ImageOverlay")
else:
    print("❌ ResultsPanel not found")

# Test 3: Page shows Phase 2
print("\n3. Testing page.tsx shows Phase 2...")
page_path = Path("frontend/app/page.tsx")
if page_path.exists():
    with open(page_path, 'r', encoding='utf-8') as f:
        content = f.read()
    if "Phase 2" in content:
        print("✅ Page shows Phase 2")
    else:
        print("❌ Page does not show Phase 2")
else:
    print("❌ page.tsx not found")

# Test 4: Scaling logic in ImageOverlay
print("\n4. Testing scaling logic...")
if overlay_path.exists():
    with open(overlay_path, 'r') as f:
        content = f.read()
    has_scale = "scaleX" in content and "scaleY" in content
    if has_scale:
        print("✅ Has scaling logic")
    else:
        print("❌ Missing scaling logic")

print("\n=== Test Complete ===")
