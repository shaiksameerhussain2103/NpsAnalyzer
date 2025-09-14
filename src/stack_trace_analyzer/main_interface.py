#!/usr/bin/env python3
"""
Main Stack Trace Analysis Interface
===================================

Clean API that provides the exact functionality requested:
- Takes stack trace line + repository root path
- Returns structured File/Class/Method/Status output
- Handles dual mode: specific method OR full file/method list
- Integrates with caching system
"""

import os
import json
import logging
import sys
from typing import Dict, Any, Optional, List
from pathlib import Path

# Add the src directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stack_trace_analyzer.enhanced_extractor import EnhancedStackTraceAnalyzer
from stack_trace_analyzer.robust_analysis_system import analyze_stack_trace

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StackTraceAnalysisInterface:
    """
    Main interface for stack trace analysis with caching support
    """
    
    def __init__(self, cache_enabled: bool = True, use_robust_parser: bool = True):
        # Use the new robust analysis system by default
        if use_robust_parser:
            self.use_robust = True
            logger.info("Using robust stack trace analysis system")
        else:
            self.analyzer = EnhancedStackTraceAnalyzer()
            self.use_robust = False
            logger.info("Using legacy enhanced analyzer")
        
        self.cache_enabled = cache_enabled
        self.cache = {}  # Simple in-memory cache
        logger.info("Stack Trace Analysis Interface initialized")
    
    def analyze_stack_trace(self, stack_trace_line: str, repository_path: str) -> Dict[str, Any]:
        """
        Main analysis method that matches the exact requirements
        
        Args:
            stack_trace_line: Stack trace input (e.g., package.Class#method)
            repository_path: Root path of the repository to search
            
        Returns:
            Dict with structured format:
            {
                "file": "<relative_path>",
                "class": "<class_name>", 
                "method": "<method_name OR [list_of_methods]>",
                "status": "success/failure"
            }
        """
        
        # Cache key
        cache_key = f"{stack_trace_line}:{repository_path}"
        
        # Check cache first
        if self.cache_enabled and cache_key in self.cache:
            logger.info(f"Cache hit for: {stack_trace_line}")
            return self.cache[cache_key]
        
        try:
            # Use robust analysis system by default
            if self.use_robust:
                result = analyze_stack_trace(stack_trace_line, repository_path)
                
                # Convert to our expected format if needed
                if "line_range" in result:
                    result["line_range"] = result["line_range"]
                
            else:
                # Legacy enhanced analyzer fallback
                # Parse the stack trace
                package_path, class_name, method_name, parse_type = self.analyzer.parser.parse_enhanced(stack_trace_line)
                
                logger.info(f"Parsed - Package: {package_path}, Class: {class_name}, Method: {method_name}")
                
                # Handle parsing failure
                if parse_type == "no_match" or not class_name:
                    result = {
                        "file": "NOT_FOUND",
                        "class": "UNKNOWN",
                        "method": "NONE",
                        "status": "failure",
                        "error": f"Could not parse input: {stack_trace_line}"
                    }
                # Validate repository path
                elif not os.path.exists(repository_path):
                    result = {
                        "file": "NOT_FOUND",
                        "class": class_name,
                        "method": method_name or "NONE",
                        "status": "failure",
                        "error": f"Repository path does not exist: {repository_path}"
                    }
                else:
                    # Perform full analysis
                    enhanced_result = self.analyzer.analyze_enhanced(stack_trace_line, repository_path)
                    
                    # Convert to required format
                    result = self._format_output(enhanced_result, class_name, method_name)
            
            # Cache the result
            if self.cache_enabled:
                self.cache[cache_key] = result
                logger.info(f"Cached result for: {stack_trace_line}")
            
            return result
            
        except Exception as e:
            logger.error(f"Analysis failed for {stack_trace_line}: {e}")
            return {
                "file": "ERROR", 
                "class": "UNKNOWN",
                "method": "UNKNOWN",
                "status": "failure",
                "error": str(e)
            }
    
    def _format_output(self, enhanced_result: Dict[str, Any], class_name: str, method_name: Optional[str]) -> Dict[str, Any]:
        """
        Format enhanced result to match required output format
        """
        
        # Extract file path
        file_path = enhanced_result.get("file", "UNKNOWN")
        status = enhanced_result.get("status", "failure")
        
        # Base result structure
        result = {
            "file": file_path,
            "class": class_name,
            "status": status
        }
        
        # Handle method field based on extraction type
        extraction_type = enhanced_result.get("extraction_type", "unknown")
        
        if extraction_type == "specific_method":
            # Case A: Specific method found
            result["method"] = enhanced_result.get("method", method_name)
            
        elif extraction_type == "all_methods":
            # Case B: Method not found, return list of available methods
            if isinstance(enhanced_result.get("method"), list):
                result["method"] = enhanced_result["method"]
            else:
                result["method"] = []
                
        elif extraction_type == "full_file":
            # Case B: No method specified, full file returned
            result["method"] = "FULL_FILE"
            
        else:
            # Fallback
            result["method"] = method_name or "NONE"
        
        # Add error information if present
        if "error" in enhanced_result:
            result["error"] = enhanced_result["error"]
            
        return result
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        return {
            "cache_size": len(self.cache),
            "cache_enabled": self.cache_enabled
        }
    
    def clear_cache(self):
        """Clear the analysis cache"""
        self.cache.clear()
        logger.info("Cache cleared")

# Convenience functions for direct usage

def analyze_java_stack_trace(stack_trace_line: str, repository_path: str, use_robust: bool = True) -> Dict[str, Any]:
    """
    Convenience function for one-off analysis with robust parsing by default.
    
    Args:
        stack_trace_line: Stack trace input 
        repository_path: Repository root path
        use_robust: Use the new robust analysis system (default True)
        
    Returns:
        Structured analysis result
    """
    interface = StackTraceAnalysisInterface(use_robust_parser=use_robust)
    return interface.analyze_stack_trace(stack_trace_line, repository_path)

def demo_analysis():
    """
    Demo function showing the interface usage with robust parsing
    """
    print("Stack Trace Analysis Interface Demo")
    print("=" * 50)
    
    # Test cases with both systems for comparison
    test_cases = [
        {
            "trace": "chs.common.attr.AttributeValidatorFactoryDescriptionTest#testIsVersionShortDescriptionUniqueNoRevisionsUniqueDesc",
            "repo": r"C:\Users\Z0055DXU\mgnoscan\repo\iesd-25\datamodel_src\tests\src\chs",
            "description": "Original failing case - with method"
        },
        {
            "trace": "chs.common.attr.AttributeValidatorFactoryDescriptionTest", 
            "repo": r"C:\Users\Z0055DXU\mgnoscan\repo\iesd-25\datamodel_src\tests\src\chs",
            "description": "Class only - should not extract method='unknown'"
        }
    ]
    
    # Test with robust system (default)
    print("=== ROBUST ANALYSIS SYSTEM (NEW) ===")
    interface_robust = StackTraceAnalysisInterface(use_robust_parser=True)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest Case {i}: {test_case['description']}")
        print(f"Input: {test_case['trace']}")
        
        result = interface_robust.analyze_stack_trace(test_case["trace"], test_case["repo"])
        
        print("Robust Result:")
        print(f"  Status: {result.get('status', 'unknown')}")
        print(f"  Class: {result.get('class', 'N/A')}")
        print(f"  Method: {result.get('method', 'N/A')}")
        print(f"  File: {result.get('file', 'N/A')}")
        
        # Check for bug fixes
        if result.get('method') != 'unknown':
            print("  ✅ BUG FIX: No method='unknown' generated")
        else:
            print("  ❌ Bug present: method='unknown'")
        
        print("-" * 30)
    
    # Show cache stats
    print(f"\nCache Stats: {interface_robust.get_cache_stats()}")

if __name__ == "__main__":
    demo_analysis()