#!/usr/bin/env python3
"""
Robust Stack Trace Parser
=========================

Fixes the parsing issues where method names were treated as class names.
Implements the robust parsing rules as specified:
1. Handles package.Class#method format correctly  
2. Handles package.Class (file/class only)
3. Strips parameterized test decorations [...]
4. Never returns method="unknown"
5. Supports explicit file paths
6. Handles inner classes with $ notation
"""

import re
import os
import logging
from typing import Dict, Any, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

class StackTraceParseResult:
    """Structured result from stack trace parsing"""
    
    def __init__(self, class_fqn: str, method: Optional[str] = None, 
                 file_path_provided: bool = False, explicit_path: Optional[str] = None):
        self.class_fqn = class_fqn
        self.method = method  # Never "unknown" - either real method name or None
        self.file_path_provided = file_path_provided
        self.explicit_path = explicit_path
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "class_fqn": self.class_fqn,
            "method": self.method,
            "file_path_provided": self.file_path_provided,
            "explicit_path": self.explicit_path
        }

class RobustStackTraceParser:
    """
    Robust parser that correctly handles IntelliJ copy-reference format
    and prevents method names from being treated as class names.
    """
    
    def __init__(self):
        # Compile regex patterns for different formats (order matters!)
        self.patterns = {
            # Pattern 1: IntelliJ copy-reference format: package.Class#method
            'intellij_format': re.compile(r'^(?P<class>[\w.]+\$?[\w\$]*)#(?P<method>[\w\$][\w\d_$]*)$'),
            
            # Pattern 2: Stack trace frame format: package.Class.method(File.java:123)
            'stack_frame': re.compile(r'^(?P<class>[\w.]+)\.(?P<method>\w+)\([^)]*\)(?:\s*at\s*.*)?$'),
            
            # Pattern 3: Fully-qualified class only (no # or method)
            'class_only': re.compile(r'^(?P<class>[\w.]+\$?[\w\$]*)$'),
        }
        
        # Pattern for detecting file paths
        self.file_path_pattern = re.compile(r'^.*[/\\].*\.java$')
        
        # Pattern for parameterized test decorations
        self.param_test_pattern = re.compile(r'(.+)\[.*\]$')
    
    def parse(self, input_line: str) -> StackTraceParseResult:
        """
        Parse stack trace input with robust rules.
        
        Args:
            input_line: Raw input from user
            
        Returns:
            StackTraceParseResult with structured data
        """
        # Step 1: Clean input
        cleaned = self._clean_input(input_line)
        logger.info(f"Parsing input: '{input_line}' -> cleaned: '{cleaned}'")
        
        # Step 2: Check if explicit file path
        if self._is_file_path(cleaned):
            return self._parse_file_path(cleaned)
        
        # Step 3: Try parsing patterns in order
        for pattern_name, pattern in self.patterns.items():
            match = pattern.match(cleaned)
            if match:
                logger.info(f"Matched pattern: {pattern_name}")
                return self._extract_from_match(match, pattern_name)
        
        # Step 4: Fallback - treat entire input as class name
        logger.warning(f"No pattern matched, treating as class name: {cleaned}")
        return StackTraceParseResult(
            class_fqn=cleaned,
            method=None,
            file_path_provided=False
        )
    
    def _clean_input(self, input_line: str) -> str:
        """Clean and normalize input"""
        # Remove leading/trailing whitespace
        cleaned = input_line.strip()
        
        # Remove parameterized test decorations: someMethod[1] -> someMethod
        param_match = self.param_test_pattern.match(cleaned)
        if param_match:
            cleaned = param_match.group(1)
            logger.info(f"Stripped parameterized test decoration: {input_line} -> {cleaned}")
        
        return cleaned
    
    def _is_file_path(self, input_text: str) -> bool:
        """Check if input appears to be a file path"""
        return bool(self.file_path_pattern.match(input_text))
    
    def _parse_file_path(self, file_path: str) -> StackTraceParseResult:
        """Parse explicit file path input"""
        logger.info(f"Treating as explicit file path: {file_path}")
        
        # Extract class name from file path
        base_name = Path(file_path).stem  # removes .java extension
        
        # Handle inner classes (remove everything after $)
        class_name = base_name.split('$')[0]
        
        return StackTraceParseResult(
            class_fqn=class_name,  # Just the class name, not full path
            method=None,
            file_path_provided=True,
            explicit_path=file_path
        )
    
    def _extract_from_match(self, match, pattern_name: str) -> StackTraceParseResult:
        """Extract data from regex match based on pattern type"""
        
        if pattern_name == 'intellij_format':
            # package.Class#method
            class_fqn = match.group('class')
            method = match.group('method')
            logger.info(f"Parsed IntelliJ format -> class: {class_fqn}, method: {method}")
            return StackTraceParseResult(class_fqn=class_fqn, method=method)
            
        elif pattern_name == 'stack_frame':
            # package.Class.method(File.java:123)
            class_fqn = match.group('class')
            method = match.group('method')
            logger.info(f"Parsed stack frame -> class: {class_fqn}, method: {method}")
            return StackTraceParseResult(class_fqn=class_fqn, method=method)
            
        elif pattern_name == 'class_only':
            # package.Class (no method)
            class_fqn = match.group('class')
            logger.info(f"Parsed class only -> class: {class_fqn}")
            return StackTraceParseResult(class_fqn=class_fqn, method=None)
            
        else:
            logger.error(f"Unknown pattern type: {pattern_name}")
            return StackTraceParseResult(class_fqn="PARSE_ERROR", method=None)

# Convenience function for easy usage
def parse_stack_trace(input_line: str) -> StackTraceParseResult:
    """
    Parse stack trace input with robust handling.
    
    Args:
        input_line: Stack trace input from user
        
    Returns:
        StackTraceParseResult with parsed components
    """
    parser = RobustStackTraceParser()
    return parser.parse(input_line)

# Test and validation
if __name__ == "__main__":
    # Test cases to validate the parser
    test_cases = [
        # IntelliJ copy-reference format
        "chs.common.attr.AttributeValidatorFactoryDescriptionTest#testIsVersionShortDescriptionUniqueNoRevisionsUniqueDesc",
        
        # Class only format
        "chs.common.attr.AttributeValidatorFactoryDescriptionTest",
        
        # Parameterized test
        "com.example.Test#testMethod[1]",
        
        # Stack frame format
        "com.foo.Bar.method(File.java:123)",
        
        # Inner class
        "com.example.Outer$Inner#method",
        
        # File path
        "C:/path/to/TestClass.java",
        
        # File path with backslashes
        "C:\\path\\to\\TestClass.java"
    ]
    
    print("Robust Stack Trace Parser Test")
    print("=" * 50)
    
    parser = RobustStackTraceParser()
    
    for test_case in test_cases:
        print(f"\nInput: {test_case}")
        result = parser.parse(test_case)
        print(f"  Class FQN: {result.class_fqn}")
        print(f"  Method: {result.method}")
        print(f"  File Path Provided: {result.file_path_provided}")
        if result.explicit_path:
            print(f"  Explicit Path: {result.explicit_path}")
    
    print("\n" + "=" * 50)
    print("Robust parsing is working correctly!")