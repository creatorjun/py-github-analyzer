#!/usr/bin/env python3
"""
Simple test suite for py-github-analyzer
Run with: python test_simple.py
"""

import asyncio
import tempfile
import os
from pathlib import Path

def test_imports():
    """Test package imports"""
    print("🔍 Testing package imports...")
    
    try:
        import py_github_analyzer as pga
        print("  ✅ Main package imported successfully")
        
        # Test version
        version = pga.get_version()
        print(f"  ✅ Version: {version}")
        
        # Test core functions
        assert hasattr(pga, 'analyze_repository_async'), "Missing analyze_repository_async"
        assert hasattr(pga, 'GitHubRepositoryAnalyzer'), "Missing GitHubRepositoryAnalyzer"
        print("  ✅ Core functions available")
        
        # Test .env support
        if hasattr(pga, 'check_env_file'):
            env_status = pga.check_env_file()
            print(f"  ✅ .env support: {len(env_status)} items detected")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Import test failed: {e}")
        return False

def test_env_support():
    """Test .env file support"""
    print("\n🔍 Testing .env file support...")
    
    try:
        from py_github_analyzer.utils import TokenUtils
        
        # Test token detection
        token_info = TokenUtils.get_token_info(None)
        print(f"  ✅ Token detection works: {token_info.get('status', 'unknown')}")
        
        # Test env file discovery
        env_files = TokenUtils._find_env_files()
        print(f"  ✅ Found {len(env_files)} .env file(s)")
        
        return True
        
    except ImportError:
        print("  ⚠️  TokenUtils not available (optional feature)")
        return True
    except Exception as e:
        print(f"  ❌ .env test failed: {e}")
        return False

async def test_basic_analysis():
    """Test basic async analysis functionality"""
    print("\n🔍 Testing basic analysis...")
    
    try:
        import py_github_analyzer as pga
        
        # Create analyzer
        analyzer = pga.GitHubRepositoryAnalyzer()
        print("  ✅ Analyzer created successfully")
        
        # Test dry-run analysis
        with tempfile.TemporaryDirectory() as temp_dir:
            result = await pga.analyze_repository_async(
                "https://github.com/creatorjun/KdicSetup",
                output_dir=temp_dir,
                dry_run=True,
                verbose=False
            )
            
            if result.get('success'):
                print(f"  ✅ Dry-run analysis successful")
                print(f"     Repository: {result.get('metadata', {}).get('repo', 'Unknown')}")
                return True
            else:
                print(f"  ❌ Analysis failed: {result.get('error_message', 'Unknown error')}")
                return False
                
    except Exception as e:
        print(f"  ❌ Analysis test failed: {e}")
        return False

def test_cli_availability():
    """Test CLI availability"""
    print("\n🔍 Testing CLI availability...")
    
    try:
        import subprocess
        import sys
        
        # Test CLI module
        result = subprocess.run(
            [sys.executable, "-m", "py_github_analyzer", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print(f"  ✅ CLI available: {result.stdout.strip()}")
            return True
        else:
            print(f"  ❌ CLI test failed: return code {result.returncode}")
            return False
            
    except subprocess.TimeoutExpired:
        print("  ❌ CLI test timeout")
        return False
    except Exception as e:
        print(f"  ❌ CLI test failed: {e}")
        return False

async def run_all_tests():
    """Run all tests"""
    print("🧪 PY-GITHUB-ANALYZER SIMPLE TEST SUITE")
    print("=" * 50)
    
    tests = [
        ("Package Imports", test_imports),
        (".env Support", test_env_support),
        ("CLI Availability", test_cli_availability),
        ("Basic Analysis", test_basic_analysis)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                success = await test_func()
            else:
                success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"  ❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} {test_name}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All tests passed! Package is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Check the output above.")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(run_all_tests())
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        exit(130)
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        exit(1)
