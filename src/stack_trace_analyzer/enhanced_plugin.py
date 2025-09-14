"""
Enhanced Stack Trace Integration Plugin

This plugin integrates the enhanced stack trace analysis functionality
into the existing UI system without breaking or modifying existing code.
It provides a clean integration point that can be enabled/disabled.
"""

import logging
from typing import Dict, Any, Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedStackTracePlugin:
    """
    Plugin class that integrates enhanced functionality into existing system
    """
    
    def __init__(self, enable_enhanced: bool = True):
        """
        Initialize the plugin
        
        Args:
            enable_enhanced: Whether to enable enhanced functionality
        """
        self.enabled = enable_enhanced
        self.adapter = None
        
        if self.enabled:
            try:
                from .enhanced_adapter import get_enhanced_adapter
                self.adapter = get_enhanced_adapter()
                logger.info("Enhanced Stack Trace Plugin enabled")
            except ImportError as e:
                logger.warning(f"Enhanced functionality not available: {e}")
                self.enabled = False
    
    def is_available(self) -> bool:
        """Check if enhanced functionality is available"""
        return self.enabled and self.adapter is not None
    
    def analyze_with_enhancement(self, input_line: str, repo_path: str) -> Dict[str, Any]:
        """
        Analyze using enhanced logic if available, otherwise return indicator
        
        Args:
            input_line: Stack trace line or file reference
            repo_path: Repository path
            
        Returns:
            Analysis result with enhanced logic or fallback indicator
        """
        if not self.is_available():
            return {
                "enhanced": False,
                "status": "fallback",
                "message": "Enhanced functionality not available, using standard analysis"
            }
        
        try:
            result = self.adapter.extract_with_enhanced_logic(input_line, repo_path)
            result["enhanced"] = True
            return result
        except Exception as e:
            logger.error(f"Enhanced analysis failed: {e}")
            return {
                "enhanced": False,
                "status": "error",
                "message": f"Enhanced analysis failed: {str(e)}"
            }
    
    def get_method_selection_options(self, input_line: str, repo_path: str) -> Optional[Dict[str, Any]]:
        """
        Get method selection options if enhanced functionality is available
        
        Returns:
            Method options or None if not available
        """
        if not self.is_available():
            return None
        
        try:
            return self.adapter.get_method_selection_options(input_line, repo_path)
        except Exception as e:
            logger.error(f"Method selection options failed: {e}")
            return None
    
    def validate_input_format(self, input_line: str) -> Dict[str, Any]:
        """
        Validate input format using enhanced logic if available
        
        Returns:
            Validation result
        """
        if not self.is_available():
            return {
                "valid": True,  # Assume valid for backward compatibility
                "enhanced_validation": False,
                "message": "Standard validation"
            }
        
        try:
            from .enhanced_adapter import validate_input
            result = validate_input(input_line)
            result["enhanced_validation"] = True
            return result
        except Exception as e:
            logger.error(f"Enhanced validation failed: {e}")
            return {
                "valid": True,  # Fallback to assuming valid
                "enhanced_validation": False,
                "message": f"Validation error: {str(e)}"
            }
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get capabilities of the enhanced plugin"""
        if not self.is_available():
            return {
                "enhanced_parsing": False,
                "method_selection": False,
                "dual_mode_extraction": False,
                "robust_file_finding": False,
                "input_validation": False
            }
        
        return {
            "enhanced_parsing": True,
            "method_selection": True,
            "dual_mode_extraction": True,
            "robust_file_finding": True,
            "input_validation": True,
            "supported_formats": [
                "package.ClassName#methodName",
                "path/to/ClassName.java",
                "ClassName#methodName",
                "package.ClassName.methodName",
                "File paths with quotes"
            ]
        }

# Global plugin instance
_plugin_instance: Optional[EnhancedStackTracePlugin] = None

def get_plugin(enable_enhanced: bool = True) -> EnhancedStackTracePlugin:
    """Get the global plugin instance"""
    global _plugin_instance
    if _plugin_instance is None:
        _plugin_instance = EnhancedStackTracePlugin(enable_enhanced)
    return _plugin_instance

def is_enhanced_available() -> bool:
    """Quick check if enhanced functionality is available"""
    return get_plugin().is_available()

def analyze_with_plugin(input_line: str, repo_path: str) -> Dict[str, Any]:
    """Convenience function to analyze using plugin"""
    return get_plugin().analyze_with_enhancement(input_line, repo_path)

def validate_with_plugin(input_line: str) -> Dict[str, Any]:
    """Convenience function to validate using plugin"""
    return get_plugin().validate_input_format(input_line)

# Integration functions for existing UI
def enhance_existing_analysis(original_result: Dict[str, Any], input_line: str, repo_path: str) -> Dict[str, Any]:
    """
    Enhance existing analysis result with plugin capabilities
    
    Args:
        original_result: Result from existing analysis system
        input_line: Original input line
        repo_path: Repository path
        
    Returns:
        Enhanced result or original result if enhancement not available
    """
    plugin = get_plugin()
    
    if not plugin.is_available():
        # Return original result with indicator
        original_result["enhanced"] = False
        return original_result
    
    # Check if original analysis failed or returned "unknown"
    original_method = original_result.get("method", "")
    original_status = original_result.get("status", "")
    
    if (original_method == "unknown" or 
        original_status == "failure" or 
        "not found" in str(original_result).lower()):
        
        logger.info("Original analysis failed/incomplete, trying enhanced logic...")
        
        # Try enhanced analysis
        enhanced_result = plugin.analyze_with_enhancement(input_line, repo_path)
        
        if enhanced_result.get("status") == "success":
            logger.info("Enhanced analysis succeeded where original failed")
            return enhanced_result
        else:
            logger.info("Enhanced analysis also failed, returning original")
            original_result["enhanced_attempted"] = True
            original_result["enhanced_result"] = enhanced_result
            return original_result
    
    # Original analysis was successful, add enhanced capabilities info
    original_result["enhanced"] = True
    original_result["enhanced_available"] = True
    return original_result

def get_method_options_for_ui(input_line: str, repo_path: str) -> Optional[Dict[str, Any]]:
    """
    Get method selection options for UI integration
    
    Returns:
        Method options that can be displayed in UI, or None
    """
    plugin = get_plugin()
    
    if not plugin.is_available():
        return None
    
    return plugin.get_method_selection_options(input_line, repo_path)

# Test function
def test_plugin_integration():
    """Test the plugin integration"""
    print("Enhanced Stack Trace Plugin Test")
    print("=" * 50)
    
    plugin = get_plugin()
    
    print(f"Plugin Available: {plugin.is_available()}")
    print("Capabilities:", plugin.get_capabilities())
    
    # Test validation
    test_inputs = [
        "chs.common.attr.AttributeValidatorFactoryDescriptionTest#testMethod",
        "chs/common/attr/AttributeValidatorFactoryDescriptionTest",
        "InvalidInput"
    ]
    
    for input_line in test_inputs:
        validation = plugin.validate_input_format(input_line)
        print(f"\nInput: {input_line}")
        print(f"Valid: {validation.get('valid', False)}")
        print(f"Enhanced: {validation.get('enhanced_validation', False)}")
    
    print("\n" + "=" * 50)
    print("Plugin integration test completed!")

if __name__ == "__main__":
    test_plugin_integration()