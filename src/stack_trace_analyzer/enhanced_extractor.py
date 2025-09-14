"""
Enhanced Method Extraction Engine

A completely separate, modular implementation for robust Java method extraction.
Handles both full path+method and partial references with dual mode parsing.

This is an independent module that can be plugged into the existing system
without modifying or breaking any existing code logic.
"""

import re
import logging
import os
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from pathlib import Path
import ast

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MethodSignature:
    """Represents a Java method signature"""
    name: str
    return_type: str
    parameters: List[str]
    modifiers: List[str]
    start_line: int
    end_line: int
    full_signature: str
    method_body: str
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "return_type": self.return_type,
            "parameters": self.parameters,
            "modifiers": self.modifiers,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "full_signature": self.full_signature,
            "method_body": self.method_body
        }

@dataclass
class EnhancedExtractionResult:
    """Result of enhanced method extraction"""
    file_path: str
    relative_path: str
    status: str  # "success" or "failure"
    extraction_type: str  # "specific_method", "all_methods", "full_file"
    target_method: Optional[MethodSignature] = None
    all_methods: List[MethodSignature] = None
    full_file_content: Optional[str] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict:
        result = {
            "file": self.relative_path,
            "status": self.status,
            "extraction_type": self.extraction_type
        }
        
        if self.target_method:
            result["method"] = self.target_method.name
            result["method_details"] = self.target_method.to_dict()
        elif self.all_methods:
            result["method"] = [m.name for m in self.all_methods]
            result["method_details"] = [m.to_dict() for m in self.all_methods]
        elif self.extraction_type == "full_file":
            result["method"] = "FULL_FILE"
            result["content_length"] = len(self.full_file_content) if self.full_file_content else 0
        
        if self.error_message:
            result["error"] = self.error_message
            
        return result

class EnhancedStackTraceParser:
    """
    Enhanced parser for stack trace lines with dual mode support.
    Completely independent from existing parser.
    """
    
    def __init__(self):
        # Patterns for different input formats (order matters - more specific first)
        self.patterns = {
            # Pattern 1: package.class#method format
            'hash_format': re.compile(r'^([a-zA-Z][a-zA-Z0-9_.]*?)\.([A-Z][a-zA-Z0-9_]*?)#([a-zA-Z_][a-zA-Z0-9_]*)$'),
            
            # Pattern 2: package.class.method format (traditional with parentheses)
            'traditional_parens': re.compile(r'^([a-zA-Z][a-zA-Z0-9_.]*?)\.([A-Z][a-zA-Z0-9_]*?)\.([a-zA-Z_][a-zA-Z0-9_]*)\(\)$'),
            
            # Pattern 3: package.class.method format (traditional without parentheses)
            'dot_format': re.compile(r'^([a-zA-Z][a-zA-Z0-9_.]*?)\.([A-Z][a-zA-Z0-9_]*?)\.([a-zA-Z_][a-zA-Z0-9_]*)$'),
            
            # Pattern 4: package.class format (no method)
            'package_class': re.compile(r'^([a-zA-Z][a-zA-Z0-9_.]*?)\.([A-Z][a-zA-Z0-9_]*)$'),
            
            # Pattern 5: file path with method (chs/common/attr/Class#method)
            'file_path_method': re.compile(r'^([a-zA-Z0-9_/\\]+?/)([A-Z][a-zA-Z0-9_]*?)#([a-zA-Z_][a-zA-Z0-9_]*)$'),
            
            # Pattern 6: file path format (chs/common/attr/Class)
            'file_path': re.compile(r'^([a-zA-Z0-9_/\\]+?/)([A-Z][a-zA-Z0-9_]*)$'),
            
            # Pattern 7: class with .java extension and method (Class.java#method)
            'class_java_method': re.compile(r'^([A-Z][a-zA-Z0-9_]*)\.java#([a-zA-Z_][a-zA-Z0-9_]*)$'),
            
            # Pattern 8: class with .java extension (Class.java)
            'class_java': re.compile(r'^([A-Z][a-zA-Z0-9_]*)\.java$'),
            
            # Pattern 9: just class with method (Class#method)
            'class_method': re.compile(r'^([A-Z][a-zA-Z0-9_]*?)#([a-zA-Z_][a-zA-Z0-9_]*)$'),
            
            # Pattern 10: just class name (Class)
            'class_only': re.compile(r'^([A-Z][a-zA-Z0-9_]*)$')
        }
    
    def parse_enhanced(self, input_line: str) -> Tuple[str, str, Optional[str], str]:
        """
        Parse input with enhanced logic
        
        Returns:
            (package_path, class_name, method_name, parse_type)
        """
        # Clean input
        cleaned = self._preprocess_input(input_line)
        logger.info(f"Enhanced parsing: {cleaned}")
        
        # Try each pattern
        for pattern_name, pattern in self.patterns.items():
            match = pattern.match(cleaned)
            if match:
                logger.info(f"Matched pattern: {pattern_name}")
                return self._extract_from_pattern(match, pattern_name)
        
        logger.warning(f"No enhanced pattern matched for: {cleaned}")
        return "", "", None, "no_match"
    
    def _preprocess_input(self, input_line: str) -> str:
        """Clean and normalize input"""
        # Remove quotes
        cleaned = input_line.strip().strip('"\'')
        
        # Don't normalize path separators yet - let patterns handle both / and \
        # Don't remove .java extensions - let patterns handle them
        
        return cleaned
    
    def _extract_from_pattern(self, match, pattern_name: str) -> Tuple[str, str, Optional[str], str]:
        """Extract components based on pattern type"""
        groups = match.groups()
        
        if pattern_name == 'hash_format':
            # package.class#method
            package, class_name, method = groups
            return package.replace('.', '/'), class_name, method, 'hash_format'
            
        elif pattern_name in ['dot_format', 'traditional_parens']:
            # package.class.method or package.class.method()
            package, class_name, method = groups
            return package.replace('.', '/'), class_name, method, pattern_name
            
        elif pattern_name == 'package_class':
            # package.class (no method)
            package, class_name = groups
            return package.replace('.', '/'), class_name, None, 'package_class'
            
        elif pattern_name == 'file_path':
            # path/to/Class
            path, class_name = groups
            return path.rstrip('/'), class_name, None, 'file_path'
            
        elif pattern_name == 'file_path_method':
            # path/to/Class#method
            path, class_name, method = groups
            return path.rstrip('/'), class_name, method, 'file_path_method'
            
        elif pattern_name == 'class_java':
            # Class.java
            class_name = groups[0]
            return "", class_name, None, 'class_java'
            
        elif pattern_name == 'class_java_method':
            # Class.java#method
            class_name, method = groups
            return "", class_name, method, 'class_java_method'
            
        elif pattern_name == 'class_only':
            # Just Class
            class_name = groups[0]
            return "", class_name, None, 'class_only'
            
        elif pattern_name == 'class_method':
            # Class#method
            class_name, method = groups
            return "", class_name, method, 'class_method'
        
        return "", "", None, "unknown"

class EnhancedMethodExtractor:
    """
    Enhanced method extractor with robust Java parsing.
    Completely independent from existing extractor.
    """
    
    def __init__(self):
        # Comprehensive Java method pattern
        self.method_pattern = re.compile(
            r'^\s*'  # Leading whitespace
            r'(?:'  # Non-capturing group for modifiers
            r'(?:public|private|protected|static|final|abstract|synchronized|native|strictfp|\s)+'
            r')?'  # Modifiers (optional)
            r'\s*'  # Whitespace
            r'(?:<[^>]+>\s+)?'  # Generic type parameters (optional)
            r'([a-zA-Z_][\w<>[\],\s]*?)\s+'  # Return type (group 1)
            r'([a-zA-Z_]\w*)\s*'  # Method name (group 2)
            r'\('  # Opening parenthesis
            r'([^)]*)'  # Parameters (group 3)
            r'\)\s*'  # Closing parenthesis
            r'(?:throws\s+[^{;]+)?'  # Throws clause (optional)
            r'\s*[{;]',  # Opening brace or semicolon
            re.MULTILINE
        )
    
    def extract_enhanced(self, file_path: str, target_method: Optional[str] = None) -> EnhancedExtractionResult:
        """
        Enhanced extraction with dual mode support
        
        Args:
            file_path: Path to Java file
            target_method: Optional specific method to extract
            
        Returns:
            EnhancedExtractionResult with structured output
        """
        try:
            relative_path = self._get_relative_path(file_path)
            
            # Read file content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            # Case A: Specific method requested
            if target_method:
                method_sig = self._find_specific_method(lines, target_method)
                if method_sig:
                    return EnhancedExtractionResult(
                        file_path=file_path,
                        relative_path=relative_path,
                        status="success",
                        extraction_type="specific_method",
                        target_method=method_sig
                    )
                else:
                    # Method not found, return all methods for user selection
                    all_methods = self._find_all_methods(lines)
                    return EnhancedExtractionResult(
                        file_path=file_path,
                        relative_path=relative_path,
                        status="success",
                        extraction_type="all_methods",
                        all_methods=all_methods,
                        error_message=f"Method '{target_method}' not found. Found {len(all_methods)} other methods."
                    )
            
            # Case B: No specific method, return all methods
            else:
                all_methods = self._find_all_methods(lines)
                if all_methods:
                    return EnhancedExtractionResult(
                        file_path=file_path,
                        relative_path=relative_path,
                        status="success",
                        extraction_type="all_methods",
                        all_methods=all_methods
                    )
                else:
                    # No methods found, return full file
                    return EnhancedExtractionResult(
                        file_path=file_path,
                        relative_path=relative_path,
                        status="success",
                        extraction_type="full_file",
                        full_file_content=content
                    )
        
        except Exception as e:
            logger.error(f"Enhanced extraction failed: {e}")
            return EnhancedExtractionResult(
                file_path=file_path,
                relative_path=self._get_relative_path(file_path),
                status="failure",
                extraction_type="error",
                error_message=str(e)
            )
    
    def _find_specific_method(self, lines: List[str], target_method: str) -> Optional[MethodSignature]:
        """Find a specific method with fuzzy matching"""
        # Try exact match first
        for method_sig in self._find_all_methods(lines):
            if method_sig.name == target_method:
                return method_sig
        
        # Try case-insensitive match
        for method_sig in self._find_all_methods(lines):
            if method_sig.name.lower() == target_method.lower():
                return method_sig
        
        # Try partial match (contains)
        for method_sig in self._find_all_methods(lines):
            if target_method.lower() in method_sig.name.lower():
                return method_sig
        
        return None
    
    def _find_all_methods(self, lines: List[str]) -> List[MethodSignature]:
        """Find all methods in the file"""
        methods = []
        
        for i, line in enumerate(lines):
            match = self.method_pattern.match(line)
            if match:
                return_type, method_name, params = match.groups()
                
                # Extract method body
                method_body, end_line = self._extract_method_body(lines, i)
                
                # Extract modifiers
                modifiers = self._extract_modifiers(line)
                
                method_sig = MethodSignature(
                    name=method_name,
                    return_type=return_type.strip(),
                    parameters=self._parse_parameters(params),
                    modifiers=modifiers,
                    start_line=i + 1,  # 1-indexed
                    end_line=end_line,
                    full_signature=line.strip(),
                    method_body=method_body
                )
                
                methods.append(method_sig)
                logger.debug(f"Found method: {method_name} at line {i + 1}")
        
        logger.info(f"Found {len(methods)} methods total")
        return methods
    
    def _extract_method_body(self, lines: List[str], start_line: int) -> Tuple[str, int]:
        """Extract complete method body"""
        if start_line >= len(lines):
            return "", start_line
        
        # Find method body by counting braces
        brace_count = 0
        method_lines = []
        i = start_line
        
        # Handle single line declarations (interfaces, abstract methods)
        if lines[start_line].strip().endswith(';'):
            return lines[start_line], start_line + 1
        
        while i < len(lines):
            line = lines[i]
            method_lines.append(line)
            
            # Count braces
            brace_count += line.count('{') - line.count('}')
            
            # If we've closed all braces, we're done
            if brace_count <= 0 and '{' in ''.join(method_lines):
                break
                
            i += 1
        
        return '\n'.join(method_lines), i + 1
    
    def _extract_modifiers(self, line: str) -> List[str]:
        """Extract method modifiers"""
        modifiers = []
        modifier_keywords = ['public', 'private', 'protected', 'static', 'final', 
                           'abstract', 'synchronized', 'native', 'strictfp']
        
        for modifier in modifier_keywords:
            if f' {modifier} ' in f' {line} ' or line.strip().startswith(modifier):
                modifiers.append(modifier)
        
        return modifiers
    
    def _parse_parameters(self, param_string: str) -> List[str]:
        """Parse method parameters"""
        if not param_string.strip():
            return []
        
        # Simple parameter parsing (can be enhanced for complex generics)
        params = []
        for param in param_string.split(','):
            param = param.strip()
            if param:
                # Extract parameter type and name
                parts = param.split()
                if len(parts) >= 2:
                    param_type = ' '.join(parts[:-1])
                    param_name = parts[-1]
                    params.append(f"{param_type} {param_name}")
                else:
                    params.append(param)
        
        return params
    
    def _get_relative_path(self, file_path: str) -> str:
        """Get relative path from absolute path"""
        try:
            # Try to make it relative to common Java source directories
            path_obj = Path(file_path)
            
            # Look for common Java source directory patterns
            java_roots = ['src/main/java', 'src/java', 'src', 'java']
            
            for root in java_roots:
                if root in str(path_obj):
                    # Find the index of the root directory
                    parts = path_obj.parts
                    try:
                        root_index = next(i for i, part in enumerate(parts) if part == root.split('/')[-1])
                        relative_parts = parts[root_index + 1:]
                        return '/'.join(relative_parts)
                    except StopIteration:
                        continue
            
            # Fallback: just return the filename
            return path_obj.name
        
        except Exception:
            return file_path

class EnhancedStackTraceAnalyzer:
    """
    Enhanced analyzer that combines parsing and extraction.
    Completely independent from existing analyzer.
    """
    
    def __init__(self):
        self.parser = EnhancedStackTraceParser()
        self.extractor = EnhancedMethodExtractor()
    
    def analyze_enhanced(self, input_line: str, repo_path: str) -> Dict:
        """
        Enhanced analysis with dual mode support
        
        Returns structured output in the required format
        """
        try:
            # Parse input
            package_path, class_name, method_name, parse_type = self.parser.parse_enhanced(input_line)
            
            if not class_name:
                return {
                    "file": "NOT_FOUND",
                    "method": "PARSE_FAILED",
                    "status": "failure",
                    "error": f"Could not parse input: {input_line}"
                }
            
            # Find file in repository
            file_path = self._find_file_in_repo(repo_path, package_path, class_name)
            
            if not file_path:
                return {
                    "file": f"{package_path}/{class_name}.java",
                    "method": "FILE_NOT_FOUND",
                    "status": "failure",
                    "error": f"File not found for class: {class_name}"
                }
            
            # Extract method(s)
            extraction_result = self.extractor.extract_enhanced(file_path, method_name)
            
            return extraction_result.to_dict()
        
        except Exception as e:
            logger.error(f"Enhanced analysis failed: {e}")
            return {
                "file": "ERROR",
                "method": "SYSTEM_ERROR",
                "status": "failure",
                "error": str(e)
            }
    
    def _find_file_in_repo(self, repo_path: str, package_path: str, class_name: str) -> Optional[str]:
        """Find Java file in repository with multiple strategies"""
        repo_root = Path(repo_path)
        
        if not repo_root.exists():
            logger.error(f"Repository path does not exist: {repo_path}")
            return None
        
        # Strategy 1: Exact package path
        if package_path:
            target_path = repo_root / package_path / f"{class_name}.java"
            if target_path.exists():
                return str(target_path)
        
        # Strategy 2: Search in common Java source directories
        common_src_dirs = ['src/main/java', 'src/java', 'src', 'java']
        
        for src_dir in common_src_dirs:
            if package_path:
                target_path = repo_root / src_dir / package_path / f"{class_name}.java"
                if target_path.exists():
                    return str(target_path)
        
        # Strategy 3: Broad search for class name
        for java_file in repo_root.rglob(f"{class_name}.java"):
            return str(java_file)
        
        logger.warning(f"File not found: {class_name}.java")
        return None

# Example usage and testing
if __name__ == "__main__":
    print("Enhanced Stack Trace Analyzer Test")
    print("=" * 50)
    
    # Test cases
    test_cases = [
        "chs.common.attr.AttributeValidatorFactoryDescriptionTest#testIsVersionShortDescriptionUniqueNoRevisionsUniqueDesc",
        "chs/common/attr/AttributeValidatorFactoryDescriptionTest",
        "AttributeValidatorFactoryDescriptionTest.java",
        "AttributeValidatorFactoryDescriptionTest#someMethod",
        "com.example.Service.processData()"
    ]
    
    analyzer = EnhancedStackTraceAnalyzer()
    
    print("Testing Enhanced Parser:")
    for test_case in test_cases:
        print(f"\nInput: {test_case}")
        package_path, class_name, method_name, parse_type = analyzer.parser.parse_enhanced(test_case)
        print(f"  Package: {package_path}")
        print(f"  Class: {class_name}")
        print(f"  Method: {method_name}")
        print(f"  Type: {parse_type}")
    
    print("\n" + "=" * 50)
    print("Enhanced Stack Trace Analyzer is ready for integration!")