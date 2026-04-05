#!/usr/bin/env python3
import os
from pathlib import Path

def test_phase2_manual():
    print("=== Phase 2 Final Test ===")
    
    # Change to project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    # Test 1: ImageOverlay component exists
    print("1. ImageOverlay exists:", Path("frontend/components/ImageOverlay.tsx").exists())
    
    # Test 2: ResultsPanel imports ImageOverlay
    results = Path("frontend/components/ResultsPanel.tsx")
    print("2. ResultsPanel imports ImageOverlay:", "import ImageOverlay" in results.read_text() if results.exists() else False)
    
    # Test 3: Page shows Phase 2
    page = Path("frontend/app/page.tsx")
    print("3. Page shows Phase 2:", "Phase 2" in page.read_text(encoding='utf-8') if page.exists() else False)
    
    # Test 4: Scaling logic in ImageOverlay
    overlay = Path("frontend/components/ImageOverlay.tsx")
    print("4. Scaling logic:", "scaleX" in overlay.read_text() and "scaleY" in overlay.read_text() if overlay.exists() else False)
    
    # Test 5: No redundant src directory
    print("5. No src dir:", not Path("frontend/src").exists())
    
    # Test 6: API includes bounding_box
    main = Path("backend/main.py")
    print("6. API bounding_box:", "bounding_box" in main.read_text() if main.exists() else False)
    
    print("=== Test Complete ===")

if __name__ == "__main__":
    test_phase2_manual()
