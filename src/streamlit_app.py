"""
Simport io
import json
import os
import tempfile
import traceback
import zipfile
from pathlib import Path
from typing import Dict, Any, Optional

import pandas as pd
import streamlit as stI for File Converter Application
A user-friendly web interface for converting CSV and XML files to JSON.
"""

import io
import json
import os
import tempfile
import traceback
import zipfile
from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st

from file_converter import FileConverter, FileConverterError
try:
    from csv_splitter import CSVSplitterError
    from comparison.comparison_ui import render_comparison_page
except ImportError:
    from .csv_splitter import CSVSplitterError
    from .comparison.comparison_ui import render_comparison_page


class StreamlitUI:
    """Streamlit user interface for the file converter."""
    
    def __init__(self):
        """Initialize the Streamlit UI."""
        self.converter = FileConverter(output_dir="output")
        self.setup_page_config()
    
    def setup_page_config(self):
        """Configure Streamlit page settings."""
        st.set_page_config(
            page_title="File Converter - CSV/XML to JSON",
            page_icon="🔄",
            layout="wide",
            initial_sidebar_state="expanded"
        )
    
    def render_header(self):
        """Render the application header."""
        st.title("🔄 File Converter")
        st.markdown("### Convert CSV and XML files to JSON format")
        
        st.markdown("""
        **Features:**
        - 📊 CSV to JSON conversion with encoding detection
        - 🌳 XML to JSON conversion with metadata
        - ✂️ CSV file splitting for AI/LLM processing
        - 📁 Batch processing support
        - 📋 Data preview and validation
        - 💾 Download converted files
        """)
        
        st.divider()
    
    def render_sidebar(self):
        """Render the sidebar with conversion options."""
        st.sidebar.header("⚙️ Conversion Settings")
        
        conversion_mode = st.sidebar.radio(
            "Select Operation Mode:",
            ["Single File Convert", "Batch Convert", "CSV File Splitter", "🔍 CSV Comparison & AI Analysis"],
            index=0
        )
        
        # Encoding selection for CSV files
        encoding = st.sidebar.selectbox(
            "CSV Encoding:",
            ["utf-8", "latin-1", "cp1252", "ascii"],
            index=0,
            help="Select encoding for CSV files. Auto-detection will be attempted."
        )
        
        # JSON formatting options
        st.sidebar.subheader("JSON Output Options")
        indent_size = st.sidebar.slider("JSON Indentation", 0, 8, 2)
        include_metadata = st.sidebar.checkbox("Include Metadata", value=True)
        
        # CSV Splitting options (shown only for CSV Splitter mode)
        splitting_options = {}
        if conversion_mode == "CSV File Splitter":
            st.sidebar.subheader("🔧 CSV Splitting Options")
            
            split_method = st.sidebar.selectbox(
                "Split Method:",
                ["brute_force", "hierarchical", "rows", "size", "column"],
                index=0,
                help="Choose how to split the CSV file"
            )
            
            if split_method == "brute_force":
                st.sidebar.info("""
                ⚡ **Brute Force Line-by-Line Splitting**
                
                Most precise method for complex CSV data:
                - Parses file character by character
                - Handles quoted fields properly
                - Identifies capital letter headings exactly
                - Groups all sub-rows with their main heading
                
                **Recommended for problematic CSV files where other methods fail.**
                """)
                
            elif split_method == "hierarchical":
                st.sidebar.info("""
                🌳 **Hierarchical Splitting**
                
                Perfect for profiling data, call stacks, or any data where:
                - Main rows start with capital letters
                - Sub-rows are indented and belong to the main row
                
                Each main section and its sub-rows will be kept together in one file.
                """)
                
            elif split_method == "rows":
                rows_per_file = st.sidebar.number_input(
                    "Rows per file:", min_value=1, max_value=10000, value=100
                )
                splitting_options["rows_per_file"] = rows_per_file
                
            elif split_method == "size":
                max_size_mb = st.sidebar.number_input(
                    "Max file size (MB):", min_value=0.1, max_value=100.0, value=10.0, step=0.1
                )
                splitting_options["max_size_mb"] = max_size_mb
                
            elif split_method == "column":
                splitting_options["column_name"] = st.sidebar.text_input(
                    "Column name to split by:",
                    help="Enter the exact column name"
                )
            
            convert_to_json = st.sidebar.checkbox(
                "Convert split files to JSON", 
                value=True,
                help="Convert each split file to JSON format"
            )
            
            splitting_options.update({
                "split_method": split_method,
                "convert_to_json": convert_to_json
            })
        
        return {
            "mode": conversion_mode,
            "encoding": encoding,
            "indent": indent_size,
            "metadata": include_metadata,
            "splitting": splitting_options
        }
    
    def preview_data(self, file_content: bytes, file_name: str, file_type: str):
        """Preview the uploaded file data."""
        try:
            st.subheader("📋 Data Preview")
            
            if file_type == "csv":
                # Create a temporary file for CSV preview
                with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp_file:
                    tmp_file.write(file_content)
                    tmp_file_path = tmp_file.name
                
                try:
                    df = pd.read_csv(tmp_file_path, encoding='utf-8')
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Rows", len(df))
                    with col2:
                        st.metric("Total Columns", len(df.columns))
                    with col3:
                        st.metric("File Size", f"{len(file_content)} bytes")
                    
                    st.write("**Column Names:**")
                    st.write(list(df.columns))
                    
                    st.write("**First 10 rows:**")
                    st.dataframe(df.head(10), use_container_width=True)
                    
                except Exception as e:
                    st.warning(f"Could not preview CSV file: {str(e)}")
                finally:
                    os.unlink(tmp_file_path)
                    
            elif file_type == "xml":
                # Preview XML content (first 1000 characters)
                xml_content = file_content.decode('utf-8', errors='ignore')
                st.write("**XML Structure Preview:**")
                st.code(xml_content[:1000] + ("..." if len(xml_content) > 1000 else ""))
                
                st.metric("File Size", f"{len(file_content)} bytes")
                
        except Exception as e:
            st.error(f"Error previewing file: {str(e)}")
    
    def convert_single_file(self, options: dict):
        """Handle single file conversion."""
        st.subheader("📁 Single File Conversion")
        
        uploaded_file = st.file_uploader(
            "Choose a CSV or XML file",
            type=['csv', 'xml'],
            help="Upload a CSV or XML file to convert to JSON format"
        )
        
        if uploaded_file is not None:
            file_details = {
                "filename": uploaded_file.name,
                "filetype": uploaded_file.type,
                "filesize": uploaded_file.size
            }
            
            st.write("**File Details:**")
            st.json(file_details)
            
            # Get file extension
            file_ext = Path(uploaded_file.name).suffix.lower()
            
            # Preview the data
            file_content = uploaded_file.read()
            uploaded_file.seek(0)  # Reset file pointer
            
            if file_ext in ['.csv', '.xml']:
                self.preview_data(file_content, uploaded_file.name, file_ext[1:])
            
            st.divider()
            
            # Conversion button
            if st.button("🔄 Convert to JSON", type="primary", use_container_width=True):
                with st.spinner("Converting file..."):
                    try:
                        # Create temporary file
                        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
                            tmp_file.write(file_content)
                            tmp_file_path = tmp_file.name
                        
                        try:
                            # Convert file
                            json_data = None
                            if file_ext == '.csv':
                                json_data = self.converter.csv_to_json(tmp_file_path, options["encoding"])
                            elif file_ext == '.xml':
                                json_data = self.converter.xml_to_json(tmp_file_path)
                            
                            if not options["metadata"]:
                                # Remove metadata if not requested
                                json_data = json_data.get("data", json_data)
                            
                            # Display success message
                            st.success("✅ Conversion completed successfully!")
                            
                            # Show JSON preview
                            st.subheader("📄 JSON Preview")
                            json_str = json.dumps(json_data, indent=options["indent"], ensure_ascii=False)
                            
                            # Limit preview to first 2000 characters
                            preview_str = json_str[:2000] + ("..." if len(json_str) > 2000 else "")
                            st.code(preview_str, language='json')
                            
                            # Download button
                            output_filename = f"{Path(uploaded_file.name).stem}.json"
                            st.download_button(
                                label="💾 Download JSON File",
                                data=json_str,
                                file_name=output_filename,
                                mime="application/json",
                                use_container_width=True
                            )
                            
                        finally:
                            os.unlink(tmp_file_path)
                            
                    except FileConverterError as e:
                        st.error(f"❌ Conversion failed: {str(e)}")
                    except Exception as e:
                        st.error(f"❌ Unexpected error: {str(e)}")
                        st.code(traceback.format_exc())
    
    def convert_batch_files(self, options: dict):
        """Handle batch file conversion."""
        st.subheader("📂 Batch File Conversion")
        
        uploaded_files = st.file_uploader(
            "Choose multiple CSV or XML files",
            type=['csv', 'xml'],
            accept_multiple_files=True,
            help="Upload multiple CSV or XML files for batch conversion"
        )
        
        if uploaded_files:
            st.write(f"**{len(uploaded_files)} files uploaded**")
            
            # Show file list
            file_df = pd.DataFrame([
                {
                    "Filename": file.name,
                    "Type": Path(file.name).suffix.upper(),
                    "Size (bytes)": file.size
                }
                for file in uploaded_files
            ])
            
            st.dataframe(file_df, use_container_width=True)
            
            if st.button("🔄 Convert All Files", type="primary", use_container_width=True):
                progress_bar = st.progress(0)
                status_text = st.empty()
                results = []
                
                for i, uploaded_file in enumerate(uploaded_files):
                    status_text.text(f"Converting {uploaded_file.name}...")
                    
                    try:
                        file_ext = Path(uploaded_file.name).suffix.lower()
                        file_content = uploaded_file.read()
                        uploaded_file.seek(0)
                        
                        # Create temporary file
                        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
                            tmp_file.write(file_content)
                            tmp_file_path = tmp_file.name
                        
                        try:
                            # Convert file
                            json_data = None
                            if file_ext == '.csv':
                                json_data = self.converter.csv_to_json(tmp_file_path, options["encoding"])
                            elif file_ext == '.xml':
                                json_data = self.converter.xml_to_json(tmp_file_path)
                            
                            if not options["metadata"]:
                                json_data = json_data.get("data", json_data)
                            
                            json_str = json.dumps(json_data, indent=options["indent"], ensure_ascii=False)
                            output_filename = f"{Path(uploaded_file.name).stem}.json"
                            
                            results.append({
                                "filename": uploaded_file.name,
                                "output_filename": output_filename,
                                "json_data": json_str,
                                "status": "Success",
                                "error": None
                            })
                            
                        finally:
                            os.unlink(tmp_file_path)
                            
                    except Exception as e:
                        results.append({
                            "filename": uploaded_file.name,
                            "output_filename": None,
                            "json_data": None,
                            "status": "Failed",
                            "error": str(e)
                        })
                    
                    progress_bar.progress((i + 1) / len(uploaded_files))
                
                status_text.text("Batch conversion completed!")
                
                # Show results
                st.subheader("📊 Conversion Results")
                success_count = sum(1 for r in results if r["status"] == "Success")
                failed_count = len(results) - success_count
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("✅ Successful", success_count)
                with col2:
                    st.metric("❌ Failed", failed_count)
                
                # Download successful conversions
                if success_count > 0:
                    st.subheader("💾 Download Converted Files")
                    
                    for result in results:
                        if result["status"] == "Success":
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                st.write(f"📄 {result['output_filename']}")
                            with col2:
                                st.download_button(
                                    label="Download",
                                    data=result["json_data"],
                                    file_name=result["output_filename"],
                                    mime="application/json",
                                    key=f"download_{result['filename']}"
                                )
                
                # Show failed conversions
                if failed_count > 0:
                    st.subheader("❌ Failed Conversions")
                    for result in results:
                        if result["status"] == "Failed":
                            st.error(f"**{result['filename']}**: {result['error']}")
    
    def split_csv_files(self, options: dict):
        """Handle CSV file splitting functionality."""
        st.subheader("✂️ CSV File Splitter")
        st.markdown("""
        **Split large CSV files into smaller chunks for easier AI/LLM processing.**
        
        This feature helps you prepare data for AI models by breaking down large CSV files into manageable pieces.
        """)
        
        uploaded_file = st.file_uploader(
            "Choose a CSV file to split",
            type=['csv'],
            help="Upload a CSV file to split into smaller files"
        )
        
        if uploaded_file is not None:
            file_details = {
                "filename": uploaded_file.name,
                "filetype": uploaded_file.type,
                "filesize": uploaded_file.size
            }
            
            st.write("**File Details:**")
            st.json(file_details)
            
            # Get file content and create temporary file
            file_content = uploaded_file.read()
            uploaded_file.seek(0)
            
            # Analyze CSV structure first
            with st.expander("📊 CSV File Analysis", expanded=True):
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp_file:
                        tmp_file.write(file_content)
                        tmp_file_path = tmp_file.name
                    
                    try:
                        analysis = self.converter.analyze_csv_for_splitting(tmp_file_path)
                        
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Total Rows", analysis["total_rows"])
                        with col2:
                            st.metric("Total Columns", analysis["total_columns"])
                        with col3:
                            st.metric("File Size (MB)", analysis["file_size_mb"])
                        with col4:
                            st.metric("Recommended Rows/File", analysis["recommended_rows_per_file"])
                        
                        st.write("**Column Names:**")
                        st.write(", ".join(analysis["column_names"]))
                        
                        st.write("**Estimated Output Files:**")
                        st.info(f"With current settings: ~{analysis['estimated_output_files']} files")
                        
                        # Show sample data
                        if analysis["sample_data"]:
                            st.write("**Sample Data (First 3 rows):**")
                            sample_df = pd.DataFrame(analysis["sample_data"])
                            st.dataframe(sample_df, use_container_width=True)
                        
                    finally:
                        os.unlink(tmp_file_path)
                        
                except Exception as e:
                    st.error(f"Error analyzing CSV file: {str(e)}")
                    return
            
            st.divider()
            
            # Get splitting options
            splitting_opts = options["splitting"]
            
            # Validation for column-based splitting
            if splitting_opts.get("split_method") == "column":
                if not splitting_opts.get("column_name"):
                    st.warning("⚠️ Please enter a column name for column-based splitting")
                    return
            
            # Split operation
            if st.button("✂️ Split CSV File", type="primary", use_container_width=True):
                with st.spinner("Splitting CSV file..."):
                    try:
                        # Create temporary file again for splitting
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp_file:
                            tmp_file.write(file_content)
                            tmp_file_path = tmp_file.name
                        
                        try:
                            # Prepare splitting parameters
                            split_params = {
                                "encoding": options["encoding"],
                                "prefix": Path(uploaded_file.name).stem
                            }
                            split_params.update(splitting_opts)
                            
                            # Remove non-splitting parameters
                            split_params.pop("convert_to_json", None)
                            
                            # Perform splitting
                            if splitting_opts.get("convert_to_json", True):
                                results = self.converter.split_and_convert_csv(
                                    tmp_file_path,
                                    convert_splits=True,
                                    **split_params
                                )
                            else:
                                results = self.converter.split_csv_file(
                                    tmp_file_path,
                                    **split_params
                                )
                            
                            # Store results in session state
                            st.session_state.split_results = results
                            st.session_state.uploaded_filename = uploaded_file.name
                            
                        finally:
                            os.unlink(tmp_file_path)
                            
                    except (FileConverterError, CSVSplitterError) as e:
                        st.error(f"❌ Splitting failed: {str(e)}")
                    except Exception as e:
                        st.error(f"❌ Unexpected error: {str(e)}")
                        st.code(traceback.format_exc())
            
            # Display results if they exist in session state
            if hasattr(st.session_state, 'split_results') and st.session_state.split_results:
                results = st.session_state.split_results
                
                # Display results
                st.success("✅ CSV splitting completed successfully!")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Split Files Created", results["total_split_files"])
                with col2:
                    if "total_json_files" in results:
                        st.metric("JSON Files Created", results["total_json_files"])
                    else:
                        st.metric("JSON Files Created", "0")
                with col3:
                    st.metric("Split Method", results["split_method"].title())
                
                # Show manifest information
                st.subheader("📋 Split Operation Summary")
                
                try:
                    with open(results["manifest_file"], 'r') as f:
                        manifest = json.load(f)
                    
                    # Show file details
                    if manifest.get("split_files"):
                        st.write("**Created Files:**")
                        
                        manifest_df = pd.DataFrame(manifest["split_files"])
                        st.dataframe(manifest_df[["filename", "row_count", "file_size_mb"]], 
                                   use_container_width=True)
                    
                    # Download manifest
                    manifest_json = json.dumps(manifest, indent=2)
                    st.download_button(
                        label="📄 Download Manifest",
                        data=manifest_json,
                        file_name="split_manifest.json",
                        mime="application/json",
                        key="download_manifest"
                    )
                    
                except Exception as e:
                    st.warning(f"Could not display manifest details: {e}")
                
                # Helper function to create ZIP file
                def create_zip_file(file_paths, zip_name):
                    """Create a ZIP file containing all the split files."""
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                        for file_path in file_paths:
                            if os.path.exists(file_path):
                                zip_file.write(file_path, Path(file_path).name)
                    zip_buffer.seek(0)
                    return zip_buffer.getvalue()
                
                # Download split files
                st.subheader("💾 Download Split Files")
                
                # Add "Download All as ZIP" button
                all_files = []
                if results["split_files"]:
                    all_files.extend(results["split_files"])
                if results.get("converted_json_files"):
                    all_files.extend(results["converted_json_files"])
                
                if all_files:
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.write("**📦 Download All Files:**")
                    with col2:
                        zip_data = create_zip_file(all_files, "all_split_files.zip")
                        st.download_button(
                            label="📦 Download All as ZIP",
                            data=zip_data,
                            file_name=f"{Path(st.session_state.uploaded_filename).stem}_split_files.zip",
                            mime="application/zip",
                            type="primary",
                            key="download_all_zip"
                        )
                    
                    st.divider()
                
                # Show CSV files
                if results["split_files"]:
                    st.write("**CSV Split Files:**")
                    for i, split_file_path in enumerate(results["split_files"]):
                        try:
                            with open(split_file_path, 'r', encoding='utf-8') as f:
                                file_content_data = f.read()
                            
                            filename = Path(split_file_path).name
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                st.write(f"📄 {filename}")
                            with col2:
                                st.download_button(
                                    label="Download",
                                    data=file_content_data,
                                    file_name=filename,
                                    mime="text/csv",
                                    key=f"csv_download_{i}"
                                )
                        except Exception as e:
                            st.error(f"Error reading {split_file_path}: {e}")
                
                # Show JSON files if available
                if results.get("converted_json_files"):
                    st.write("**JSON Converted Files:**")
                    for i, json_file_path in enumerate(results["converted_json_files"]):
                        try:
                            with open(json_file_path, 'r', encoding='utf-8') as f:
                                json_content = f.read()
                            
                            filename = Path(json_file_path).name
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                st.write(f"📄 {filename}")
                            with col2:
                                st.download_button(
                                    label="Download",
                                    data=json_content,
                                    file_name=filename,
                                    mime="application/json",
                                    key=f"json_download_{i}"
                                )
                        except Exception as e:
                            st.error(f"Error reading {json_file_path}: {e}")
                
                # Add a button to clear results and start over
                st.divider()
                if st.button("🔄 Upload New File", type="secondary"):
                    if hasattr(st.session_state, 'split_results'):
                        del st.session_state.split_results
                    if hasattr(st.session_state, 'uploaded_filename'):
                        del st.session_state.uploaded_filename
                    st.rerun()
    
    def render_footer(self):
        """Render the application footer."""
        st.divider()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("### 📊 Supported Formats")
            st.markdown("""
            - **Input**: CSV, XML
            - **Output**: JSON
            - **Encoding**: UTF-8, Latin-1, CP1252
            """)
        
        with col2:
            st.markdown("### 🔧 Features")
            st.markdown("""
            - Auto encoding detection
            - Data validation
            - Batch processing
            - Error handling
            """)
        
        with col3:
            st.markdown("### 💡 Tips")
            st.markdown("""
            - Use UTF-8 encoding when possible
            - Check data preview before conversion
            - Large files may take longer to process
            - **NEW**: Split large CSV files for AI/LLM processing
            - Use row-based splitting for equal-sized chunks
            - Use column-based splitting to group by categories
            """)
    
    def run(self):
        """Run the Streamlit application."""
        # Get conversion options from sidebar
        options = self.render_sidebar()
        
        # Check if this is the comparison page
        if options["mode"] == "🔍 CSV Comparison & AI Analysis":
            # Render the comparison page (no header/footer needed as it's self-contained)
            render_comparison_page()
            return
        
        # For other modes, render normal header
        self.render_header()
        
        # Main content area
        if options["mode"] == "Single File Convert":
            self.convert_single_file(options)
        elif options["mode"] == "Batch Convert":
            self.convert_batch_files(options)
        else:  # CSV File Splitter
            self.split_csv_files(options)
        
        self.render_footer()


def main():
    """Main function to run the Streamlit app."""
    app = StreamlitUI()
    app.run()


if __name__ == "__main__":
    main()
