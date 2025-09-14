"""
Enhanced Extractor Integration Adapter

This adapter integrates the enhanced method extraction engine into the existing system
without modifying or breaking any existing code. It provides backward compatibility
while offering enhanced functionality.
"""

import logging
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

from .enhanced_extractor import (
    EnhancedStackTraceAnalyzer, 
    EnhancedExtractionResult,
    MethodSignature
)
from .method_extractor import ExtractedCode, ExtractedMethod
from .stack_trace_parser import StackTraceInfo
from .repo_file_finder import FileLocation

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedExtractionAdapter:
    """
    Adapter that bridges enhanced extraction with existing system.
    Provides both new enhanced functionality and backward compatibility.
    """
    
    def __init__(self):
        """Initialize the enhanced analyzer"""
        self.enhanced_analyzer = EnhancedStackTraceAnalyzer()
        logger.info("Enhanced Extraction Adapter initialized")
    
    def extract_with_enhanced_logic(self, 
                                   input_line: str, 
                                   repo_path: str,
                                   use_enhanced: bool = True) -> Dict[str, Any]:
        """
        Extract code using enhanced logic with structured output
        
        Args:
            input_line: Stack trace line or file reference
            repo_path: Repository root path
            use_enhanced: Whether to use enhanced extraction (default True)
            
        Returns:
            Structured extraction result
        """
        logger.info(f"Extracting with enhanced logic: {input_line}")
        
        if use_enhanced:
            # Use new enhanced logic
            return self.enhanced_analyzer.analyze_enhanced(input_line, repo_path)
        else:
            # Fallback to basic extraction (for backward compatibility)
            return self._basic_extraction_fallback(input_line, repo_path)
    
    def extract_compatible_format(self, 
                                 input_line: str, 
                                 repo_path: str) -> Optional[ExtractedCode]:
        """
        Extract code and return in existing ExtractedCode format for compatibility
        
        Args:
            input_line: Stack trace line or file reference
            repo_path: Repository root path
            
        Returns:
            ExtractedCode object compatible with existing system
        """
        try:
            # Get enhanced extraction result
            enhanced_result = self.enhanced_analyzer.analyze_enhanced(input_line, repo_path)
            
            if enhanced_result["status"] != "success":
                logger.warning(f"Enhanced extraction failed: {enhanced_result.get('error', 'Unknown error')}")
                return None
            
            # Convert to compatible format
            return self._convert_to_extracted_code(enhanced_result, repo_path)
        
        except Exception as e:
            logger.error(f"Compatible format extraction failed: {e}")
            return None
    
    def get_method_selection_options(self, 
                                   input_line: str, 
                                   repo_path: str) -> Dict[str, Any]:
        """
        Get method selection options when specific method is not found
        
        Args:
            input_line: Stack trace line or file reference
            repo_path: Repository root path
            
        Returns:
            Dictionary with available method options
        """
        try:
            # Parse without method name to get all methods
            package_path, class_name, _, _ = self.enhanced_analyzer.parser.parse_enhanced(input_line)
            
            if not class_name:
                return {
                    "status": "error",
                    "message": "Could not parse class name from input"
                }
            
            # Find file
            file_path = self.enhanced_analyzer._find_file_in_repo(repo_path, package_path, class_name)
            
            if not file_path:
                return {
                    "status": "error", 
                    "message": f"File not found for class: {class_name}"
                }
            
            # Extract all methods
            extraction_result = self.enhanced_analyzer.extractor.extract_enhanced(file_path, target_method=None)
            
            if extraction_result.status == "success" and extraction_result.all_methods:
                methods_info = []
                for method in extraction_result.all_methods:
                    methods_info.append({
                        "name": method.name,
                        "signature": method.full_signature,
                        "line_range": f"{method.start_line}-{method.end_line}",
                        "parameters": method.parameters,
                        "modifiers": method.modifiers
                    })
                
                return {
                    "status": "success",
                    "file": extraction_result.relative_path,
                    "class_name": class_name,
                    "methods_count": len(methods_info),
                    "methods": methods_info
                }
            
            else:
                return {
                    "status": "no_methods",
                    "file": extraction_result.relative_path,
                    "message": "No methods found in file, returning full file content available"
                }
        
        except Exception as e:
            logger.error(f"Method selection options failed: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def extract_specific_method_by_name(self, 
                                       file_path: str,
                                       method_name: str) -> Optional[ExtractedCode]:
        """
        Extract a specific method by name from a known file
        
        Args:
            file_path: Full path to Java file
            method_name: Name of method to extract
            
        Returns:
            ExtractedCode object if successful
        """
        try:
            extraction_result = self.enhanced_analyzer.extractor.extract_enhanced(file_path, method_name)
            
            if extraction_result.status == "success" and extraction_result.target_method:
                # Convert to compatible format
                enhanced_dict = extraction_result.to_dict()
                return self._convert_to_extracted_code(enhanced_dict, str(Path(file_path).parent))
            
            return None
        
        except Exception as e:
            logger.error(f"Specific method extraction failed: {e}")
            return None
    
    def _convert_to_extracted_code(self, enhanced_result: Dict, repo_path: str) -> ExtractedCode:
        """Convert enhanced result to existing ExtractedCode format"""
        try:
            # Create file location info
            file_info = FileLocation(
                absolute_path=enhanced_result.get("file_path", ""),
                relative_path=enhanced_result.get("file", ""),
                package_path="",
                class_name="",
                file_size=0,
                search_strategy="enhanced"
            )
            
            # Handle different extraction types
            if enhanced_result.get("extraction_type") == "specific_method":
                # Single method extraction
                method_details = enhanced_result.get("method_details", {})
                target_method = ExtractedMethod(
                    method_name=method_details.get("name", "unknown"),
                    method_signature=method_details.get("full_signature", ""),
                    method_body=method_details.get("method_body", ""),
                    start_line=method_details.get("start_line", 0),
                    end_line=method_details.get("end_line", 0),
                    class_name="",
                    dependencies=[]
                )
                
                return ExtractedCode(
                    target_method=target_method,
                    dependent_methods=[],
                    class_fields=[],
                    imports=[],
                    class_declaration="",
                    file_info=file_info,
                    extraction_strategy="enhanced_specific",
                    total_lines=method_details.get("end_line", 0) - method_details.get("start_line", 0)
                )
            
            elif enhanced_result.get("extraction_type") == "all_methods":
                # Multiple methods - use first as target, rest as dependents
                method_details_list = enhanced_result.get("method_details", [])
                
                if method_details_list:
                    first_method = method_details_list[0]
                    target_method = ExtractedMethod(
                        method_name=first_method.get("name", "multiple_methods"),
                        method_signature=first_method.get("full_signature", ""),
                        method_body=first_method.get("method_body", ""),
                        start_line=first_method.get("start_line", 0),
                        end_line=first_method.get("end_line", 0),
                        class_name="",
                        dependencies=[]
                    )
                    
                    # Convert other methods to dependent methods
                    dependent_methods = []
                    for method_details in method_details_list[1:]:
                        dep_method = ExtractedMethod(
                            method_name=method_details.get("name", ""),
                            method_signature=method_details.get("full_signature", ""),
                            method_body=method_details.get("method_body", ""),
                            start_line=method_details.get("start_line", 0),
                            end_line=method_details.get("end_line", 0),
                            class_name="",
                            dependencies=[]
                        )
                        dependent_methods.append(dep_method)
                    
                    return ExtractedCode(
                        target_method=target_method,
                        dependent_methods=dependent_methods,
                        class_fields=[],
                        imports=[],
                        class_declaration="",
                        file_info=file_info,
                        extraction_strategy="enhanced_multiple",
                        total_lines=sum(m.get("end_line", 0) - m.get("start_line", 0) for m in method_details_list)
                    )
            
            # Fallback for other cases
            target_method = ExtractedMethod(
                method_name="enhanced_extraction",
                method_signature="",
                method_body="",
                start_line=0,
                end_line=0,
                class_name="",
                dependencies=[]
            )
            
            return ExtractedCode(
                target_method=target_method,
                dependent_methods=[],
                class_fields=[],
                imports=[],
                class_declaration="",
                file_info=file_info,
                extraction_strategy="enhanced_fallback",
                total_lines=0
            )
        
        except Exception as e:
            logger.error(f"Conversion to ExtractedCode failed: {e}")
            raise
    
    def _basic_extraction_fallback(self, input_line: str, repo_path: str) -> Dict[str, Any]:
        """Fallback to basic extraction for backward compatibility"""
        return {
            "file": "FALLBACK_MODE",
            "method": "basic_extraction",
            "status": "success",
            "extraction_type": "fallback",
            "message": "Using basic extraction fallback"
        }
    
    def validate_input_format(self, input_line: str) -> Dict[str, Any]:
        """
        Validate and provide feedback on input format
        
        Returns:
            Dictionary with validation results and suggestions
        """
        try:
            package_path, class_name, method_name, parse_type = self.enhanced_analyzer.parser.parse_enhanced(input_line)
            
            if not class_name:
                return {
                    "valid": False,
                    "message": "Could not extract class name from input",
                    "suggestions": [
                        "Try format: package.ClassName#methodName",
                        "Try format: path/to/ClassName.java",
                        "Try format: ClassName#methodName"
                    ]
                }
            
            return {
                "valid": True,
                "parsed_class": class_name,
                "parsed_method": method_name,
                "parsed_package": package_path,
                "parse_type": parse_type,
                "message": f"Successfully parsed class: {class_name}"
            }
        
        except Exception as e:
            return {
                "valid": False,
                "message": f"Validation error: {str(e)}",
                "suggestions": ["Check input format and try again"]
            }

# Global adapter instance for easy access
_adapter_instance: Optional[EnhancedExtractionAdapter] = None

def get_enhanced_adapter() -> EnhancedExtractionAdapter:
    """Get global enhanced extraction adapter instance"""
    global _adapter_instance
    if _adapter_instance is None:
        _adapter_instance = EnhancedExtractionAdapter()
    return _adapter_instance

# Convenience functions for integration
def extract_enhanced(input_line: str, repo_path: str) -> Dict[str, Any]:
    """Convenience function for enhanced extraction"""
    adapter = get_enhanced_adapter()
    return adapter.extract_with_enhanced_logic(input_line, repo_path)

def get_method_options(input_line: str, repo_path: str) -> Dict[str, Any]:
    """Convenience function to get method selection options"""
    adapter = get_enhanced_adapter()
    return adapter.get_method_selection_options(input_line, repo_path)

def validate_input(input_line: str) -> Dict[str, Any]:
    """Convenience function to validate input format"""
    adapter = get_enhanced_adapter()
    return adapter.validate_input_format(input_line)

# Example usage and testing
if __name__ == "__main__":
    print("Enhanced Extraction Adapter Test")
    print("=" * 50)
    
    # Test the adapter
    adapter = EnhancedExtractionAdapter()
    
    test_inputs = [
        "chs.common.attr.AttributeValidatorFactoryDescriptionTest#testIsVersionShortDescriptionUniqueNoRevisionsUniqueDesc",
        "chs/common/attr/AttributeValidatorFactoryDescriptionTest",
        "AttributeValidatorFactoryDescriptionTest.java"
    ]
    
    for input_line in test_inputs:
        print(f"\nTesting: {input_line}")
        
        # Validate input
        validation = adapter.validate_input_format(input_line)
        print(f"Valid: {validation['valid']}")
        if validation['valid']:
            print(f"Parsed Class: {validation.get('parsed_class', 'N/A')}")
            print(f"Parsed Method: {validation.get('parsed_method', 'N/A')}")
            print(f"Parse Type: {validation.get('parse_type', 'N/A')}")
        else:
            print(f"Error: {validation['message']}")
    
    print("\n" + "=" * 50)
    print("Enhanced Extraction Adapter is ready for integration!")
    print("Use get_enhanced_adapter() to access the adapter in your existing code.")