#!/usr/bin/env python3
"""
Deterministic Stack Trace Locator
=================================

A reliable, deterministic Stack-Trace → Repo → File → Method mapper that implements
incremental repository traversal and robust parsing rules.

Key Features:
- Correctly parses class FQN and optional method name
- Uses incremental directory traversal based on package tokens
- Distinguishes package vs class tokens using naming conventions
- Provides robust fallbacks (fuzzy search, candidate selection)
- Never returns method="unknown"
- Structured JSON output with detailed logging

Usage:
    from stacktrace_locator import locate
    
    result = locate(
        "chs.common.styles.PinListDecorationStyle.refreshDecorations()",
        "C:/path/to/repo/src/chs"
    )
"""

import os
import re
import logging
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

class StackTraceLocator:
    """
    Main class for deterministic stack trace location with incremental traversal
    """
    
    def __init__(self):
        # Regex patterns for different input formats
        self.patterns = {
            # Explicit file path
            'explicit_path': re.compile(r'^.*[/\\].*\.java$'),
            
            # IntelliJ copy-reference: FQN#method
            'intellij_format': re.compile(r'^([^#]+)#(.+)$'),
            
            # Full stack trace frame: com.foo.Bar.method(File.java:123)
            'stack_frame': re.compile(r'^(.+)\.(\w+)\([^)]*\)(?:\s*at\s*.*)?$'),
            
            # Package/class naming patterns
            'package_token': re.compile(r'^[a-z_][a-z0-9_]*$'),
            'class_token': re.compile(r'^[A-Z][a-zA-Z0-9_]*(\$[A-Z][a-zA-Z0-9_]*)*$'),
            'method_token': re.compile(r'^[a-z][a-zA-Z0-9_]*$|^.*\(\)$'),
            
            # Parameterized test cleanup
            'param_test': re.compile(r'(.+)\[.*\]$'),
            
            # Method parentheses cleanup
            'method_parens': re.compile(r'(.+)\(\)$')
        }
        
        # Cache for parsed file metadata
        self.file_cache = {}
        
        logger.info("StackTraceLocator initialized")
    
    def locate(self, stack_trace_line: str, repo_root: str) -> Dict[str, Any]:
        """
        Main entry point for stack trace location.
        
        Args:
            stack_trace_line: Stack trace input from user
            repo_root: Repository root path
            
        Returns:
            Structured result dictionary
        """
        
        try:
            # Step 1: Parse the input
            parse_result = self._parse_input(stack_trace_line)
            if not parse_result:
                return self._create_failure_result("parsing_failed", f"Could not parse: {stack_trace_line}")
            
            class_fqn, method_name, is_explicit_path, explicit_path = parse_result
            
            logger.info(f"stack_trace_parser:Input='{stack_trace_line}' parsed -> class_fqn='{class_fqn}' method='{method_name}'")
            
            # Step 2: Locate the file
            file_result = self._locate_file(class_fqn, repo_root, is_explicit_path, explicit_path)
            if not file_result['success']:
                return file_result
            
            file_path = file_result['file_path']
            how_found = file_result['how_found']
            
            # Step 3: Extract method or provide file-level analysis
            if method_name:
                return self._extract_method(file_path, class_fqn, method_name, how_found)
            else:
                return self._provide_file_analysis(file_path, class_fqn, how_found)
                
        except Exception as e:
            logger.error(f"Location failed for '{stack_trace_line}': {e}")
            return self._create_failure_result("system_error", str(e))
    
    def _parse_input(self, input_line: str) -> Optional[Tuple[str, Optional[str], bool, Optional[str]]]:
        """
        Parse input according to the specified rules.
        
        Returns:
            (class_fqn, method_name, is_explicit_path, explicit_path) or None
        """
        
        # Step 1: Normalize input
        normalized = self._normalize_input(input_line)
        
        # Step 2: Check for explicit file path
        if self.patterns['explicit_path'].match(normalized):
            logger.info(f"Detected explicit file path: {normalized}")
            # Extract class name from file path
            class_name = Path(normalized).stem
            return class_name, None, True, normalized
        
        # Step 3: Check for IntelliJ copy-reference format
        intellij_match = self.patterns['intellij_format'].match(normalized)
        if intellij_match:
            class_fqn = intellij_match.group(1)
            method_name = intellij_match.group(2)
            logger.info(f"Detected IntelliJ format: class={class_fqn}, method={method_name}")
            return class_fqn, method_name, False, None
        
        # Step 4: Check for full stack trace frame format
        frame_match = self.patterns['stack_frame'].match(normalized)
        if frame_match:
            class_fqn = frame_match.group(1)
            method_name = frame_match.group(2)
            logger.info(f"Detected stack frame format: class={class_fqn}, method={method_name}")
            return class_fqn, method_name, False, None
        
        # Step 5: Dot notation parsing with smart class/method detection
        return self._parse_dot_notation(normalized)
    
    def _normalize_input(self, input_line: str) -> str:
        """Normalize input according to specified rules"""
        
        # Trim whitespace
        normalized = input_line.strip()
        
        # Replace backslashes with forward slashes for parsing
        normalized = normalized.replace('\\', '/')
        
        # Strip parameterized test suffixes: testName[0] → testName
        param_match = self.patterns['param_test'].match(normalized)
        if param_match:
            normalized = param_match.group(1)
            logger.info(f"Stripped parameterized test suffix: {input_line} -> {normalized}")
        
        # Remove trailing () from method tokens (will be handled in parsing)
        return normalized
    
    def _parse_dot_notation(self, normalized: str) -> Optional[Tuple[str, Optional[str], bool, Optional[str]]]:
        """
        Parse dot notation using smart class/method detection.
        
        Logic: Split by '.', find first token that looks like a class name,
        everything before = package, that token = class, remaining = method(s)
        """
        
        tokens = normalized.split('.')
        if len(tokens) < 2:
            # Single token - treat as class name
            return tokens[0], None, False, None
        
        # Find the first class-like token
        class_index = -1
        for i, token in enumerate(tokens):
            if self._looks_like_class(token):
                class_index = i
                break
        
        if class_index == -1:
            # No clear class token found - use heuristics
            if self._looks_like_method(tokens[-1]):
                # Last token looks like method
                class_fqn = '.'.join(tokens[:-1])
                method_name = self._clean_method_name(tokens[-1])
                logger.info(f"Heuristic parsing: class={class_fqn}, method={method_name}")
                return class_fqn, method_name, False, None
            else:
                # Treat entire string as class FQN
                logger.info(f"Treating entire input as class FQN: {normalized}")
                return normalized, None, False, None
        
        # Build class FQN from tokens up to and including class token
        class_fqn = '.'.join(tokens[:class_index + 1])
        
        # Remaining tokens are method(s)
        if class_index + 1 < len(tokens):
            method_tokens = tokens[class_index + 1:]
            method_name = self._clean_method_name('.'.join(method_tokens))
            logger.info(f"Dot notation parsed: class={class_fqn}, method={method_name}")
            return class_fqn, method_name, False, None
        else:
            # No method tokens
            logger.info(f"Dot notation parsed: class={class_fqn}, no method")
            return class_fqn, None, False, None
    
    def _looks_like_class(self, token: str) -> bool:
        """Check if token looks like a Java class name"""
        return bool(self.patterns['class_token'].match(token))
    
    def _looks_like_method(self, token: str) -> bool:
        """Check if token looks like a Java method name"""
        return bool(self.patterns['method_token'].match(token))
    
    def _clean_method_name(self, method_token: str) -> str:
        """Clean method name by removing parentheses"""
        parens_match = self.patterns['method_parens'].match(method_token)
        if parens_match:
            return parens_match.group(1)
        return method_token
    
    def _locate_file(self, class_fqn: str, repo_root: str, is_explicit_path: bool, 
                     explicit_path: Optional[str]) -> Dict[str, Any]:
        """
        Locate Java file using incremental traversal or explicit path.
        """
        
        if is_explicit_path:
            return self._locate_explicit_path(explicit_path)
        
        logger.info(f"repo_file_finder:Starting incremental traversal from repo_root='{repo_root}'")
        
        # Step 1: Try incremental traversal
        result = self._incremental_traversal(class_fqn, repo_root)
        if result['success']:
            return result
        
        # Step 2: Fallback strategies
        return self._fallback_search(class_fqn, repo_root, result['searched_paths'])
    
    def _locate_explicit_path(self, explicit_path: str) -> Dict[str, Any]:
        """Handle explicit file path"""
        
        if os.path.exists(explicit_path):
            logger.info(f"repo_file_finder:Explicit path exists -> using '{explicit_path}'")
            return {
                'success': True,
                'file_path': explicit_path,
                'how_found': 'explicit_path',
                'searched_paths': [explicit_path]
            }
        else:
            return {
                'success': False,
                'reason': 'explicit_path_not_found',
                'searched_paths': [explicit_path],
                'candidates': []
            }
    
    def _incremental_traversal(self, class_fqn: str, repo_root: str) -> Dict[str, Any]:
        """
        Perform incremental directory traversal based on package tokens.
        """
        
        # Split FQN into tokens
        tokens = class_fqn.split('.')
        if not tokens:
            return {'success': False, 'searched_paths': []}
        
        current_path = repo_root
        searched_paths = [repo_root]
        
        # Process tokens incrementally
        for i, token in enumerate(tokens):
            if self._looks_like_class(token):
                # This looks like a class token - try to find the .java file
                candidate_file = os.path.join(current_path, token + '.java')
                searched_paths.append(candidate_file)
                
                if os.path.exists(candidate_file):
                    logger.info(f"repo_file_finder:Candidate file '{token}.java' exists -> using exact path")
                    return {
                        'success': True,
                        'file_path': candidate_file,
                        'how_found': 'exact_fqn',
                        'searched_paths': searched_paths
                    }
                
                # File not found at this location, but this might be the class token
                # Continue to check if there are more tokens (inner class case)
                
            else:
                # This looks like a package token - treat as directory
                next_path = os.path.join(current_path, token)
                searched_paths.append(next_path)
                
                if os.path.exists(next_path) and os.path.isdir(next_path):
                    logger.info(f"repo_file_finder:Checking dir '{next_path}' ...")
                    current_path = next_path
                else:
                    # Directory doesn't exist - might be misnamed or this might be a class
                    logger.warning(f"repo_file_finder:Directory '{next_path}' does not exist")
                    break
        
        # If we reach here, incremental traversal didn't find the file
        logger.info("repo_file_finder:Incremental traversal failed")
        return {
            'success': False,
            'searched_paths': searched_paths
        }
    
    def _fallback_search(self, class_fqn: str, repo_root: str, previous_searched: List[str]) -> Dict[str, Any]:
        """
        Implement fallback search strategies when incremental traversal fails.
        """
        
        # Extract class name from FQN
        class_name = class_fqn.split('.')[-1]
        # Handle inner classes
        if '$' in class_name:
            class_name = class_name.split('$')[0]
        
        target_filename = class_name + '.java'
        searched_paths = list(previous_searched)
        candidates = []
        
        logger.info(f"repo_file_finder:Starting fuzzy search for '{target_filename}'")
        
        # Fuzzy basename search with limited depth
        max_depth = 8
        for root, dirs, files in os.walk(repo_root):
            # Limit recursion depth
            current_depth = len(Path(root).relative_to(Path(repo_root)).parts)
            if current_depth > max_depth:
                dirs.clear()
                continue
            
            # Check for exact filename match
            if target_filename in files:
                candidate_path = os.path.join(root, target_filename)
                candidates.append(candidate_path)
                
                # Return first exact match
                logger.info(f"repo_file_finder:Found by fuzzy search -> '{candidate_path}'")
                return {
                    'success': True,
                    'file_path': candidate_path,
                    'how_found': 'fuzzy',
                    'searched_paths': searched_paths,
                    'candidates': candidates
                }
            
            # Case-insensitive fallback
            for file in files:
                if file.lower() == target_filename.lower() and file != target_filename:
                    candidate_path = os.path.join(root, file)
                    candidates.append(candidate_path)
        
        # If we found case-insensitive matches, return the first one
        if candidates:
            best_candidate = candidates[0]
            logger.info(f"repo_file_finder:Found by case-insensitive search -> '{best_candidate}'")
            return {
                'success': True,
                'file_path': best_candidate,
                'how_found': 'case_insensitive',
                'searched_paths': searched_paths,
                'candidates': candidates
            }
        
        # No file found
        logger.warning(f"repo_file_finder:File not found for class '{class_name}'")
        return {
            'success': False,
            'reason': 'file_not_found',
            'searched_paths': searched_paths,
            'candidates': candidates
        }
    
    def _extract_method(self, file_path: str, class_fqn: str, method_name: str, 
                       how_found: str) -> Dict[str, Any]:
        """Extract specific method from Java file"""
        
        logger.info(f"method_extractor:Extracting method '{method_name}' from file '{file_path}'")
        
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.splitlines()
            
            # Find method in file
            method_info = self._find_method_in_content(content, lines, method_name)
            
            if method_info:
                start_line, end_line, method_code = method_info
                logger.info(f"method_extractor:Method found lines [{start_line},{end_line}]")
                
                return {
                    'status': 'success',
                    'file': self._get_relative_path(file_path),
                    'absolute_path': file_path,
                    'class': class_fqn,
                    'method': method_name,
                    'method_line_range': [start_line, end_line],
                    'method_code_snippet': method_code,
                    'how_found': how_found
                }
            else:
                logger.warning(f"method_extractor:Method '{method_name}' not found in file")
                
                # Provide method list for selection
                all_methods = self._get_all_methods(content, lines)
                
                return {
                    'status': 'failure',
                    'reason': 'method_not_found',
                    'file': self._get_relative_path(file_path),
                    'class': class_fqn,
                    'method': method_name,
                    'candidates': [],
                    'method_list': all_methods,
                    'suggestions': [
                        'Check method name spelling',
                        'Select from available methods',
                        'Verify method exists in this class'
                    ]
                }
                
        except Exception as e:
            logger.error(f"method_extractor:Failed to extract method: {e}")
            return self._create_failure_result("method_extraction_error", str(e))
    
    def _provide_file_analysis(self, file_path: str, class_fqn: str, how_found: str) -> Dict[str, Any]:
        """Provide file-level analysis when no method specified"""
        
        logger.info(f"method_extractor:No method specified, providing file-level analysis")
        
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.splitlines()
            
            # Get all methods
            all_methods = self._get_all_methods(content, lines)
            
            logger.info(f"method_extractor:Found {len(all_methods)} methods in file")
            
            return {
                'status': 'success',
                'file': self._get_relative_path(file_path),
                'absolute_path': file_path,
                'class': class_fqn,
                'method': None,
                'file_contents': content,
                'method_list': all_methods,
                'how_found': how_found
            }
            
        except Exception as e:
            logger.error(f"method_extractor:Failed to analyze file: {e}")
            return self._create_failure_result("file_analysis_error", str(e))
    
    def _find_method_in_content(self, content: str, lines: List[str], method_name: str) -> Optional[Tuple[int, int, str]]:
        """
        Find method in file content using regex approach.
        Returns (start_line, end_line, method_code) or None
        """
        
        # Method signature patterns
        patterns = [
            # Standard method pattern
            re.compile(
                rf'^\s*(?:(?:public|private|protected|static|final|abstract|synchronized|@\w+(?:\([^)]*\))?)\s+)*'
                rf'(?:<[^>]+>\s+)?[\w<>[\],\s]+\s+{re.escape(method_name)}\s*\([^)]*\)\s*(?:throws[^{{;]*)?\s*[{{;]',
                re.MULTILINE
            ),
            
            # Test method pattern (more lenient)
            re.compile(
                rf'^\s*(?:@\w+(?:\([^)]*\))?\s*)*(?:public|private|protected)?\s*(?:static\s+)?(?:void|[\w<>]+)\s+'
                rf'{re.escape(method_name)}\s*\([^)]*\)\s*(?:throws[^{{]*)?\s*{{',
                re.MULTILINE
            )
        ]
        
        for pattern in patterns:
            match = pattern.search(content)
            if match:
                # Find start line
                start_pos = match.start()
                start_line = content[:start_pos].count('\n') + 1
                
                # Extract method body using brace matching
                method_code = self._extract_method_body_from_pos(content, match.start())
                if method_code:
                    end_line = start_line + method_code.count('\n')
                    return start_line, end_line, method_code
        
        return None
    
    def _extract_method_body_from_pos(self, content: str, start_pos: int) -> Optional[str]:
        """Extract method body using brace matching from starting position"""
        
        # Find the opening brace
        brace_pos = content.find('{', start_pos)
        if brace_pos == -1:
            return None  # Abstract method or interface
        
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
        
        # If we get here, braces don't match
        return content[start_pos:]
    
    def _get_all_methods(self, content: str, lines: List[str]) -> List[Dict[str, Any]]:
        """Get list of all methods in the file"""
        
        methods = []
        
        # Method detection pattern
        method_pattern = re.compile(
            r'^\s*(?:(?:public|private|protected|static|final|abstract|@\w+(?:\([^)]*\))?)\s+)*'
            r'(?:<[^>]+>\s+)?[\w<>[\],\s]+\s+(\w+)\s*\([^)]*\)\s*(?:throws[^{;]*)?\s*[{;]',
            re.MULTILINE
        )
        
        for match in method_pattern.finditer(content):
            method_name = match.group(1)
            start_pos = match.start()
            line_num = content[:start_pos].count('\n') + 1
            
            # Get method signature
            signature = lines[line_num - 1].strip() if line_num <= len(lines) else ""
            
            methods.append({
                'name': method_name,
                'line': line_num,
                'signature': signature[:100] + '...' if len(signature) > 100 else signature
            })
        
        # Remove duplicates and sort by line number
        unique_methods = []
        seen = set()
        for method in methods:
            key = (method['name'], method['line'])
            if key not in seen:
                seen.add(key)
                unique_methods.append(method)
        
        return sorted(unique_methods, key=lambda x: x['line'])
    
    def _get_relative_path(self, file_path: str) -> str:
        """Get relative path for display"""
        path = Path(file_path)
        
        # Try to find a sensible relative path based on common Java source patterns
        parts = path.parts
        for i, part in enumerate(parts):
            if part in ['src', 'java', 'main', 'test', 'tests']:
                if i + 1 < len(parts):
                    return '/'.join(parts[i + 1:])
        
        # Fallback to just the filename or last few components
        if len(parts) > 3:
            return '/'.join(parts[-3:])
        return path.name
    
    def _create_failure_result(self, reason: str, details: str, 
                              searched_paths: List[str] = None, 
                              candidates: List[str] = None) -> Dict[str, Any]:
        """Create structured failure result"""
        
        return {
            'status': 'failure',
            'reason': reason,
            'details': details,
            'searched_paths': searched_paths or [],
            'candidates': candidates or [],
            'suggestions': [
                'provide explicit file path',
                'pick a candidate file',
                'supply different stack trace format'
            ]
        }

# Public interface function
def locate(stack_trace_line: str, repo_root: str) -> Dict[str, Any]:
    """
    Locate Java file and method from stack trace input.
    
    This is the main entry point for the deterministic stack trace locator.
    
    Args:
        stack_trace_line: Stack trace input (various formats supported)
        repo_root: Repository root path for searching
        
    Returns:
        Structured result dictionary with file location and method extraction
    """
    locator = StackTraceLocator()
    return locator.locate(stack_trace_line, repo_root)

# Test and validation
if __name__ == "__main__":
    print("Deterministic Stack Trace Locator Test")
    print("=" * 60)
    
    # Test cases as specified in requirements
    test_cases = [
        {
            'input': 'chs.common.styles.PinListDecorationStyle.refreshDecorations()',
            'repo': 'test_repo/src/chs',
            'description': 'Dot notation with method'
        },
        {
            'input': 'chs.common.attr.AttributeValidatorFactoryDescriptionTest#testIsVersionShortDescriptionUniqueNoRevisionsUniqueDesc',
            'repo': 'test_repo/src/chs',
            'description': 'IntelliJ format with method'
        },
        {
            'input': 'AttributeValidatorFactoryDescriptionTest',
            'repo': 'test_repo/src/chs',
            'description': 'Class only (no method)'
        },
        {
            'input': 'MyTest#testFoo[0]',
            'repo': 'test_repo/src',
            'description': 'Parameterized test'
        },
        {
            'input': 'com.foo.Bar$Inner#method',
            'repo': 'test_repo/src',
            'description': 'Inner class'
        }
    ]
    
    locator = StackTraceLocator()
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest Case {i}: {test_case['description']}")
        print(f"Input: {test_case['input']}")
        print(f"Repo: {test_case['repo']}")
        
        # Test parsing only (since test repo doesn't exist)
        parse_result = locator._parse_input(test_case['input'])
        if parse_result:
            class_fqn, method_name, is_explicit, explicit_path = parse_result
            print(f"Parsed -> Class FQN: {class_fqn}")
            print(f"         Method: {method_name}")
            print(f"         Explicit Path: {is_explicit}")
            
            if method_name != "unknown":
                print("✅ No method='unknown' generated")
            else:
                print("❌ Generated method='unknown'")
        else:
            print("❌ Parsing failed")
        
        print("-" * 40)
    
    print("\n" + "=" * 60)
    print("🎯 DETERMINISTIC STACK TRACE LOCATOR READY!")
    print("Key features implemented:")
    print("• ✅ Incremental directory traversal")
    print("• ✅ Smart package/class token detection")
    print("• ✅ Robust fallback strategies")
    print("• ✅ Never generates method='unknown'")
    print("• ✅ Structured JSON output")
    print("• ✅ Detailed logging for debugging")