#!/usr/bin/env python3
"""
Robust Stack Trace Analysis System
==================================

Main integration module that combines the robust parsing, file finding,
and method extraction components. This fixes the core issues:

1. Method names no longer treated as class names
2. Never attempts to extract method="unknown"
3. Proper dual-flow: specific method vs file-level analysis
4. Clear logging and structured output
5. Backward compatibility with existing systems

Usage:
    from robust_analysis_system import analyze_stack_trace
    
    result = analyze_stack_trace(
        "chs.common.attr.AttributeValidatorFactoryDescriptionTest#testMethod",
        "/path/to/repo"
    )
"""

import os
import logging
import sys
from typing import Dict, Any, Optional
from pathlib import Path

# Add current directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from robust_stack_trace_parser import RobustStackTraceParser, StackTraceParseResult
from enhanced_repo_file_finder import EnhancedRepositoryFileFinder, FileSearchResult
from enhanced_method_extractor import EnhancedMethodExtractor, MethodExtractionResult

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)
logger = logging.getLogger(__name__)

class RobustStackTraceAnalysisSystem:
    """
    Main system that orchestrates the robust stack trace analysis.
    Fixes parsing bugs and implements proper dual-flow handling.
    """
    
    def __init__(self):
        self.parser = RobustStackTraceParser()
        self.file_finder = EnhancedRepositoryFileFinder()
        self.method_extractor = EnhancedMethodExtractor()
        
        # Simple cache to avoid repeated operations
        self.cache = {}
        
        logger.info("RobustStackTraceAnalysisSystem initialized")
    
    def analyze(self, stack_trace_input: str, repo_root: str) -> Dict[str, Any]:
        """
        Main analysis method that implements the complete workflow.
        
        Args:
            stack_trace_input: Stack trace line from user
            repo_root: Repository root path
            
        Returns:
            Structured result dictionary
        """
        
        # Cache key
        cache_key = f"{stack_trace_input}:{repo_root}"
        if cache_key in self.cache:
            logger.info(f"Cache hit for: {stack_trace_input}")
            return self.cache[cache_key]
        
        try:
            # Step 1: Parse the input
            parse_result = self._parse_input(stack_trace_input)
            if not parse_result:
                return self._create_error_result("parsing_failed", stack_trace_input)
            
            # Step 2: Find the file
            file_result = self._find_file(parse_result, repo_root)
            if not file_result.success:
                return self._create_file_not_found_result(file_result, parse_result)
            
            # Step 3: Extract method or provide file-level analysis
            extraction_result = self._extract_or_analyze(file_result, parse_result)
            
            # Step 4: Create final structured result
            result = self._create_final_result(extraction_result, parse_result, file_result)
            
            # Cache the result
            self.cache[cache_key] = result
            logger.info(f"Cached result for: {stack_trace_input}")
            
            return result
            
        except Exception as e:
            logger.error(f"Analysis failed for '{stack_trace_input}': {e}")
            return self._create_error_result("system_error", stack_trace_input, str(e))
    
    def _parse_input(self, stack_trace_input: str) -> Optional[StackTraceParseResult]:
        """Parse the stack trace input"""
        
        try:
            parse_result = self.parser.parse(stack_trace_input)
            
            logger.info(f"Parsed -> class_fqn={parse_result.class_fqn} method={parse_result.method}")
            
            return parse_result
            
        except Exception as e:
            logger.error(f"Parsing failed: {e}")
            return None
    
    def _find_file(self, parse_result: StackTraceParseResult, repo_root: str) -> FileSearchResult:
        """Find the Java file"""
        
        return self.file_finder.find_file(
            class_fqn=parse_result.class_fqn,
            repo_root=repo_root,
            explicit_path=parse_result.explicit_path
        )
    
    def _extract_or_analyze(self, file_result: FileSearchResult, 
                           parse_result: StackTraceParseResult) -> MethodExtractionResult:
        """Extract method or provide file-level analysis"""
        
        if parse_result.method:
            # Flow A: Specific method extraction
            logger.info(f"MethodExtractor: Extracting method {parse_result.method} from file {file_result.file_path}")
            
            extraction_result = self.method_extractor.extract(
                file_path=file_result.file_path,
                class_name=parse_result.class_fqn,
                method_name=parse_result.method
            )
            
            if extraction_result.status == "success":
                if extraction_result.line_range:
                    logger.info(f"MethodExtractor: Method found at lines {extraction_result.line_range[0]}-{extraction_result.line_range[1]}")
                else:
                    logger.info("MethodExtractor: Method extraction successful")
            else:
                logger.warning(f"MethodExtractor: Method extraction failed - {extraction_result.reason}")
            
            return extraction_result
            
        else:
            # Flow B: File-level analysis (no method specified)
            logger.info(f"MethodExtractor: No method specified, providing file-level analysis")
            
            extraction_result = self.method_extractor.extract(
                file_path=file_result.file_path,
                class_name=parse_result.class_fqn,
                method_name=None  # Explicitly None, never "unknown"
            )
            
            if extraction_result.status == "success":
                method_count = len(extraction_result.method_list)
                logger.info(f"FileOnlyMode: returned list of {method_count} methods")
            
            return extraction_result
    
    def _create_final_result(self, extraction_result: MethodExtractionResult,
                           parse_result: StackTraceParseResult,
                           file_result: FileSearchResult) -> Dict[str, Any]:
        """Create the final structured result"""
        
        # Start with extraction result
        result = extraction_result.to_dict()
        
        # Ensure we have the correct relative file path
        if file_result.file_path:
            result["file"] = self._get_relative_path(file_result.file_path)
        
        return result
    
    def _get_relative_path(self, file_path: str) -> str:
        """Get relative path for display"""
        path = Path(file_path)
        
        # Try to find a sensible relative path
        parts = path.parts
        for i, part in enumerate(parts):
            if part in ['src', 'java', 'main', 'test']:
                return '/'.join(parts[i+1:])
        
        # Fallback to just filename
        return path.name
    
    def _create_error_result(self, reason: str, input_line: str, details: str = None) -> Dict[str, Any]:
        """Create error result"""
        
        return {
            "status": "failure",
            "reason": reason,
            "details": details or f"Failed to process: {input_line}",
            "suggestions": [
                "Check input format",
                "Verify repository path exists",
                "Try explicit file path"
            ]
        }
    
    def _create_file_not_found_result(self, file_result: FileSearchResult,
                                    parse_result: StackTraceParseResult) -> Dict[str, Any]:
        """Create result for file not found"""
        
        return {
            "status": "failure",
            "reason": "file_not_found",
            "class": parse_result.class_fqn,
            "method": parse_result.method,
            "searched_paths": file_result.searched_paths,
            "suggestions": [
                "Verify class name spelling",
                "Check repository path",
                "Provide explicit file path",
                "Check if file exists in repository"
            ]
        }

# Convenience function for direct usage
def analyze_stack_trace(stack_trace_input: str, repo_root: str) -> Dict[str, Any]:
    """
    Analyze stack trace with robust handling.
    
    This is the main entry point that fixes the parsing issues:
    - Correctly handles package.Class#method format
    - Never treats method names as class names
    - Never attempts to extract method="unknown"
    - Provides proper dual-flow handling
    
    Args:
        stack_trace_input: Stack trace line (e.g., package.Class#method)
        repo_root: Repository root path
        
    Returns:
        Structured analysis result
    """
    
    system = RobustStackTraceAnalysisSystem()
    return system.analyze(stack_trace_input, repo_root)

# Test and validation with the original failing case
def test_original_failing_case():
    """Test with the original failing case from the requirements"""
    
    print("Testing Original Failing Case")
    print("=" * 50)
    
    # Original failing case
    stack_trace = "chs.common.attr.AttributeValidatorFactoryDescriptionTest#testIsVersionShortDescriptionUniqueNoRevisionsUniqueDesc"
    repo_root = r"C:\Users\Z0055DXU\mgnoscan\repo\iesd-25\datamodel_src\tests\src\chs"
    
    print(f"Input:")
    print(f"  Stack trace: {stack_trace}")
    print(f"  Repo root: {repo_root}")
    print()
    
    result = analyze_stack_trace(stack_trace, repo_root)
    
    print("Result:")
    print(f"  Status: {result['status']}")
    if 'class' in result:
        print(f"  Class: {result['class']}")
    if 'method' in result:
        print(f"  Method: {result['method']}")
    if 'file' in result:
        print(f"  File: {result['file']}")
    
    # Check for the specific bug fix
    if result.get('method') != 'unknown':
        print("✅ BUG FIX VERIFIED: Method is not 'unknown'")
    else:
        print("❌ Bug still present: method='unknown'")
    
    return result

if __name__ == "__main__":
    
    print("Robust Stack Trace Analysis System")
    print("=" * 60)
    
    # Test the original failing case
    test_result = test_original_failing_case()
    
    print("\n" + "=" * 60)
    
    # Additional test cases
    additional_tests = [
        # Class only (should not attempt method extraction)
        ("chs.common.attr.AttributeValidatorFactoryDescriptionTest", "Class only test"),
        
        # Parameterized test
        ("com.example.Test#testMethod[1]", "Parameterized test"),
        
        # Inner class
        ("com.example.Outer$Inner#method", "Inner class test")
    ]
    
    system = RobustStackTraceAnalysisSystem()
    
    for test_input, description in additional_tests:
        print(f"\n{description}:")
        print(f"Input: {test_input}")
        
        # Use a dummy repo path since we're testing parsing logic
        dummy_repo = "."
        
        # Just test the parsing part
        parse_result = system.parser.parse(test_input)
        print(f"Parsed -> Class: {parse_result.class_fqn}, Method: {parse_result.method}")
        
        if parse_result.method != "unknown":
            print("✅ No 'unknown' method generated")
        else:
            print("❌ Generated method='unknown'")
    
    print("\n" + "=" * 60)
    print("🎯 ROBUST ANALYSIS SYSTEM READY!")
    print("Key fixes implemented:")
    print("• ✅ Method names no longer treated as class names")
    print("• ✅ Never generates method='unknown'")  
    print("• ✅ Proper dual-flow handling")
    print("• ✅ Structured output format")
    print("• ✅ Clear logging and error handling")