#!/usr/bin/env python3
"""
Phase 2 Test: Detection Overlay MVP
Validates that all Phase 2 requirements are met
"""

import os
import sqlite3
from pathlib import Path

def test_phase2():
    print("=== Phase 2 Test: Detection Overlay MVP ===")
    
    # Change to project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Frontend structure with app/ directory
    tests_total += 1
    print("\n1. Testing frontend structure...")
    try:
        app_dir = Path("frontend/app")
        components_dir = Path("frontend/components")
        
        if app_dir.exists() and components_dir.exists():
            print("✅ Frontend has correct app/ and components/ structure")
            tests_passed += 1
        else:
            missing = []
            if not app_dir.exists():
                missing.append("frontend/app")
            if not components_dir.exists():
                missing.append("frontend/components")
            print(f"❌ Missing frontend directories: {missing}")
            
    except Exception as e:
        print(f"❌ Error checking frontend structure: {e}")
    
    # Test 2: ImageOverlay component exists
    tests_total += 1
    print("\n2. Testing ImageOverlay component exists...")
    try:
        overlay_component = Path("frontend/components/ImageOverlay.tsx")
        if overlay_component.exists():
            print("✅ ImageOverlay component exists")
            tests_passed += 1
        else:
            print("❌ ImageOverlay component not found")
            
    except Exception as e:
        print(f"❌ Error checking ImageOverlay: {e}")
    
    # Test 3: ResultsPanel uses ImageOverlay
    tests_total += 1
    print("\n3. Testing ResultsPanel uses ImageOverlay...")
    try:
        results_panel = Path("frontend/components/ResultsPanel.tsx")
        if results_panel.exists():
            with open(results_panel, 'r') as f:
                content = f.read()
            
            if "import ImageOverlay" in content and "ImageOverlay" in content:
                print("✅ ResultsPanel imports and uses ImageOverlay")
                tests_passed += 1
            else:
                print("❌ ResultsPanel does not properly use ImageOverlay")
        else:
            print("❌ ResultsPanel component not found")
            
    except Exception as e:
        print(f"❌ Error checking ResultsPanel: {e}")
    
    # Test 4: Page.tsx shows Phase 2 badge
    tests_total += 1
    print("\n4. Testing page.tsx shows Phase 2...")
    try:
        page_file = Path("frontend/app/page.tsx")
        if page_file.exists():
            with open(page_file, 'r') as f:
                content = f.read()
            
            if "Phase 2" in content:
                print("✅ Page shows Phase 2 badge")
                tests_passed += 1
            else:
                print("❌ Page does not show Phase 2 badge")
        else:
            print("❌ page.tsx not found")
            
    except Exception as e:
        print(f"❌ Error checking page.tsx: {e}")
    
    # Test 5: Bounding box scaling logic in ImageOverlay
    tests_total += 1
    print("\n5. Testing bounding box scaling logic...")
    try:
        overlay_component = Path("frontend/components/ImageOverlay.tsx")
        if overlay_component.exists():
            with open(overlay_component, 'r') as f:
                content = f.read()
            
            # Check for scaling logic
            has_scale_x = "scaleX" in content
            has_scale_y = "scaleY" in content
            has_canvas_drawing = "strokeRect" in content
            
            if has_scale_x and has_scale_y and has_canvas_drawing:
                print("✅ ImageOverlay has proper scaling and drawing logic")
                tests_passed += 1
            else:
                missing = []
                if not has_scale_x:
                    missing.append("scaleX")
                if not has_scale_y:
                    missing.append("scaleY")
                if not has_canvas_drawing:
                    missing.append("canvas drawing")
                print(f"❌ Missing scaling logic: {missing}")
        else:
            print("❌ ImageOverlay component not found")
            
    except Exception as e:
        print(f"❌ Error checking ImageOverlay scaling: {e}")
    
    # Test 6: No redundant frontend/src directory
    tests_total += 1
    print("\n6. Testing no redundant frontend/src directory...")
    try:
        src_dir = Path("frontend/src")
        if not src_dir.exists():
            print("✅ No redundant frontend/src directory")
            tests_passed += 1
        else:
            print("❌ Redundant frontend/src directory exists")
            
    except Exception as e:
        print(f"❌ Error checking for redundant src directory: {e}")
    
    # Test 7: Backend still returns bounding_box in API
    tests_total += 1
    print("\n7. Testing API returns bounding_box...")
    try:
        main_py = Path("backend/main.py")
        if main_py.exists():
            with open(main_py, 'r') as f:
                content = f.read()
            
            if "bounding_box" in content:
                print("✅ API includes bounding_box in response")
                tests_passed += 1
            else:
                print("❌ API does not include bounding_box")
        else:
            print("❌ backend/main.py not found")
            
    except Exception as e:
        print(f"❌ Error checking API response: {e}")
    
    # Summary
    print(f"\n=== Phase 2 Test Summary ===")
    print(f"Tests passed: {tests_passed}/{tests_total}")
    
    if tests_passed == tests_total:
        print("🎉 All Phase 2 tests PASSED!")
        print("\n📋 Phase 2 Requirements Met:")
        print("✅ Detection overlay with bounding boxes")
        print("✅ Proper canvas scaling")
        print("✅ Clean frontend structure")
        print("✅ No redundant directories")
        print("✅ API supports overlay data")
        print("\n🚀 Ready to start servers:")
        print("   Backend: cd backend; uvicorn main:app --host 0.0.0.0 --port 8000 --reload")
        print("   Frontend: cd frontend; npm run dev")
        return True
    else:
        print("❌ Some Phase 2 tests FAILED!")
        return False

if __name__ == "__main__":
    success = test_phase2()
    exit(0 if success else 1)
