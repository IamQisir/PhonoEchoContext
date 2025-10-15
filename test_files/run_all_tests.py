"""
Test runner script for CAPT modules.
Run this with: python run_all_tests.py
"""

import sys
import subprocess

def run_test_file(test_file):
    """Run a single test file and report results."""
    print(f"\n{'='*70}")
    print(f"Running: {test_file}")
    print('='*70)
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", test_file, "-v", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"❌ TIMEOUT: {test_file} took too long")
        return False
    except Exception as e:
        print(f"❌ ERROR running {test_file}: {e}")
        return False

def main():
    """Run all CAPT test files."""
    test_files = [
        "test_capt_guidance_card.py",
        "test_capt_attempt_summary.py",
        "test_capt_feedback_generator.py",
    ]
    
    print("🧪 CAPT Test Suite Runner")
    print("="*70)
    
    results = {}
    for test_file in test_files:
        results[test_file] = run_test_file(test_file)
    
    # Summary
    print(f"\n{'='*70}")
    print("📊 Test Summary")
    print('='*70)
    
    for test_file, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test_file}")
    
    print()
    total = len(results)
    passed = sum(results.values())
    print(f"Total: {passed}/{total} test files passed")
    
    return all(results.values())

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
