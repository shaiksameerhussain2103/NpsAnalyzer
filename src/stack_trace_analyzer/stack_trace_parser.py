"""
Stack Trace Parser Module

Parses Java stack trace lines to extract package path, class name, and method name.

Example input: "chs.common.styles.PinListDecorationStyle.refreshDecorations()"
Output: {
    "package_path": "chs/common/styles",
    "class_name": "PinListDecorationStyle", 
    "method_name": "refreshDecorations",
    "full_class_path": "chs.common.styles.PinListDecorationStyle"
}
"""

import re
import logging
from typing import Dict, Optional, List
from dataclasses import dataclass

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class StackTraceInfo:
    """Data class to hold parsed stack trace information"""
    package_path: str
    class_name: str
    method_name: str
    full_class_path: str
    file_name: str
    line_number: Optional[int] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "package_path": self.package_path,
            "class_name": self.class_name,
            "method_name": self.method_name,
            "full_class_path": self.full_class_path,
            "file_name": self.file_name,
            "line_number": self.line_number
        }

class StackTraceParser:
    """Parser for Java stack trace lines"""
    
    # Regex patterns for different stack trace formats
    PATTERNS = {
        # Standard format: "package.Class.method()"
        'standard': r'^([a-zA-Z][a-zA-Z0-9_]*(?:\.[a-zA-Z][a-zA-Z0-9_]*)*?)\.([A-Z][a-zA-Z0-9_]*?)\.([a-zA-Z][a-zA-Z0-9_]*)\(\)$',
        
        # With line number: "package.Class.method(File.java:123)"
        'with_line': r'^([a-zA-Z][a-zA-Z0-9_]*(?:\.[a-zA-Z][a-zA-Z0-9_]*)*?)\.([A-Z][a-zA-Z0-9_]*?)\.([a-zA-Z][a-zA-Z0-9_]*)\(([^:]+):(\d+)\)$',
        
        # At format: "at package.Class.method(File.java:123)"
        'at_format': r'^at\s+([a-zA-Z][a-zA-Z0-9_]*(?:\.[a-zA-Z][a-zA-Z0-9_]*)*?)\.([A-Z][a-zA-Z0-9_]*?)\.([a-zA-Z][a-zA-Z0-9_]*)\(([^:]+):(\d+)\)$',
        
        # Simple at format: "at package.Class.method()"
        'at_simple': r'^at\s+([a-zA-Z][a-zA-Z0-9_]*(?:\.[a-zA-Z][a-zA-Z0-9_]*)*?)\.([A-Z][a-zA-Z0-9_]*?)\.([a-zA-Z][a-zA-Z0-9_]*)\(\)$',
        
        # File path format: "path/to/package/Class.java" or "package/Class.java"
        'file_path_slash': r'^(?:.*?[/\\])?([a-zA-Z][a-zA-Z0-9_]*(?:[/\\][a-zA-Z][a-zA-Z0-9_]*)*)[/\\]([A-Z][a-zA-Z0-9_]*?)\.java$',
        
        # File path with dots: "package.Class.java" 
        'file_path_dot': r'^(?:.*[/\\])?([a-zA-Z][a-zA-Z0-9_]*(?:\.[a-zA-Z][a-zA-Z0-9_]*)*?)\.([A-Z][a-zA-Z0-9_]*?)\.java$',
        
        # Just class name: "ClassName" or "package.ClassName"
        'class_only': r'^(?:([a-zA-Z][a-zA-Z0-9_]*(?:\.[a-zA-Z][a-zA-Z0-9_]*)*?)\.)?([A-Z][a-zA-Z0-9_]*?)$',
        
        # Mixed slash/dot format: "package/subpackage.ClassName" 
        'mixed_format': r'^([a-zA-Z][a-zA-Z0-9_]*(?:[/\\\.][a-zA-Z][a-zA-Z0-9_]*)*)[/\\.]([A-Z][a-zA-Z0-9_]*?)(?:\.java)?$'
    }
    
    def __init__(self):
        """Initialize the stack trace parser"""
        self.compiled_patterns = {
            name: re.compile(pattern) 
            for name, pattern in self.PATTERNS.items()
        }
    
    def parse_single_line(self, stack_trace_line: str) -> Optional[StackTraceInfo]:
        """
        Parse a single stack trace line
        
        Args:
            stack_trace_line: The stack trace line to parse
            
        Returns:
            StackTraceInfo object if parsing successful, None otherwise
        """
        # Preprocess the input line
        processed_line = self._preprocess_input(stack_trace_line)
        
        if not processed_line:
            return None
            
        logger.info(f"Parsing stack trace line: {processed_line}")
        
        # Try each pattern
        for pattern_name, compiled_pattern in self.compiled_patterns.items():
            match = compiled_pattern.match(processed_line)
            
            if match:
                logger.info(f"Matched pattern: {pattern_name}")
                return self._extract_info_from_match(match, pattern_name)
        
        logger.warning(f"No pattern matched for line: {processed_line}")
        
        # Try smart fallback parsing
        fallback_result = self._smart_fallback_parse(processed_line)
        if fallback_result:
            logger.info("Used smart fallback parsing")
            return fallback_result
        
        return None
    
    def _preprocess_input(self, input_line: str) -> str:
        """
        Preprocess input line to handle various formats and clean up
        
        Args:
            input_line: Raw input line
            
        Returns:
            Cleaned and normalized line
        """
        if not input_line:
            return ""
        
        # Remove leading/trailing whitespace
        line = input_line.strip()
        
        # Remove quotes (single or double)
        if (line.startswith('"') and line.endswith('"')) or (line.startswith("'") and line.endswith("'")):
            line = line[1:-1].strip()
        
        # Handle Windows paths with backslashes
        if '\\' in line and not line.startswith('at '):
            line = line.replace('\\', '/')
        
        # Remove common prefixes that might interfere
        prefixes_to_remove = [
            'File: ',
            'Class: ',
            'Method: ',
            'Stack: ',
            'Error in: ',
            'Exception at: '
        ]
        
        for prefix in prefixes_to_remove:
            if line.startswith(prefix):
                line = line[len(prefix):].strip()
                break
        
        return line
    
    def _smart_fallback_parse(self, line: str) -> Optional[StackTraceInfo]:
        """
        Smart fallback parser for lines that don't match standard patterns
        
        Args:
            line: Cleaned input line
            
        Returns:
            StackTraceInfo if we can intelligently parse it, None otherwise
        """
        # Try to extract class name from file paths or partial info
        
        # Case 1: Ends with .java - extract class name
        if line.endswith('.java'):
            # Remove .java extension
            without_extension = line[:-5]
            
            # Find the class name (last part)
            if '/' in without_extension:
                parts = without_extension.split('/')
                class_name = parts[-1]
                package_parts = parts[:-1]
                package_path = '/'.join(package_parts)
                package = '.'.join(package_parts)
            elif '.' in without_extension:
                parts = without_extension.split('.')
                class_name = parts[-1]
                package_parts = parts[:-1] 
                package_path = '/'.join(package_parts)
                package = '.'.join(package_parts)
            else:
                class_name = without_extension
                package_path = ""
                package = ""
            
            # Validate that class name looks reasonable
            if class_name and class_name[0].isupper() and class_name.replace('_', '').replace('$', '').isalnum():
                full_class_path = f"{package}.{class_name}" if package else class_name
                
                return StackTraceInfo(
                    package_path=package_path,
                    class_name=class_name,
                    method_name="unknown",
                    full_class_path=full_class_path,
                    file_name=f"{class_name}.java",
                    line_number=None
                )
        
        # Case 2: Contains recognizable Java class pattern
        # Look for something that looks like a class name
        import re
        class_pattern = r'([A-Z][a-zA-Z0-9_]*(?:Test|Exception|Service|Controller|Manager|Factory|Builder|Handler)?)'
        matches = re.findall(class_pattern, line)
        
        if matches:
            # Take the longest/most specific looking class name
            class_name = max(matches, key=len)
            
            # Try to extract package context
            class_index = line.find(class_name)
            before_class = line[:class_index].strip()
            
            # Look for package-like patterns before the class name
            package_parts = []
            if before_class:
                # Split by various separators and look for package-like parts
                potential_parts = re.split(r'[/\\.]', before_class)
                for part in potential_parts:
                    if part and part[0].islower() and part.isalnum():
                        package_parts.append(part)
            
            package = '.'.join(package_parts) if package_parts else ""
            package_path = '/'.join(package_parts) if package_parts else ""
            full_class_path = f"{package}.{class_name}" if package else class_name
            
            return StackTraceInfo(
                package_path=package_path,
                class_name=class_name,
                method_name="unknown",
                full_class_path=full_class_path,
                file_name=f"{class_name}.java",
                line_number=None
            )
        
        return None
    
    def _extract_info_from_match(self, match, pattern_name: str) -> StackTraceInfo:
        """Extract StackTraceInfo from regex match"""
        groups = match.groups()
        
        if pattern_name in ['standard', 'at_simple']:
            # Groups: (package, class, method)
            package, class_name, method = groups
            file_name = f"{class_name}.java"
            line_number = None
            
        elif pattern_name in ['with_line', 'at_format']:
            # Groups: (package, class, method, file, line)
            package, class_name, method, file_name, line_str = groups
            line_number = int(line_str) if line_str.isdigit() else None
            
        elif pattern_name in ['file_path_slash', 'mixed_format']:
            # Groups: (package_path, class_name) - from file path
            package_path_raw, class_name = groups
            
            # For file paths, we need to be smarter about extracting the actual package
            if package_path_raw:
                # Remove common prefixes that aren't part of the package
                package_parts = package_path_raw.replace('\\', '/').split('/')
                
                # Filter out common non-package directories
                non_package_dirs = {'src', 'main', 'java', 'test', 'resources', 'scala', 'kotlin'}
                filtered_parts = []
                
                # Find where the actual package starts (after src/main/java or similar)
                start_collecting = False
                for part in package_parts:
                    if part.lower() in non_package_dirs:
                        # Reset - we found a structural directory
                        filtered_parts = []
                    elif part:  # Non-empty part
                        filtered_parts.append(part)
                
                # Convert back to package notation
                package = '.'.join(filtered_parts) if filtered_parts else ""
                package_path = '/'.join(filtered_parts) if filtered_parts else ""
            else:
                package = ""
                package_path = ""
                
            method = "unknown"  # Default method name when not specified
            file_name = f"{class_name}.java"
            line_number = None
            
        elif pattern_name == 'file_path_dot':
            # Groups: (package, class_name) - from dotted file path  
            package, class_name = groups
            method = "unknown"  # Default method name
            file_name = f"{class_name}.java"
            line_number = None
            
        elif pattern_name == 'class_only':
            # Groups: (package_or_none, class_name)
            package_part, class_name = groups
            package = package_part if package_part else ""
            method = "unknown"  # Default method name
            file_name = f"{class_name}.java"
            line_number = None
            
        else:
            # Fallback for unknown patterns
            package = ""
            class_name = "Unknown"
            method = "unknown"
            file_name = f"{class_name}.java"
            line_number = None
        
        # Convert package notation to file path, handle empty package
        package_path = package.replace('.', '/') if package else ""
        
        # Create full class path
        full_class_path = f"{package}.{class_name}" if package else class_name
        
        return StackTraceInfo(
            package_path=package_path,
            class_name=class_name,
            method_name=method,
            full_class_path=full_class_path,
            file_name=file_name,
            line_number=line_number
        )
    
    def parse_multiple_lines(self, stack_trace_text: str) -> List[StackTraceInfo]:
        """
        Parse multiple stack trace lines
        
        Args:
            stack_trace_text: Multi-line stack trace text
            
        Returns:
            List of StackTraceInfo objects for successfully parsed lines
        """
        lines = stack_trace_text.strip().split('\n')
        parsed_lines = []
        
        for i, line in enumerate(lines, 1):
            parsed = self.parse_single_line(line)
            if parsed:
                logger.info(f"Successfully parsed line {i}: {parsed.full_class_path}.{parsed.method_name}")
                parsed_lines.append(parsed)
            else:
                logger.warning(f"Failed to parse line {i}: {line.strip()}")
        
        return parsed_lines
    
    def validate_parsed_info(self, info: StackTraceInfo) -> bool:
        """
        Validate that parsed information makes sense
        
        Args:
            info: StackTraceInfo to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Check for reasonable package depth (not too deep, but allow empty)
        if info.package_path:
            package_parts = info.package_path.split('/')
            if len(package_parts) > 15:  # More reasonable limit
                return False
        
        # Check class name follows Java conventions (starts with uppercase)
        if not info.class_name or len(info.class_name) < 1:
            return False
        
        if not info.class_name[0].isupper():
            return False
        
        # Allow more flexible method names - "unknown" is valid when method not specified
        if not info.method_name:
            return False
        
        # Method name can be "unknown" for file-based parsing
        if info.method_name != "unknown" and not info.method_name[0].islower():
            return False
        
        return True

# Example usage and testing
if __name__ == "__main__":
    parser = StackTraceParser()
    
    # Test cases including the problematic format
    test_lines = [
        "chs.common.styles.PinListDecorationStyle.refreshDecorations()",
        "at com.example.service.DataProcessor.processData(DataProcessor.java:45)",
        "java.util.ArrayList.get(ArrayList.java:434)",
        "at org.springframework.boot.Application.main(Application.java:123)",
        # NEW TEST CASES for the issue
        "chs/common/attr/AttributeValidatorFactoryDescriptionTest.java",
        '"chs/common/attr/AttributeValidatorFactoryDescriptionTest.java"',
        "C:\\project\\src\\main\\java\\chs\\common\\attr\\AttributeValidatorFactoryDescriptionTest.java",
        "AttributeValidatorFactoryDescriptionTest",
        "com.example.TestClass",
        "src/main/java/com/example/service/MyService.java"
    ]
    
    print("Testing Stack Trace Parser (Updated):")
    print("=" * 50)
    
    for line in test_lines:
        result = parser.parse_single_line(line)
        if result:
            print(f"✅ Parsed: {line}")
            print(f"   Package: {result.package_path}")
            print(f"   Class: {result.class_name}")
            print(f"   Method: {result.method_name}")
            print(f"   File: {result.file_name}")
            if result.line_number:
                print(f"   Line: {result.line_number}")
            print(f"   Valid: {parser.validate_parsed_info(result)}")
        else:
            print(f"❌ Failed: {line}")
        print()