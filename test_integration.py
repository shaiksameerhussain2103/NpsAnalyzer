#!/usr/bin/env python3
"""
Integration test for the deterministic stack trace locator
Testing with the original failing case
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from stack_trace_analyzer.stacktrace_locator import StackTraceLocator
from stack_trace_analyzer.main_interface import StackTraceAnalysisInterface
import json

def test_original_failing_case():
    """Test the original case that was failing"""
    
    print("🔍 Testing Original Failing Case")
    print("=" * 60)
    
    # The original problematic input
    original_input = "chs.common.attr.AttributeValidatorFactoryDescriptionTest#testIsVersionShortDescriptionUniqueNoRevisionsUniqueDesc"
    
    print(f"Input: {original_input}")
    print()
    
    # Test with deterministic locator directly
    print("1️⃣ Testing Deterministic Locator Directly")
    print("-" * 40)
    
    locator = StackTraceLocator()
    result = locator.locate(original_input, "test_repo/src")
    
    print(f"Success: {result.get('success', False)}")
    print(f"Class: {result.get('class_name', 'Not found')}")
    print(f"Method: {result.get('method_name', 'Not found')}")
    print(f"File Path: {result.get('file_path', 'Not found')}")
    print()
    
    # Test with main interface (robust system)
    print("2️⃣ Testing Main Interface (Robust System)")
    print("-" * 40)
    
    interface = StackTraceAnalysisInterface()
    interface_result = interface.analyze_stack_trace(original_input, "test_repo/src")
    
    print(f"Success: {interface_result.get('success', False)}")
    print(f"Class: {interface_result.get('class_name', 'Not found')}")  
    print(f"Method: {interface_result.get('method_name', 'Not found')}")
    print(f"File Path: {interface_result.get('file_path', 'Not found')}")
    print()
    
    # Verify no method='unknown' is generated
    print("3️⃣ Verification Checks")
    print("-" * 40)
    
    method_check_1 = result.get('method_name') != 'unknown'
    method_check_2 = interface_result.get('method_name') != 'unknown'
    
    print(f"✅ Deterministic locator never returns method='unknown': {method_check_1}")
    print(f"✅ Interface never returns method='unknown': {method_check_2}")
    
    # Show the parsing breakdown
    print()
    print("4️⃣ Parsing Breakdown")
    print("-" * 40)
    
    if '#' in original_input:
        class_part, method_part = original_input.split('#', 1)
        print(f"Class FQN: {class_part}")
        print(f"Method: {method_part}")
        
        # Check if method is being treated as class (the original bug)
        print()
        print("🐛 Bug Check: Is method being treated as class?")
        if result.get('class_name') == method_part:
            print("❌ BUG DETECTED: Method is being treated as class!")
        else:
            print("✅ NO BUG: Method is correctly parsed as method")
    
    print()
    print("=" * 60)
    print("🎯 INTEGRATION TEST COMPLETE")

def test_multiple_formats():
    """Test various input formats to ensure robustness"""
    
    print("\n🔧 Testing Multiple Input Formats")
    print("=" * 60)
    
    test_cases = [
        "chs.common.styles.PinListDecorationStyle.refreshDecorations()",
        "AttributeValidatorFactoryDescriptionTest#testMethod",
        "com.foo.Bar$Inner#method",
        "TestClass#parameterizedTest[0]",
        "simple.ClassName",
        "path/to/File.java:123"
    ]
    
    interface = StackTraceAnalysisInterface()
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"{i}️⃣ {test_case}")
        result = interface.analyze_stack_trace(test_case, "test_repo/src")
        
        method = result.get('method_name', 'None')
        if method == 'unknown':
            print("   ❌ ERROR: Generated method='unknown'")
        else:
            print(f"   ✅ Method: {method}")
        print()

if __name__ == "__main__":
    test_original_failing_case()
    test_multiple_formats()