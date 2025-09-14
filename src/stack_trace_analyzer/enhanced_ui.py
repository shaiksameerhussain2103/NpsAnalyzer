"""
Enhanced Stack Trace UI Component

This component provides an enhanced user interface for the improved stack trace analysis
without modifying or breaking existing UI components. It can be plugged in as an
additional option or replacement.
"""

import streamlit as st
import logging
from typing import Dict, List, Optional, Any
import traceback

from .enhanced_adapter import get_enhanced_adapter, validate_input
from .cache_manager import get_cache

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedStackTraceUI:
    """Enhanced UI component for improved stack trace analysis"""
    
    def __init__(self):
        """Initialize the enhanced UI"""
        self.adapter = get_enhanced_adapter()
        self.cache = get_cache()
        
        # Initialize session state for enhanced UI
        self._initialize_enhanced_session_state()
    
    def _initialize_enhanced_session_state(self):
        """Initialize enhanced UI session state variables"""
        if 'enhanced_extraction_result' not in st.session_state:
            st.session_state.enhanced_extraction_result = None
        if 'enhanced_method_options' not in st.session_state:
            st.session_state.enhanced_method_options = None
        if 'enhanced_selected_method' not in st.session_state:
            st.session_state.enhanced_selected_method = None
        if 'enhanced_repo_path' not in st.session_state:
            st.session_state.enhanced_repo_path = ""
    
    def render_enhanced_ui(self):
        """Render the enhanced stack trace analyzer UI"""
        st.header("🚀 Enhanced Stack Trace Analyzer")
        st.markdown("""
        **Improved method extraction with dual mode parsing:**
        - Handles various input formats (file paths, class names, methods)
        - Never returns "unknown" - provides method selection when needed
        - Supports both full extraction and method-specific analysis
        """)
        
        # Enhanced input section
        self._render_enhanced_input_section()
        
        # Method selection section (if multiple methods found)
        if st.session_state.enhanced_method_options:
            self._render_method_selection_section()
        
        # Results section
        if st.session_state.enhanced_extraction_result:
            self._render_enhanced_results_section()
    
    def _render_enhanced_input_section(self):
        """Render enhanced input section with validation"""
        st.subheader("1. Enhanced Stack Trace Input")
        
        # Input examples
        with st.expander("📖 Supported Input Formats"):
            st.markdown("""
            **Supported formats:**
            - `package.ClassName#methodName` (recommended)
            - `path/to/ClassName.java` (auto-detect methods)
            - `ClassName` (search entire repo)
            - `package.ClassName.methodName` (traditional)
            - File paths with or without quotes
            
            **Examples:**
            - `chs.common.attr.AttributeValidatorFactoryDescriptionTest#testMethod`
            - `chs/common/attr/AttributeValidatorFactoryDescriptionTest`
            - `"C:\\path\\to\\ClassName.java"`
            - `AttributeValidatorFactoryDescriptionTest`
            """)
        
        # Input field
        input_line = st.text_input(
            "Enter stack trace line or file reference:",
            placeholder="e.g., chs.common.attr.AttributeValidatorFactoryDescriptionTest#testMethod",
            key="enhanced_input_line"
        )
        
        # Real-time validation
        if input_line:
            validation = validate_input(input_line)
            
            if validation['valid']:
                st.success(f"✅ Valid input: {validation['message']}")
                
                # Show parsed components
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.info(f"**Class:** {validation.get('parsed_class', 'N/A')}")
                with col2:
                    st.info(f"**Method:** {validation.get('parsed_method', 'Auto-detect') or 'Auto-detect'}")
                with col3:
                    st.info(f"**Package:** {validation.get('parsed_package', 'Auto-detect') or 'Auto-detect'}")
            else:
                st.error(f"❌ {validation['message']}")
                if 'suggestions' in validation:
                    st.info("**Suggestions:** " + " | ".join(validation['suggestions']))
        
        # Repository path input
        st.subheader("2. Repository Path")
        
        repo_path = st.text_input(
            "Repository root path:",
            value=st.session_state.enhanced_repo_path,
            placeholder='e.g., C:\\Users\\YourName\\Projects\\JavaRepo (quotes will be auto-removed)',
            key="enhanced_repo_input"
        )
        
        # Clean and validate repo path
        if repo_path:
            # Remove quotes and normalize
            cleaned_repo_path = repo_path.strip().strip('"\'')
            
            from pathlib import Path
            if Path(cleaned_repo_path).exists():
                st.success("✅ Repository path exists")
                st.session_state.enhanced_repo_path = cleaned_repo_path
            else:
                st.error("❌ Repository path does not exist")
                st.info(f"Cleaned path: {cleaned_repo_path}")
        
        # Analyze button
        if st.button("🔍 Analyze with Enhanced Logic", 
                    disabled=not (input_line and repo_path and validation.get('valid', False))):
            self._perform_enhanced_analysis(input_line, st.session_state.enhanced_repo_path)
    
    def _perform_enhanced_analysis(self, input_line: str, repo_path: str):
        """Perform enhanced analysis with the new logic"""
        try:
            with st.spinner("Analyzing with enhanced extraction logic..."):
                result = self.adapter.extract_with_enhanced_logic(input_line, repo_path)
            
            logger.info(f"Enhanced analysis result: {result}")
            
            # Handle different result types
            if result["status"] == "success":
                extraction_type = result.get("extraction_type", "unknown")
                
                if extraction_type == "specific_method":
                    # Single method found and extracted
                    st.session_state.enhanced_extraction_result = result
                    st.success("✅ Method extracted successfully!")
                    
                elif extraction_type == "all_methods":
                    # Multiple methods found - show selection
                    method_options = self.adapter.get_method_selection_options(input_line, repo_path)
                    st.session_state.enhanced_method_options = method_options
                    st.info(f"🔍 Found {method_options.get('methods_count', 0)} methods. Please select one below.")
                    
                elif extraction_type == "full_file":
                    # No methods found, full file available
                    st.session_state.enhanced_extraction_result = result
                    st.info("📄 No specific methods found. Full file content available.")
                
                else:
                    st.warning(f"⚠️ Unexpected extraction type: {extraction_type}")
                    st.session_state.enhanced_extraction_result = result
            
            else:
                st.error(f"❌ Analysis failed: {result.get('error', 'Unknown error')}")
                st.session_state.enhanced_extraction_result = result
        
        except Exception as e:
            st.error(f"❌ Enhanced analysis error: {str(e)}")
            logger.error(f"Enhanced analysis error: {e}")
            logger.error(traceback.format_exc())
    
    def _render_method_selection_section(self):
        """Render method selection interface when multiple methods are found"""
        st.subheader("3. Method Selection")
        
        method_options = st.session_state.enhanced_method_options
        
        if method_options and method_options.get("status") == "success":
            st.info(f"📁 **File:** {method_options['file']}")
            st.info(f"🔢 **Found {method_options['methods_count']} methods**")
            
            methods = method_options.get("methods", [])
            
            # Create method selection options
            method_choices = []
            method_details = {}
            
            for i, method in enumerate(methods):
                choice_text = f"{method['name']} ({method['line_range']}) - {', '.join(method['modifiers'])}"
                method_choices.append(choice_text)
                method_details[choice_text] = method
            
            # Add option for full file
            method_choices.append("📄 View Full File Content")
            
            # Selection interface
            selected_choice = st.selectbox(
                "Select a method to analyze:",
                options=method_choices,
                key="method_selection"
            )
            
            # Show method preview
            if selected_choice and selected_choice != "📄 View Full File Content":
                method_info = method_details[selected_choice]
                
                with st.expander(f"Preview: {method_info['name']}"):
                    st.code(method_info['signature'], language='java')
                    st.write(f"**Parameters:** {', '.join(method_info['parameters']) if method_info['parameters'] else 'None'}")
                    st.write(f"**Modifiers:** {', '.join(method_info['modifiers'])}")
                    st.write(f"**Line Range:** {method_info['line_range']}")
            
            # Analyze selected method button
            if st.button("🎯 Analyze Selected Method"):
                self._analyze_selected_method(selected_choice, method_details, method_options)
    
    def _analyze_selected_method(self, selected_choice: str, method_details: Dict, method_options: Dict):
        """Analyze the user-selected method"""
        try:
            if selected_choice == "📄 View Full File Content":
                # User wants full file content
                result = {
                    "file": method_options['file'],
                    "method": "FULL_FILE",
                    "status": "success",
                    "extraction_type": "full_file",
                    "content_info": f"Full file with {method_options['methods_count']} methods"
                }
            else:
                # User selected a specific method
                method_info = method_details[selected_choice]
                
                # Extract the specific method
                # For now, create a mock result - in real implementation, 
                # this would call the enhanced extractor with the specific method
                result = {
                    "file": method_options['file'],
                    "method": method_info['name'],
                    "status": "success",
                    "extraction_type": "specific_method",
                    "method_details": method_info
                }
            
            st.session_state.enhanced_extraction_result = result
            st.session_state.enhanced_method_options = None  # Clear selection UI
            st.success(f"✅ Selected: {selected_choice}")
            st.rerun()
        
        except Exception as e:
            st.error(f"❌ Method selection error: {str(e)}")
            logger.error(f"Method selection error: {e}")
    
    def _render_enhanced_results_section(self):
        """Render enhanced analysis results"""
        st.subheader("4. Enhanced Analysis Results")
        
        result = st.session_state.enhanced_extraction_result
        
        # Results header
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("File", result.get("file", "N/A"))
        with col2:
            method_display = result.get("method", "N/A")
            if isinstance(method_display, list):
                method_display = f"{len(method_display)} methods"
            st.metric("Method", method_display)
        with col3:
            status_color = "🟢" if result.get("status") == "success" else "🔴"
            st.metric("Status", f"{status_color} {result.get('status', 'unknown')}")
        
        # Detailed results based on extraction type
        extraction_type = result.get("extraction_type", "unknown")
        
        if extraction_type == "specific_method":
            self._render_specific_method_results(result)
        elif extraction_type == "all_methods":
            self._render_all_methods_results(result)
        elif extraction_type == "full_file":
            self._render_full_file_results(result)
        else:
            st.warning(f"⚠️ Unknown extraction type: {extraction_type}")
            st.json(result)
        
        # Action buttons
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🔄 Analyze Another"):
                self._reset_enhanced_analysis()
        with col2:
            if st.button("📥 Export Results"):
                self._export_enhanced_results(result)
        with col3:
            if st.button("📊 View Cache Stats"):
                self._show_enhanced_cache_stats()
    
    def _render_specific_method_results(self, result: Dict):
        """Render results for specific method extraction"""
        st.success("🎯 **Specific Method Extracted**")
        
        method_details = result.get("method_details", {})
        
        if method_details:
            # Method information
            with st.expander("Method Information", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Name:** {method_details.get('name', 'N/A')}")
                    st.write(f"**Return Type:** {method_details.get('return_type', 'N/A')}")
                    st.write(f"**Line Range:** {method_details.get('start_line', 0)}-{method_details.get('end_line', 0)}")
                with col2:
                    st.write(f"**Modifiers:** {', '.join(method_details.get('modifiers', []))}")
                    st.write(f"**Parameters:** {len(method_details.get('parameters', []))}")
            
            # Method signature
            if method_details.get('full_signature'):
                st.subheader("Method Signature")
                st.code(method_details['full_signature'], language='java')
            
            # Method body
            if method_details.get('method_body'):
                st.subheader("Method Body")
                st.code(method_details['method_body'], language='java')
    
    def _render_all_methods_results(self, result: Dict):
        """Render results for all methods extraction"""
        st.info("📋 **All Methods Listed**")
        
        method_details_list = result.get("method_details", [])
        
        if method_details_list:
            st.write(f"Found **{len(method_details_list)} methods** in the file:")
            
            for i, method in enumerate(method_details_list, 1):
                with st.expander(f"Method {i}: {method.get('name', 'Unknown')}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Return Type:** {method.get('return_type', 'N/A')}")
                        st.write(f"**Line Range:** {method.get('start_line', 0)}-{method.get('end_line', 0)}")
                    with col2:
                        st.write(f"**Modifiers:** {', '.join(method.get('modifiers', []))}")
                        st.write(f"**Parameters:** {len(method.get('parameters', []))}")
                    
                    if method.get('full_signature'):
                        st.code(method['full_signature'], language='java')
    
    def _render_full_file_results(self, result: Dict):
        """Render results for full file extraction"""
        st.info("📄 **Full File Content Available**")
        
        content_length = result.get("content_length", 0)
        st.write(f"File size: **{content_length:,} characters**")
        
        if content_length > 0:
            st.info("💡 Full file content is available for analysis, but specific methods could not be extracted.")
            
            # Option to try again with different input
            st.markdown("**Suggestions:**")
            st.markdown("- Try specifying a method name with `#methodName`")
            st.markdown("- Check if the file contains valid Java methods")
            st.markdown("- Verify the file is not just a test or configuration file")
    
    def _reset_enhanced_analysis(self):
        """Reset enhanced analysis to start over"""
        st.session_state.enhanced_extraction_result = None
        st.session_state.enhanced_method_options = None
        st.session_state.enhanced_selected_method = None
        st.rerun()
    
    def _export_enhanced_results(self, result: Dict):
        """Export enhanced analysis results"""
        try:
            import json
            from datetime import datetime
            
            export_data = {
                "enhanced_analysis_result": result,
                "exported_at": datetime.now().isoformat(),
                "export_type": "enhanced_extraction"
            }
            
            json_string = json.dumps(export_data, indent=2)
            
            filename = f"enhanced_analysis_{result.get('method', 'result')}.json"
            
            st.download_button(
                label="📥 Download Enhanced Results",
                data=json_string,
                file_name=filename,
                mime="application/json"
            )
        
        except Exception as e:
            st.error(f"Export error: {str(e)}")
    
    def _show_enhanced_cache_stats(self):
        """Show enhanced cache statistics"""
        try:
            stats = self.cache.get_cache_stats()
            
            st.subheader("📊 Enhanced Cache Statistics")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Cache Entries", stats.get('total_entries', 0))
                st.metric("Extracted Code Entries", stats.get('extracted_code_entries', 0))
            with col2:
                st.metric("Analysis Results", stats.get('analysis_result_entries', 0))
                st.metric("Average Age (hours)", f"{stats.get('average_age_hours', 0):.1f}")
            
            if st.button("🗑️ Clear Enhanced Cache"):
                self.cache.clear_cache()
                st.success("Enhanced cache cleared!")
        
        except Exception as e:
            st.error(f"Cache stats error: {str(e)}")

def render_enhanced_stack_trace_ui():
    """Main function to render enhanced stack trace UI"""
    try:
        enhanced_ui = EnhancedStackTraceUI()
        enhanced_ui.render_enhanced_ui()
    except Exception as e:
        st.error(f"❌ Enhanced UI Error: {str(e)}")
        logger.error(f"Enhanced UI error: {e}")
        logger.error(traceback.format_exc())

# Example usage for testing
if __name__ == "__main__":
    st.set_page_config(
        page_title="Enhanced Stack Trace Analyzer",
        page_icon="🚀",
        layout="wide"
    )
    
    render_enhanced_stack_trace_ui()