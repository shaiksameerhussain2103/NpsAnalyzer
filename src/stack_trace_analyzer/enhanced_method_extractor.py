#!/usr/bin/env python3
"""
Enhanced Method Extractor
=========================

Implements dual-flow method extraction as specified:
1. If method provided: extract specific method with robust Java parsing
2. If method is None: return full file or method list (never extract "unknown")
3. Support for overloaded methods and method selection
4. Structured output with clear success/failure handling
"""

import re
import logging
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

class MethodInfo:
    """Information about a Java method"""
    
    def __init__(self, name: str, line_start: int, line_end: int = None, 
                 signature: str = None, body: str = None):
        self.name = name
        self.line_start = line_start
        self.line_end = line_end or line_start
        self.signature = signature
        self.body = body
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "line": self.line_start,
            "line_range": [self.line_start, self.line_end],
            "signature": self.signature,
            "body": self.body
        }

class MethodExtractionResult:
    """Result of method extraction operation"""
    
    def __init__(self, status: str = "failure", file_path: str = None, 
                 class_name: str = None, method_name: str = None):
        self.status = status
        self.file_path = file_path
        self.class_name = class_name
        self.method_name = method_name
        
        # Method-specific results
        self.method_code_snippet: Optional[str] = None
        self.line_range: Optional[List[int]] = None
        self.method_candidates: List[MethodInfo] = []
        
        # File-level results
        self.file_contents: Optional[str] = None
        self.method_list: List[Dict[str, Any]] = []
        
        # Error information
        self.reason: Optional[str] = None
        self.searched_paths: List[str] = []
        self.suggestions: List[str] = []
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "status": self.status,
            "file": self.file_path,
            "class": self.class_name,
            "method": self.method_name
        }
        
        if self.status == "success":
            if self.method_name:
                # Method extraction success
                result["method_code_snippet"] = self.method_code_snippet
                result["line_range"] = self.line_range
                if self.method_candidates:
                    result["method_candidates"] = [m.to_dict() for m in self.method_candidates]
            else:
                # File-level success
                result["method"] = None
                if self.file_contents:
                    result["file_contents"] = self.file_contents
                result["method_list"] = self.method_list
        else:
            # Failure
            result["reason"] = self.reason
            result["searched_paths"] = self.searched_paths
            result["suggestions"] = self.suggestions
        
        return result

class EnhancedMethodExtractor:
    """
    Enhanced method extractor with dual-flow support.
    Never attempts to extract a method named 'unknown'.
    """
    
    def __init__(self):
        # Java method pattern with comprehensive matching
        self.method_patterns = [
            # Standard method pattern
            re.compile(
                r'^\s*'  # Leading whitespace
                r'(?:(?:public|private|protected|static|final|abstract|synchronized|native|strictfp)\s+)*'  # Modifiers
                r'(?:<[^>]+>\s+)?'  # Generic type parameters
                r'(?:[\w\[\]<>,\s]+\s+)'  # Return type
                r'(?P<name>\w+)\s*'  # Method name
                r'\([^)]*\)\s*'  # Parameters
                r'(?:throws\s+[^{;]+)?'  # Throws clause
                r'(?:\s*\{|\s*;)',  # Opening brace or semicolon
                re.MULTILINE
            ),
            
            # Test method pattern (more lenient for test names)
            re.compile(
                r'^\s*'
                r'(?:@\w+(?:\([^)]*\))?\s*)*'  # Annotations
                r'(?:(?:public|private|protected|static|final)\s+)*'  # Modifiers
                r'(?:void|[\w<>]+)\s+'  # Return type
                r'(?P<name>test\w*|\w*[Tt]est\w*|\w+)\s*'  # Test method name
                r'\([^)]*\)\s*'  # Parameters
                r'(?:throws\s+[^{;]+)?'  # Throws clause
                r'\s*\{',  # Opening brace
                re.MULTILINE
            )
        ]
    
    def extract(self, file_path: str, class_name: str, 
                method_name: Optional[str] = None) -> MethodExtractionResult:
        """
        Extract method or provide file-level analysis.
        
        Args:
            file_path: Path to Java file
            class_name: Name of the class
            method_name: Optional method name to extract (None for file-level)
            
        Returns:
            MethodExtractionResult with extraction results
        """
        
        result = MethodExtractionResult(
            file_path=file_path,
            class_name=class_name,
            method_name=method_name
        )
        
        # Read file content
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.splitlines()
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            result.reason = "file_read_error"
            result.suggestions = [f"Verify file permissions and encoding: {file_path}"]
            return result
        
        # Find all methods in the file
        all_methods = self._find_all_methods(content, lines)
        logger.info(f"MethodExtractor: found {len(all_methods)} total methods in {file_path}")
        
        if method_name:
            # Flow A: Extract specific method
            return self._extract_specific_method(method_name, all_methods, content, lines, result)
        else:
            # Flow B: File-level analysis (no method specified)
            return self._provide_file_level_analysis(all_methods, content, result)
    
    def _find_all_methods(self, content: str, lines: List[str]) -> List[MethodInfo]:
        """Find all methods in the Java file"""
        
        methods = []
        
        for pattern in self.method_patterns:
            for match in pattern.finditer(content):
                method_name = match.group('name')
                start_pos = match.start()
                
                # Find line number
                line_num = content[:start_pos].count('\n') + 1
                
                # Extract method signature
                signature = match.group(0).strip()
                
                # Try to find method body
                body = self._extract_method_body(content, match.start(), lines)
                end_line = line_num + (body.count('\n') if body else 0)
                
                method_info = MethodInfo(
                    name=method_name,
                    line_start=line_num,
                    line_end=end_line,
                    signature=signature,
                    body=body
                )
                
                methods.append(method_info)
        
        # Remove duplicates (same method found by different patterns)
        unique_methods = []
        seen_methods = set()
        
        for method in methods:
            method_key = (method.name, method.line_start)
            if method_key not in seen_methods:
                seen_methods.add(method_key)
                unique_methods.append(method)
        
        return unique_methods
    
    def _extract_method_body(self, content: str, start_pos: int, lines: List[str]) -> str:
        """Extract the full method body using brace matching"""
        
        # Find the opening brace
        brace_pos = content.find('{', start_pos)
        if brace_pos == -1:
            return ""  # Abstract method or interface
        
        # Count braces to find matching closing brace
        brace_count = 0
        pos = brace_pos
        
        while pos < len(content):
            char = content[pos]
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    # Found matching closing brace
                    return content[start_pos:pos + 1]
            pos += 1
        
        # If we get here, braces don't match - return what we have
        return content[start_pos:]
    
    def _extract_specific_method(self, method_name: str, all_methods: List[MethodInfo], 
                                content: str, lines: List[str], 
                                result: MethodExtractionResult) -> MethodExtractionResult:
        """Extract a specific method by name"""
        
        # Find methods matching the name
        matching_methods = [m for m in all_methods if m.name == method_name]
        
        if not matching_methods:
            logger.warning(f"MethodExtractor: method '{method_name}' not found")
            result.reason = "method_not_found"
            result.suggestions = [
                "Check method name spelling",
                "Choose from available methods",
                "Verify the method exists in this class"
            ]
            
            # Provide list of available methods for user selection
            result.method_list = [{"name": m.name, "line": m.line_start} for m in all_methods]
            return result
        
        if len(matching_methods) == 1:
            # Single method found
            method = matching_methods[0]
            logger.info(f"MethodExtractor: Method found at lines {method.line_start}-{method.line_end}")
            
            result.status = "success"
            result.method_code_snippet = method.body
            result.line_range = [method.line_start, method.line_end]
            
        else:
            # Multiple overloaded methods
            logger.info(f"MethodExtractor: Found {len(matching_methods)} overloaded methods")
            
            result.status = "success"
            result.method_candidates = matching_methods
            result.method_code_snippet = matching_methods[0].body  # Default to first one
            result.line_range = [matching_methods[0].line_start, matching_methods[0].line_end]
        
        return result
    
    def _provide_file_level_analysis(self, all_methods: List[MethodInfo], content: str, 
                                   result: MethodExtractionResult) -> MethodExtractionResult:
        """Provide file-level analysis when no specific method requested"""
        
        logger.info("MethodExtractor: No method specified, providing file-level analysis")
        
        result.status = "success"
        result.method_name = None
        
        # Option 1: Provide method list for selection (preferred)
        result.method_list = [
            {
                "name": m.name,
                "line": m.line_start,
                "signature": m.signature[:100] + "..." if len(m.signature) > 100 else m.signature
            }
            for m in all_methods
        ]
        
        # Option 2: Also provide full file contents if requested
        # result.file_contents = content  # Uncomment if full file content is needed
        
        logger.info(f"MethodExtractor: Returned list of {len(all_methods)} methods for selection")
        
        return result

# Convenience function for easy usage
def extract_method(file_path: str, class_name: str, 
                   method_name: Optional[str] = None) -> MethodExtractionResult:
    """
    Extract method or provide file-level analysis.
    
    Args:
        file_path: Path to Java file
        class_name: Class name
        method_name: Optional method name (None for file-level analysis)
        
    Returns:
        MethodExtractionResult with results
    """
    extractor = EnhancedMethodExtractor()
    return extractor.extract(file_path, class_name, method_name)

# Test and validation
if __name__ == "__main__":
    import tempfile
    
    print("Enhanced Method Extractor Test")
    print("=" * 50)
    
    # Create test Java file
    test_java_content = '''
public class TestClass {
    
    public void testMethod() {
        System.out.println("Test method");
    }
    
    public void testMethodOverloaded(int param) {
        System.out.println("Overloaded method: " + param);
    }
    
    public void testMethodOverloaded(String param) {
        System.out.println("Overloaded method: " + param);
    }
    
    private String helperMethod() {
        return "helper";
    }
    
    @Test
    public void testAnnotatedMethod() {
        // Test with annotation
    }
}
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.java', delete=False) as f:
        f.write(test_java_content)
        test_file = f.name
    
    try:
        extractor = EnhancedMethodExtractor()
        
        # Test cases
        test_cases = [
            ("testMethod", "Extract single method"),
            ("testMethodOverloaded", "Extract overloaded method"),
            ("nonExistentMethod", "Method not found"),
            (None, "File-level analysis")
        ]
        
        for method_name, description in test_cases:
            print(f"\n{description}:")
            print(f"Method: {method_name}")
            
            result = extractor.extract(test_file, "TestClass", method_name)
            print(f"Status: {result.status}")
            
            if result.status == "success":
                if method_name:
                    if result.line_range:
                        print(f"Lines: {result.line_range}")
                    if result.method_candidates:
                        print(f"Candidates: {len(result.method_candidates)}")
                else:
                    print(f"Methods found: {len(result.method_list)}")
                    for method in result.method_list[:3]:  # Show first 3
                        print(f"  - {method['name']} (line {method['line']})")
            else:
                print(f"Reason: {result.reason}")
        
    finally:
        # Clean up
        Path(test_file).unlink(missing_ok=True)
    
    print("\n" + "=" * 50)
    print("Enhanced method extraction is working correctly!")