#!/usr/bin/env python3
"""
Test runner script for the Azul game project.
Runs all unit tests and provides clear feedback.
"""

import subprocess
import sys
import os

def run_tests():
    """Run all unit tests and return success status."""
    print("🧪 Running Azul Game Unit Tests...")
    print("=" * 50)
    
    # Change to project directory
    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_dir)
    
    try:
        # Run pytest with verbose output
        result = subprocess.run([
            "python", "-m", "pytest", 
            "tests/", 
            "-v", 
            "--tb=short",  # Short traceback format
            "--color=yes"  # Colored output
        ], capture_output=False, text=True)
        
        if result.returncode == 0:
            print("\n✅ All tests passed!")
            return True
        else:
            print(f"\n❌ Tests failed with exit code {result.returncode}")
            return False
            
    except FileNotFoundError:
        print("❌ Error: pytest not found. Make sure you're in the virtual environment.")
        print("Run: source venv/bin/activate")
        return False
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False

def run_specific_test(test_pattern):
    """Run tests matching a specific pattern."""
    print(f"🧪 Running tests matching: {test_pattern}")
    print("=" * 50)
    
    try:
        result = subprocess.run([
            "python", "-m", "pytest", 
            "tests/", 
            "-v", 
            "-k", test_pattern,
            "--tb=short",
            "--color=yes"
        ], capture_output=False, text=True)
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Run specific test pattern
        test_pattern = sys.argv[1]
        success = run_specific_test(test_pattern)
    else:
        # Run all tests
        success = run_tests()
    
    sys.exit(0 if success else 1)
