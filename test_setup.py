#!/usr/bin/env python3
"""
Simple test script to verify the setup is correct.
Run this after installing dependencies to check if everything is properly configured.
"""

import sys
from pathlib import Path

def test_imports():
    """Test if all required packages can be imported."""
    print("Testing imports...")
    
    try:
        import fastapi
        print("✓ FastAPI imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import FastAPI: {e}")
        return False
    
    try:
        import uvicorn
        print("✓ Uvicorn imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import Uvicorn: {e}")
        return False
    
    try:
        import openai
        print("✓ OpenAI imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import OpenAI: {e}")
        return False
    
    try:
        from app.core.config import settings
        print("✓ App config imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import app config: {e}")
        return False
    
    return True

def test_paths():
    """Test if required paths exist."""
    print("\nTesting paths...")
    
    frontend_template = Path(__file__).parent / "app" / "frontend_template"
    if frontend_template.exists():
        print(f"✓ Frontend template found at: {frontend_template}")
    else:
        print(f"✗ Frontend template not found at: {frontend_template}")
        return False
    
    # Check for required frontend files
    required_files = [
        "package.json",
        "vite.config.ts",
        "src/App.tsx",
        "src/main.tsx",
        "src/index.css"
    ]
    
    for file in required_files:
        file_path = frontend_template / file
        if file_path.exists():
            print(f"✓ {file} exists")
        else:
            print(f"✗ {file} missing")
            return False
    
    return True

def test_env():
    """Test if environment variables are configured."""
    print("\nTesting environment configuration...")
    
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    has_api_key = False
    
    if os.getenv("GEMINI_API_KEY"):
        print("✓ GEMINI_API_KEY is set")
        has_api_key = True
    else:
        print("⚠ GEMINI_API_KEY not set")
    
    if os.getenv("TOGETHER_API_KEY"):
        print("✓ TOGETHER_API_KEY is set")
        has_api_key = True
    else:
        print("⚠ TOGETHER_API_KEY not set")
    
    if os.getenv("OPENAI_API_KEY"):
        print("✓ OPENAI_API_KEY is set")
        has_api_key = True
    else:
        print("⚠ OPENAI_API_KEY not set")
    
    if not has_api_key:
        print("\n⚠ Warning: No API keys configured. Please create a .env file with at least one API key.")
        print("   See README.md for configuration details.")
    
    return True  # Don't fail on missing API keys, just warn

def main():
    """Run all tests."""
    print("=" * 60)
    print("LauzHack API Setup Test")
    print("=" * 60)
    
    tests = [
        ("Imports", test_imports),
        ("Paths", test_paths),
        ("Environment", test_env),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name} test failed with exception: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("Test Results:")
    print("=" * 60)
    
    all_passed = True
    for name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{name}: {status}")
        if not result:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n🎉 All tests passed! Your setup is ready.")
        print("\nNext steps:")
        print("1. Make sure you have a .env file with your API keys")
        print("2. Run: uvicorn app.main:app --reload")
        print("3. Visit: http://127.0.0.1:8000/docs")
        return 0
    else:
        print("\n❌ Some tests failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

