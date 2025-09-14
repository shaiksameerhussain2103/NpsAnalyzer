"""
Stack Trace Analyzer Streamlit UI

Provides a user-friendly interface for the Stack Trace → Repo Code Analyzer feature.
Allows users to input stack tr            if input_method == "Multiple Lines":
                # Multiple lines - parse each line
                lines = stack_trace_text.strip().split('\n')
                parsed_info_list = []
                for line in lines:
                    if line.strip():
                        parsed_result = self.parser.parse(line.strip())
                        if parsed_result:
                            parsed_info_list.append(parsed_result)
                
                if parsed_info_list:
                    st.session_state.stack_trace_parsed_info = parsed_info_list
                    st.success(f"✅ Parsed {len(parsed_info_list)} stack trace lines successfully!")
                else:
                    st.error("❌ Could not parse any stack trace lines. Please check the format.")
            else:
                # Single line
                parsed_info = self.parser.parse(stack_trace_text)
                if parsed_info:
                    st.session_state.stack_trace_parsed_info = [parsed_info]
                    st.success("✅ Stack trace parsed successfully!")
                else:
                    st.error("❌ Could not parse stack trace line. Please check the format.")racted code, and get AI analysis results.

Features:
- Stack trace input and parsing
- Repository path selection
- Code extraction preview and confirmation
- AI analysis with custom questions
- Results display and caching
- Integration with main application UI
"""

import streamlit as st
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
import traceback
from datetime import datetime

from .robust_stack_trace_parser import RobustStackTraceParser, StackTraceParseResult
from .repo_file_finder import RepositoryFileFinder, FileLocation
from .method_extractor import JavaMethodExtractor, ExtractedCode
from .ai_analyzer import StackTraceAIAnalyzer
from .cache_manager import get_cache

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StackTraceAnalyzerUI:
    """Streamlit UI for Stack Trace Analyzer"""
    
    def __init__(self):
        """Initialize the UI components"""
        self.parser = RobustStackTraceParser()
        self.extractor = JavaMethodExtractor()
        self.ai_analyzer = StackTraceAIAnalyzer()
        self.cache = get_cache()
        
        # Initialize session state
        self._initialize_session_state()
    
    def _initialize_session_state(self):
        """Initialize Streamlit session state variables"""
        if 'stack_trace_parsed_info' not in st.session_state:
            st.session_state.stack_trace_parsed_info = None
        if 'stack_trace_found_files' not in st.session_state:
            st.session_state.stack_trace_found_files = []
        if 'stack_trace_extracted_code' not in st.session_state:
            st.session_state.stack_trace_extracted_code = None
        if 'stack_trace_analysis_result' not in st.session_state:
            st.session_state.stack_trace_analysis_result = None
        if 'stack_trace_repo_path' not in st.session_state:
            st.session_state.stack_trace_repo_path = r"C:\Users\Z0055DXU\mgnoscan\repo\iesd-25\datamodel_src\tests\src\chs"
    
    def render_main_ui(self):
        """Render the main Stack Trace Analyzer UI"""
        st.header("🔍 Stack Trace → Repo Code Analyzer")
        st.markdown("""
        Analyze Java methods directly from stack trace lines. This tool will:
        1. Parse your stack trace to identify the method
        2. Find the method in your repository
        3. Extract the relevant code
        4. Provide AI-powered analysis
        """)
        
        # Step 1: Stack Trace Input
        self._render_stack_trace_input()
        
        # Step 2: Repository Path Input
        if st.session_state.stack_trace_parsed_info:
            self._render_repository_input()
        
        # Step 3: File Search Results
        if st.session_state.stack_trace_found_files:
            self._render_file_search_results()
        
        # Step 4: Code Extraction and Confirmation
        if st.session_state.stack_trace_extracted_code:
            self._render_code_confirmation()
        
        # Step 5: AI Analysis Results
        if st.session_state.stack_trace_analysis_result:
            self._render_analysis_results()
    
    def _render_stack_trace_input(self):
        """Render stack trace input section"""
        st.subheader("1. Stack Trace Input")
        
        # Input method selection
        input_method = st.radio(
            "Choose input method:",
            ["Single Line", "Multiple Lines", "Upload File"],
            key="stack_trace_input_method"
        )
        
        stack_trace_text = ""
        
        if input_method == "Single Line":
            stack_trace_text = st.text_input(
                "Enter stack trace line:",
                placeholder="e.g., chs.common.styles.PinListDecorationStyle.refreshDecorations()",
                key="single_stack_trace"
            )
            
            # Show supported formats
            with st.expander("📋 Supported Input Formats"):
                st.markdown("""
                **The parser supports various input formats:**
                
                ✅ **Standard Stack Trace:**
                - `chs.common.styles.PinListDecorationStyle.refreshDecorations()`
                - `at com.example.Service.method(Service.java:123)`
                
                ✅ **File Paths (with or without quotes):**
                - `chs/common/attr/AttributeValidatorFactoryDescriptionTest.java`
                - `"chs/common/attr/AttributeValidatorFactoryDescriptionTest.java"`
                - `C:\\project\\src\\main\\java\\com\\example\\MyClass.java`
                
                ✅ **Class Names:**
                - `AttributeValidatorFactoryDescriptionTest`
                - `com.example.TestClass`
                
                The parser will automatically detect the format and extract the relevant information.
                """)
        
        elif input_method == "Multiple Lines":
            stack_trace_text = st.text_area(
                "Enter multiple stack trace lines:",
                height=150,
                placeholder="Paste your complete stack trace here...",
                key="multi_stack_trace"
            )
        
        elif input_method == "Upload File":
            uploaded_file = st.file_uploader(
                "Upload stack trace file",
                type=['txt', 'log'],
                key="stack_trace_file"
            )
            if uploaded_file:
                stack_trace_text = uploaded_file.read().decode('utf-8')
                st.text_area("File content:", value=stack_trace_text, height=100, disabled=True)
        
        # Parse button
        if st.button("Parse Stack Trace", disabled=not stack_trace_text.strip()):
            self._parse_stack_trace(stack_trace_text.strip())
        
        # Show parsed results
        if st.session_state.stack_trace_parsed_info:
            self._display_parsed_info()
    
    def _parse_stack_trace(self, stack_trace_text: str):
        """Parse the stack trace input"""
        try:
            if '\\n' in stack_trace_text:
                # Multiple lines - parse each line
                lines = stack_trace_text.strip().split('\\n')
                parsed_info_list = []
                for line in lines:
                    if line.strip():
                        parsed_result = self.parser.parse(line.strip())
                        if parsed_result:
                            parsed_info_list.append(parsed_result)
                
                if parsed_info_list:
                    st.session_state.stack_trace_parsed_info = parsed_info_list
                    st.success(f"✅ Parsed {len(parsed_info_list)} stack trace lines successfully!")
                else:
                    st.error("❌ Could not parse any stack trace lines. Please check the format.")
            else:
                # Single line
                parsed_info = self.parser.parse(stack_trace_text)
                if parsed_info:
                    st.session_state.stack_trace_parsed_info = [parsed_info]
                    st.success("✅ Stack trace parsed successfully!")
                else:
                    st.error("❌ Could not parse stack trace line. Please check the format.")
        
        except Exception as e:
            st.error(f"❌ Error parsing stack trace: {str(e)}")
            logger.error(f"Stack trace parsing error: {e}")
    
    def _display_parsed_info(self):
        """Display parsed stack trace information"""
        st.markdown("### Parsed Information")
        
        parsed_info = st.session_state.stack_trace_parsed_info
        if isinstance(parsed_info, list):
            for i, info in enumerate(parsed_info, 1):
                with st.expander(f"Stack Trace {i}: {info.class_fqn}.{info.method or 'N/A'}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Class FQN:** {info.class_fqn}")
                        st.write(f"**Method:** {info.method or 'N/A'}")
                    with col2:
                        if info.explicit_path:
                            st.write(f"**File Path:** {info.explicit_path}")
                        st.write(f"**Has File Path:** {info.file_path_provided}")
    
    def _render_repository_input(self):
        """Render repository path input section"""
        st.subheader("2. Repository Path")
        
        # Repository path input
        repo_path = st.text_input(
            "Enter repository root path:",
            value=st.session_state.stack_trace_repo_path,
            placeholder="e.g., C:\\Users\\YourName\\Projects\\MyJavaRepo",
            key="repo_path_input"
        )
        
        # Validate and search button
        col1, col2 = st.columns([3, 1])
        with col1:
            if repo_path:
                cleaned_path = self._clean_repository_path(repo_path)
                if Path(cleaned_path).exists():
                    st.success("✅ Repository path exists")
                    if cleaned_path != repo_path:
                        st.info(f"📝 Normalized path: {cleaned_path}")
                else:
                    st.error("❌ Repository path does not exist")
            elif repo_path:
                st.error("❌ Repository path does not exist")
        
        with col2:
            search_disabled = not (repo_path and Path(self._clean_repository_path(repo_path) if repo_path else "").exists())
            if st.button("Search Files", disabled=search_disabled):
                self._search_repository_files(repo_path)
    
    def _search_repository_files(self, repo_path: str):
        """Search for files in the repository"""
        try:
            # Clean and normalize the repository path
            cleaned_repo_path = self._clean_repository_path(repo_path)
            
            st.session_state.stack_trace_repo_path = cleaned_repo_path
            finder = RepositoryFileFinder(cleaned_repo_path)
            
            parsed_info_list = st.session_state.stack_trace_parsed_info
            found_files = []
            
            with st.spinner("Searching repository..."):
                for info in parsed_info_list:
                    # Create compatibility object for file finder
                    # TODO: Update file finder to use StackTraceParseResult directly
                    from .stack_trace_parser import StackTraceInfo
                    
                    # Extract class name from fully qualified name
                    if '.' in info.class_fqn:
                        parts = info.class_fqn.split('.')
                        package_path = '.'.join(parts[:-1])
                        class_name = parts[-1]
                    else:
                        package_path = ""
                        class_name = info.class_fqn
                    
                    # Create compatibility object
                    compat_info = StackTraceInfo(
                        package_path=package_path,
                        class_name=class_name,
                        method_name=info.method or "unknown",
                        full_class_path=info.class_fqn,
                        file_name=f"{class_name}.java",
                        line_number=None
                    )
                    
                    file_locations = finder.find_file(compat_info)
                    found_files.extend([(info, loc) for loc in file_locations])
            
            st.session_state.stack_trace_found_files = found_files
            
            if found_files:
                st.success(f"✅ Found {len(found_files)} matching file(s)!")
            else:
                st.warning("⚠️ No matching files found. Try checking the repository path or stack trace format.")
        
        except Exception as e:
            st.error(f"❌ Error searching repository: {str(e)}")
            logger.error(f"Repository search error: {e}")
    
    def _clean_repository_path(self, repo_path: str) -> str:
        """
        Clean and normalize repository path to handle quotes and various formats
        
        Args:
            repo_path: Raw repository path input
            
        Returns:
            Cleaned repository path
        """
        if not repo_path:
            return repo_path
        
        # Remove leading/trailing whitespace
        path = repo_path.strip()
        
        # Remove quotes (single or double)
        if (path.startswith('"') and path.endswith('"')) or (path.startswith("'") and path.endswith("'")):
            path = path[1:-1].strip()
        
        # Convert forward slashes to backslashes on Windows, or keep as is on Unix
        # Path will automatically handle this, but let's be explicit
        from pathlib import Path
        try:
            # Normalize the path
            normalized_path = str(Path(path).resolve())
            return normalized_path
        except Exception:
            # If Path fails, return the cleaned string
            return path
    
    def _render_file_search_results(self):
        """Render file search results"""
        st.subheader("3. Found Files")
        
        found_files = st.session_state.stack_trace_found_files
        
        if not found_files:
            st.info("No files found. Please check your repository path and try again.")
            return
        
        # Display found files
        for i, (stack_info, file_location) in enumerate(found_files):
            with st.expander(f"File {i+1}: {file_location.relative_path}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Method:** {stack_info.method or 'N/A'}")
                    st.write(f"**Search Strategy:** {file_location.search_strategy}")
                    st.write(f"**File Size:** {file_location.file_size:,} bytes")
                with col2:
                    st.write(f"**Package Path:** {file_location.package_path}")
                    st.write(f"**Relative Path:** {file_location.relative_path}")
                
                # Extract code button
                if st.button(f"Extract Code from File {i+1}", key=f"extract_{i}"):
                    self._extract_code_from_file(stack_info, file_location)
    
    def _extract_code_from_file(self, stack_info: StackTraceParseResult, file_location: FileLocation):
        """Extract code from the selected file"""
        try:
            # Create compatibility object for method extractor
            # TODO: Update method extractor to use StackTraceParseResult directly
            from .stack_trace_parser import StackTraceInfo
            
            # Extract class name from fully qualified name
            if '.' in stack_info.class_fqn:
                parts = stack_info.class_fqn.split('.')
                package_path = '.'.join(parts[:-1])
                class_name = parts[-1]
            else:
                package_path = ""
                class_name = stack_info.class_fqn
            
            # Create compatibility object
            compat_info = StackTraceInfo(
                package_path=package_path,
                class_name=class_name,
                method_name=stack_info.method or "unknown",
                full_class_path=stack_info.class_fqn,
                file_name=f"{class_name}.java",
                line_number=None
            )
            
            with st.spinner(f"Extracting method {stack_info.method or 'N/A'}..."):
                extracted_code = self.extractor.extract_method(file_location, compat_info)
            
            if extracted_code:
                st.session_state.stack_trace_extracted_code = (stack_info, file_location, extracted_code)
                st.success(f"✅ Successfully extracted method {stack_info.method or 'N/A'}!")
                st.rerun()
            else:
                st.error(f"❌ Could not extract method {stack_info.method or 'N/A'} from the file.")
        
        except Exception as e:
            st.error(f"❌ Error extracting code: {str(e)}")
            logger.error(f"Code extraction error: {e}")
    
    def _render_code_confirmation(self):
        """Render extracted code confirmation section"""
        st.subheader("4. Extracted Code")
        
        stack_info, file_location, extracted_code = st.session_state.stack_trace_extracted_code
        
        # Code preview
        st.markdown(f"### Method: `{stack_info.class_fqn}.{stack_info.method or 'N/A'}`")
        st.markdown(f"**File:** {file_location.relative_path}")
        st.markdown(f"**Lines:** {extracted_code.target_method.start_line} - {extracted_code.target_method.end_line}")
        st.markdown(f"**Extraction Strategy:** {extracted_code.extraction_strategy}")
        
        # Show extracted code
        with st.expander("View Extracted Code", expanded=True):
            st.code(extracted_code.get_complete_code(), language='java')
        
        # Show extraction details
        with st.expander("Extraction Details"):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Target Method:** {extracted_code.target_method.method_name}")
                st.write(f"**Dependencies Found:** {len(extracted_code.target_method.dependencies)}")
                st.write(f"**Dependent Methods:** {len(extracted_code.dependent_methods)}")
            with col2:
                st.write(f"**Class Fields:** {len(extracted_code.class_fields)}")
                st.write(f"**Imports:** {len(extracted_code.imports)}")
                st.write(f"**Total Lines:** {extracted_code.total_lines}")
        
        # Analysis options
        st.markdown("### Analysis Options")
        
        analysis_type = st.radio(
            "Choose analysis type:",
            ["Default Analysis", "Custom Question"],
            key="analysis_type"
        )
        
        custom_question = ""
        if analysis_type == "Custom Question":
            custom_question = st.text_area(
                "Enter your analysis question:",
                placeholder="e.g., What are the potential performance issues in this method?",
                key="custom_analysis_question"
            )
        
        # Analyze button
        analyze_disabled = analysis_type == "Custom Question" and not custom_question.strip()
        if st.button("Analyze Code", disabled=analyze_disabled):
            self._analyze_extracted_code(
                stack_info, 
                file_location, 
                extracted_code, 
                custom_question if analysis_type == "Custom Question" else None
            )
    
    def _analyze_extracted_code(self, stack_info: StackTraceParseResult, file_location: FileLocation, 
                               extracted_code: ExtractedCode, custom_question: Optional[str] = None):
        """Analyze the extracted code using AI"""
        try:
            with st.spinner("Analyzing code with AI..."):
                analysis_result = self.ai_analyzer.analyze_extracted_code(
                    extracted_code,
                    stack_info,
                    st.session_state.stack_trace_repo_path,
                    custom_question
                )
            
            st.session_state.stack_trace_analysis_result = (stack_info, analysis_result)
            st.success("✅ AI analysis completed!")
            st.rerun()
        
        except Exception as e:
            st.error(f"❌ Error during AI analysis: {str(e)}")
            logger.error(f"AI analysis error: {e}")
    
    def _render_analysis_results(self):
        """Render AI analysis results"""
        st.subheader("5. AI Analysis Results")
        
        stack_info, analysis_result = st.session_state.stack_trace_analysis_result
        
        # Analysis metadata
        metadata = analysis_result.get('analysis_metadata', {})
        if metadata:
            with st.expander("Analysis Information"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Analyzed At:** {metadata.get('analyzed_at', 'Unknown')}")
                    st.write(f"**Analysis Strategy:** {metadata.get('analysis_strategy', 'Unknown')}")
                with col2:
                    st.write(f"**Code Size:** {metadata.get('code_size_chars', 0):,} characters")
                    st.write(f"**Target Method:** {metadata.get('target_method', 'Unknown')}")
        
        # Main analysis results
        if analysis_result.get('analysis_strategy') == 'chunking':
            # Chunked analysis results
            st.markdown("### Analysis Results (Chunked)")
            
            # Show aggregated analysis
            if 'aggregated_analysis' in analysis_result:
                st.markdown("#### Overall Summary")
                st.markdown(analysis_result['aggregated_analysis'])
            
            # Show individual chunk analyses
            if 'chunk_analyses' in analysis_result:
                st.markdown("#### Detailed Chunk Analysis")
                for chunk_analysis in analysis_result['chunk_analyses']:
                    with st.expander(f"Chunk {chunk_analysis['chunk_id']}: {chunk_analysis['chunk_type']}"):
                        st.write(f"**Description:** {chunk_analysis['chunk_description']}")
                        st.markdown("**Analysis:**")
                        st.markdown(chunk_analysis['ai_response'])
        
        else:
            # Complete analysis results
            st.markdown("### Analysis Results")
            if 'ai_response' in analysis_result:
                st.markdown(analysis_result['ai_response'])
            
            # Show code context
            if 'code_context' in analysis_result:
                with st.expander("Code Context"):
                    context = analysis_result['code_context']
                    for key, value in context.items():
                        st.write(f"**{key.replace('_', ' ').title()}:** {value}")
        
        # Action buttons
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Analyze Another Method"):
                self._reset_analysis()
        with col2:
            if st.button("Export Results"):
                self._export_results(stack_info, analysis_result)
        with col3:
            if st.button("Show Cache Stats"):
                self._show_cache_stats()
    
    def _reset_analysis(self):
        """Reset the analysis to start over"""
        st.session_state.stack_trace_parsed_info = None
        st.session_state.stack_trace_found_files = []
        st.session_state.stack_trace_extracted_code = None
        st.session_state.stack_trace_analysis_result = None
        st.rerun()
    
    def _export_results(self, stack_info: StackTraceParseResult, analysis_result: Dict):
        """Export analysis results"""
        try:
            export_data = {
                "stack_trace_info": stack_info.to_dict(),
                "analysis_result": analysis_result,
                "exported_at": str(datetime.now())
            }
            
            # Convert to JSON string for download
            import json
            json_string = json.dumps(export_data, indent=2)
            
            st.download_button(
                label="Download Results as JSON",
                data=json_string,
                file_name=f"stack_trace_analysis_{stack_info.class_fqn.replace('.', '_')}_{stack_info.method or 'unknown'}.json",
                mime="application/json"
            )
        except Exception as e:
            st.error(f"Error exporting results: {str(e)}")
    
    def _show_cache_stats(self):
        """Show cache statistics"""
        try:
            stats = self.cache.get_cache_stats()
            
            st.markdown("### Cache Statistics")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Entries", stats.get('total_entries', 0))
                st.metric("Extracted Code Entries", stats.get('extracted_code_entries', 0))
            with col2:
                st.metric("Analysis Result Entries", stats.get('analysis_result_entries', 0))
                st.metric("Average Age (hours)", stats.get('average_age_hours', 0))
            
            if st.button("Clear Cache"):
                self.cache.clear_cache()
                st.success("Cache cleared successfully!")
        
        except Exception as e:
            st.error(f"Error retrieving cache stats: {str(e)}")

def render_stack_trace_analyzer_ui():
    """Main function to render the Stack Trace Analyzer UI"""
    try:
        analyzer_ui = StackTraceAnalyzerUI()
        analyzer_ui.render_main_ui()
    except Exception as e:
        st.error(f"Error initializing Stack Trace Analyzer: {str(e)}")
        st.error("Please check the logs for more details.")
        logger.error(f"Stack Trace Analyzer UI error: {e}")
        logger.error(traceback.format_exc())

# Example usage for testing
if __name__ == "__main__":
    st.set_page_config(
        page_title="Stack Trace Analyzer",
        page_icon="🔍",
        layout="wide"
    )
    
    render_stack_trace_analyzer_ui()