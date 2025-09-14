"""
Java Method Extraction Engine

Extracts specific methods and their dependencies from Java files.
Handles large files by focusing only on the target method and related code.

Features:
- Parse Java files to identify method boundaries
- Extract target method with proper context
- Find and include dependent methods and fields
- Handle large files with chunking strategy
- Support for different code extraction strategies
"""

import re
import logging
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from pathlib import Path
import ast

from .stack_trace_parser import StackTraceInfo
from .repo_file_finder import FileLocation

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ExtractedMethod:
    """Information about an extracted method"""
    method_name: str
    method_signature: str
    method_body: str
    start_line: int
    end_line: int
    class_name: str
    dependencies: List[str]  # Other methods/fields this method uses
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "method_name": self.method_name,
            "method_signature": self.method_signature,
            "method_body": self.method_body,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "class_name": self.class_name,
            "dependencies": self.dependencies
        }

@dataclass 
class ExtractedCode:
    """Complete extracted code including method and context"""
    target_method: ExtractedMethod
    dependent_methods: List[ExtractedMethod]
    class_fields: List[str]
    imports: List[str]
    class_declaration: str
    file_info: FileLocation
    extraction_strategy: str
    total_lines: int
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "target_method": self.target_method.to_dict(),
            "dependent_methods": [m.to_dict() for m in self.dependent_methods],
            "class_fields": self.class_fields,
            "imports": self.imports,
            "class_declaration": self.class_declaration,
            "file_info": self.file_info.to_dict(),
            "extraction_strategy": self.extraction_strategy,
            "total_lines": self.total_lines
        }
    
    def get_complete_code(self) -> str:
        """Get the complete extracted code as a single string"""
        lines = []
        
        # Add imports
        if self.imports:
            lines.extend(self.imports)
            lines.append("")
        
        # Add class declaration
        lines.append(self.class_declaration)
        lines.append("")
        
        # Add class fields
        if self.class_fields:
            lines.extend(self.class_fields)
            lines.append("")
        
        # Add target method
        lines.append(f"    // TARGET METHOD: {self.target_method.method_name}")
        lines.append(self.target_method.method_body)
        lines.append("")
        
        # Add dependent methods
        if self.dependent_methods:
            lines.append("    // DEPENDENT METHODS:")
            for method in self.dependent_methods:
                lines.append(f"    // Method: {method.method_name}")
                lines.append(method.method_body)
                lines.append("")
        
        lines.append("}")  # Close class
        
        return "\n".join(lines)

class JavaMethodExtractor:
    """Extracts methods from Java source files"""
    
    # Maximum lines to extract before using chunking strategy
    MAX_EXTRACTION_LINES = 1000
    
    def __init__(self):
        """Initialize the method extractor"""
        self.method_pattern = re.compile(
            r'^(\s*(?:public|private|protected|static|final|abstract|synchronized|\s)*)\s+'
            r'(?:[\w<>[\],\s]+\s+)?'  # Return type
            r'(\w+)\s*\('               # Method name
            r'([^)]*)\)\s*'             # Parameters
            r'(?:throws\s+[\w\s,]+)?\s*'# Throws clause
            r'[{;]',                    # Opening brace or semicolon
            re.MULTILINE
        )
    
    def extract_method(self, file_location: FileLocation, stack_trace_info: StackTraceInfo) -> Optional[ExtractedCode]:
        """
        Extract a specific method from a Java file
        
        Args:
            file_location: Information about the Java file
            stack_trace_info: Information about the method to extract
            
        Returns:
            ExtractedCode object if successful, None otherwise
        """
        try:
            with open(file_location.absolute_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Failed to read file {file_location.absolute_path}: {e}")
            return None
        
        lines = content.split('\n')
        logger.info(f"Extracting method {stack_trace_info.method_name} from {file_location.relative_path} ({len(lines)} lines)")
        
        # Choose extraction strategy based on file size
        if len(lines) > self.MAX_EXTRACTION_LINES:
            return self._extract_with_chunking(file_location, stack_trace_info, lines)
        else:
            return self._extract_complete(file_location, stack_trace_info, lines)
    
    def _extract_complete(self, file_location: FileLocation, stack_trace_info: StackTraceInfo, lines: List[str]) -> Optional[ExtractedCode]:
        """Extract method from a reasonably-sized file"""
        logger.info("Using complete extraction strategy")
        
        # Find the target method
        target_method = self._find_method(lines, stack_trace_info.method_name)
        if not target_method:
            logger.warning(f"Could not find method {stack_trace_info.method_name}")
            return None
        
        # Extract class-level information
        imports = self._extract_imports(lines)
        class_declaration = self._extract_class_declaration(lines, stack_trace_info.class_name)
        class_fields = self._extract_class_fields(lines)
        
        # Find dependent methods
        dependent_methods = self._find_dependent_methods(lines, target_method, stack_trace_info.class_name)
        
        return ExtractedCode(
            target_method=target_method,
            dependent_methods=dependent_methods,
            class_fields=class_fields,
            imports=imports,
            class_declaration=class_declaration,
            file_info=file_location,
            extraction_strategy="complete",
            total_lines=len(lines)
        )
    
    def _extract_with_chunking(self, file_location: FileLocation, stack_trace_info: StackTraceInfo, lines: List[str]) -> Optional[ExtractedCode]:
        """Extract method from a large file using chunking strategy"""
        logger.info("Using chunking extraction strategy for large file")
        
        # First, find the target method location
        target_method = self._find_method(lines, stack_trace_info.method_name)
        if not target_method:
            logger.warning(f"Could not find method {stack_trace_info.method_name}")
            return None
        
        # Extract a reasonable window around the target method
        window_start = max(0, target_method.start_line - 50)
        window_end = min(len(lines), target_method.end_line + 50)
        
        # Extract basic class information from the beginning of the file
        header_lines = lines[:min(100, len(lines))]
        imports = self._extract_imports(header_lines)
        class_declaration = self._extract_class_declaration(header_lines, stack_trace_info.class_name)
        
        # Extract class fields from a broader range
        field_search_end = min(500, len(lines))
        class_fields = self._extract_class_fields(lines[:field_search_end])
        
        # Look for dependent methods in the window
        window_lines = lines[window_start:window_end]
        dependent_methods = self._find_dependent_methods(window_lines, target_method, stack_trace_info.class_name, window_start)
        
        return ExtractedCode(
            target_method=target_method,
            dependent_methods=dependent_methods,
            class_fields=class_fields,
            imports=imports,
            class_declaration=class_declaration,
            file_info=file_location,
            extraction_strategy="chunking",
            total_lines=len(lines)
        )
    
    def _find_method(self, lines: List[str], method_name: str) -> Optional[ExtractedMethod]:
        """Find a specific method in the file"""
        
        # Join all lines to handle multi-line method signatures
        content = '\n'.join(lines)
        
        # Find all method matches in the content
        matches = self.method_pattern.finditer(content)
        
        for match in matches:
            if match.group(2) == method_name:
                # Found the method, now find its line number
                method_start = content[:match.start()].count('\n')
                return self._extract_method_body(lines, method_start, method_name)
        
        return None
    
    def _extract_method_body(self, lines: List[str], start_line: int, method_name: str) -> Optional[ExtractedMethod]:
        """Extract the complete body of a method"""
        signature_lines = []
        body_lines = []
        
        # Extract method signature (might span multiple lines)
        i = start_line
        brace_count = 0
        in_signature = True
        
        while i < len(lines):
            line = lines[i]
            signature_lines.append(line)
            
            if in_signature:
                if '{' in line:
                    in_signature = False
                    brace_count = line.count('{')
                    if brace_count > 0:
                        body_lines.append(line)
            else:
                body_lines.append(line)
                brace_count += line.count('{') - line.count('}')
                
                if brace_count <= 0:
                    break
            
            i += 1
        
        if not body_lines:
            return None
        
        # Extract method signature (everything before the opening brace)
        signature = ""
        for line in signature_lines:
            signature += line
            if '{' in line:
                signature = signature[:signature.find('{')].strip()
                break
        
        # Find dependencies within the method
        dependencies = self._find_method_dependencies(body_lines)
        
        return ExtractedMethod(
            method_name=method_name,
            method_signature=signature,
            method_body='\n'.join(body_lines),
            start_line=start_line + 1,  # 1-indexed
            end_line=i + 1,  # 1-indexed
            class_name="",  # Will be set by caller
            dependencies=dependencies
        )
    
    def _find_method_dependencies(self, method_lines: List[str]) -> List[str]:
        """Find other methods and fields that this method depends on"""
        dependencies = set()
        
        # Look for method calls and field references
        method_call_pattern = re.compile(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(')
        field_reference_pattern = re.compile(r'\bthis\.([a-zA-Z_][a-zA-Z0-9_]*)')
        simple_field_pattern = re.compile(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*[=;]')
        
        for line in method_lines:
            # Find method calls
            method_calls = method_call_pattern.findall(line)
            dependencies.update(method_calls)
            
            # Find field references
            field_refs = field_reference_pattern.findall(line)
            dependencies.update(field_refs)
            
            # Find simple field references (less reliable)
            simple_fields = simple_field_pattern.findall(line)
            dependencies.update(simple_fields)
        
        # Filter out common Java keywords and built-in methods
        java_keywords = {'if', 'for', 'while', 'try', 'catch', 'return', 'new', 'super', 'this'}
        dependencies = dependencies - java_keywords
        
        return list(dependencies)
    
    def _find_dependent_methods(self, lines: List[str], target_method: ExtractedMethod, class_name: str, line_offset: int = 0) -> List[ExtractedMethod]:
        """Find methods that the target method depends on"""
        dependent_methods = []
        
        for dependency in target_method.dependencies:
            method = self._find_method(lines, dependency)
            if method:
                method.class_name = class_name
                # Adjust line numbers if we're working with a chunk
                method.start_line += line_offset
                method.end_line += line_offset
                dependent_methods.append(method)
        
        return dependent_methods
    
    def _extract_imports(self, lines: List[str]) -> List[str]:
        """Extract import statements from the beginning of the file"""
        imports = []
        
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('import '):
                imports.append(stripped)
            elif stripped.startswith('package '):
                imports.append(stripped)
            elif stripped and not stripped.startswith('//') and not stripped.startswith('/*'):
                # Stop when we hit non-import, non-comment code
                if not stripped.startswith('import') and not stripped.startswith('package'):
                    break
        
        return imports
    
    def _extract_class_declaration(self, lines: List[str], class_name: str) -> str:
        """Extract the class declaration line"""
        class_pattern = re.compile(f'.*class\\s+{class_name}.*{{', re.IGNORECASE)
        
        for line in lines:
            if class_pattern.match(line.strip()):
                return line.strip().replace('{', '').strip()
        
        return f"public class {class_name}"
    
    def _extract_class_fields(self, lines: List[str]) -> List[str]:
        """Extract class field declarations"""
        fields = []
        field_pattern = re.compile(r'^\s*(private|protected|public)?\s+.*\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*[=;].*$')
        
        in_class = False
        for line in lines:
            stripped = line.strip()
            
            # Look for class declaration to start collecting fields
            if 'class ' in stripped and '{' in stripped:
                in_class = True
                continue
            
            if in_class and stripped:
                # Check if it's a field declaration
                match = field_pattern.match(line)
                if match and not stripped.startswith('//'):
                    fields.append(stripped)
                elif stripped.startswith('public ') and '(' in stripped:
                    # Stop when we hit the first method
                    break
        
        return fields

# Example usage and testing
if __name__ == "__main__":
    print("Java Method Extractor Test")
    print("=" * 50)
    print("Note: This test requires actual Java files to work with.")
    print("Example usage:")
    print()
    print("from stack_trace_parser import StackTraceParser")
    print("from repo_file_finder import RepositoryFileFinder") 
    print("from method_extractor import JavaMethodExtractor")
    print()
    print("# Complete workflow")
    print('parser = StackTraceParser()')
    print('info = parser.parse_single_line("com.example.Service.processData()")')
    print()
    print('finder = RepositoryFileFinder("/path/to/repo")')
    print('locations = finder.find_file(info)')
    print()
    print('extractor = JavaMethodExtractor()')
    print('extracted = extractor.extract_method(locations[0], info)')
    print()
    print('if extracted:')
    print('    print(f"Extracted {extracted.target_method.method_name}")')
    print('    print(f"Dependencies: {extracted.target_method.dependencies}")')
    print('    print(f"Lines: {extracted.target_method.start_line}-{extracted.target_method.end_line}")')