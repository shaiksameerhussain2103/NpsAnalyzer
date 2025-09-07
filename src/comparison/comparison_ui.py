#!/usr/bin/env python3
"""
CSV Comparison UI Page
======================

Streamlit page for CSV comparison and AI analysis functionality.
This is an isolated addon feature that provides:
- Dual CSV upload interface
- File selection from separated outputs
- Real-time comparison results
- AI-powered analysis display
"""

import streamlit as st
import pandas as pd
import os
import sys
import tempfile
import json
from pathlib import Path
from typing import Dict, List, Any

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from csv_splitter import CSVSplitter
from comparison.csv_comparison_engine import CSVComparisonEngine


def render_comparison_page():
    """Render the complete CSV comparison page."""
    
    st.title("🔍 CSV Comparison & AI Analysis")
    st.markdown("---")
    st.markdown("""
    **Advanced CSV Comparison Tool with AI Analysis**
    
    This addon feature allows you to:
    - Upload two CSV files for comparison
    - Automatically separate files using hierarchical detection
    - Select specific sections for detailed comparison
    - Get AI-powered analysis of differences using Siemens API
    """)
    
    # Initialize session state
    if 'comparison_files_a' not in st.session_state:
        st.session_state.comparison_files_a = {}
    if 'comparison_files_b' not in st.session_state:
        st.session_state.comparison_files_b = {}
    if 'comparison_results' not in st.session_state:
        st.session_state.comparison_results = None
    
    # Create two columns for file uploads
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📄 File A (First CSV)")
        file_a = st.file_uploader(
            "Choose first CSV file", 
            type=['csv'], 
            key="csv_file_a",
            help="Upload the first CSV file for comparison"
        )
        
        if file_a is not None:
            process_uploaded_file(file_a, "A")
    
    with col2:
        st.subheader("📄 File B (Second CSV)")
        file_b = st.file_uploader(
            "Choose second CSV file", 
            type=['csv'], 
            key="csv_file_b",
            help="Upload the second CSV file for comparison"
        )
        
        if file_b is not None:
            process_uploaded_file(file_b, "B")
    
    # Show file selection interface if both files are processed
    if st.session_state.comparison_files_a and st.session_state.comparison_files_b:
        st.markdown("---")
        render_file_selection_interface()
    
    # Show results if comparison has been performed
    if st.session_state.comparison_results:
        st.markdown("---")
        render_comparison_results()


def process_uploaded_file(uploaded_file, file_type: str):
    """
    Process uploaded CSV file and separate it using existing logic.
    
    Args:
        uploaded_file: Streamlit uploaded file object
        file_type: "A" or "B" to distinguish between first and second file
    """
    try:
        # Create temporary directory for this file
        temp_dir = tempfile.mkdtemp(prefix=f"csv_comparison_{file_type.lower()}_")
        
        # Save uploaded file
        temp_file_path = os.path.join(temp_dir, uploaded_file.name)
        with open(temp_file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Show file info
        st.success(f"✅ File {file_type} uploaded: {uploaded_file.name}")
        
        # Display file preview
        with st.expander(f"Preview File {file_type}"):
            try:
                df = pd.read_csv(temp_file_path)
                st.write(f"**Shape:** {df.shape[0]} rows × {df.shape[1]} columns")
                st.dataframe(df.head(10))
            except Exception as e:
                st.error(f"Error reading file: {e}")
                return
        
        # Process with CSV splitter
        if st.button(f"🔄 Separate File {file_type}", key=f"separate_{file_type}"):
            with st.spinner(f"Separating File {file_type} using brute force method..."):
                try:
                    # Create output directory
                    output_dir = os.path.join(temp_dir, "separated")
                    os.makedirs(output_dir, exist_ok=True)
                    
                    # Initialize CSV splitter
                    splitter = CSVSplitter(output_dir)
                    
                    # Use brute force splitting method
                    separated_files = splitter.split_by_brute_force_line_by_line(temp_file_path)
                    
                    if separated_files:
                        # Store in session state
                        session_key = f"comparison_files_{file_type.lower()}"
                        st.session_state[session_key] = {
                            "original_file": temp_file_path,
                            "separated_files": separated_files,
                            "output_dir": output_dir,
                            "file_name": uploaded_file.name
                        }
                        
                        st.success(f"✅ File {file_type} separated into {len(separated_files)} sections")
                        
                        # Show separated files
                        with st.expander(f"Separated Files from File {file_type} ({len(separated_files)} files)"):
                            for i, file_path in enumerate(separated_files, 1):
                                file_name = Path(file_path).name
                                # Extract heading from filename (remove .csv extension and output directory prefix)
                                heading = file_name.replace('.csv', '').replace('_output', '')
                                st.write(f"**{i}.** `{file_name}` - *{heading}*")
                    
                    else:
                        st.error(f"Failed to separate File {file_type}")
                        
                except Exception as e:
                    st.error(f"Error separating File {file_type}: {e}")
                    st.exception(e)
    
    except Exception as e:
        st.error(f"Error processing File {file_type}: {e}")


def render_file_selection_interface():
    """Render interface for selecting specific files to compare."""
    
    st.subheader("🎯 Select Files for Comparison")
    
    files_a = st.session_state.comparison_files_a["separated_files"]
    files_b = st.session_state.comparison_files_b["separated_files"]
    
    # Get file lists - create display names from file paths
    file_names_a = [Path(file_path).name.replace('.csv', '').replace('_output', '') for file_path in files_a]
    file_names_b = [Path(file_path).name.replace('.csv', '').replace('_output', '') for file_path in files_b]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"**File A Options ({len(file_names_a)} sections):**")
        selected_file_a = st.selectbox(
            "Choose section from File A:",
            options=file_names_a,
            key="selected_file_a",
            help="Select which separated section to compare"
        )
    
    with col2:
        st.write(f"**File B Options ({len(file_names_b)} sections):**")
        selected_file_b = st.selectbox(
            "Choose section from File B:",
            options=file_names_b,
            key="selected_file_b",
            help="Select which separated section to compare"
        )
    
    # Performance Mode Selection
    st.markdown("---")
    st.subheader("⚡ Analysis Performance Settings")
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        fast_mode = st.checkbox(
            "🚀 Fast Mode", 
            value=False, 
            key="fast_mode_checkbox",
            help="Enable for ~95% faster processing using two-pass summarization"
        )
    
    with col2:
        if fast_mode:
            st.info("**Fast Mode Enabled**: Uses structured summarization for ~95% faster analysis. Best for quick insights.")
        else:
            st.info("**Standard Mode**: Full line-by-line preprocessing with parallel chunk analysis. Most detailed results.")
    
    # Performance estimates
    if st.session_state.get('comparison_files_a') and st.session_state.get('comparison_files_b'):
        selected_file_a_index = file_names_a.index(selected_file_a) if selected_file_a in file_names_a else 0
        selected_file_b_index = file_names_b.index(selected_file_b) if selected_file_b in file_names_b else 0
        
        # Estimate file sizes for performance prediction
        try:
            file_a_path_est = files_a[selected_file_a_index]
            file_b_path_est = files_b[selected_file_b_index]
            
            # Quick size check
            import os
            size_a = os.path.getsize(file_a_path_est) if os.path.exists(file_a_path_est) else 0
            size_b = os.path.getsize(file_b_path_est) if os.path.exists(file_b_path_est) else 0
            total_size_kb = (size_a + size_b) / 1024
            
            if total_size_kb > 500:  # Large files
                if fast_mode:
                    st.success(f"🎯 **Estimated Time**: ~30-60 seconds (Fast Mode) for {total_size_kb:.0f}KB files")
                else:
                    st.warning(f"⏱️ **Estimated Time**: ~2-5 minutes (Standard Mode) for {total_size_kb:.0f}KB files. Consider Fast Mode for quicker results.")
            else:
                st.info(f"📊 **File Size**: {total_size_kb:.0f}KB - Both modes will be fast")
                
        except Exception:
            pass  # Ignore size estimation errors
    
    # Comparison button
    if st.button("🔍 Compare Selected Files", type="primary"):
        # Get the actual file paths by matching the selected display names back to indices
        file_a_index = file_names_a.index(selected_file_a)
        file_b_index = file_names_b.index(selected_file_b)
        file_a_path = files_a[file_a_index]
        file_b_path = files_b[file_b_index]
        
        perform_comparison(selected_file_a, selected_file_b, file_a_path, file_b_path, fast_mode)


def perform_comparison(selected_file_a: str, selected_file_b: str, file_a_path: str, file_b_path: str, fast_mode: bool = False):
    """
    Perform comparison between selected files using the comparison engine.
    
    Args:
        selected_file_a: Selected heading from file A
        selected_file_b: Selected heading from file B  
        file_a_path: File path for file A
        file_b_path: File path for file B
        fast_mode: Whether to use fast mode analysis
    """
    try:
        mode_text = "Fast Mode (Two-pass Summarization)" if fast_mode else "Standard Mode (Full Preprocessing + Parallel Analysis)"
        with st.spinner(f"🤖 Performing brute force comparison and AI analysis ({mode_text})..."):
            
            # Get file paths (already provided as parameters)
            # file_a_path = files_a[selected_file_a]  # Old dictionary approach
            # file_b_path = files_b[selected_file_b]  # Old dictionary approach
            
            # Initialize comparison engine
            engine = CSVComparisonEngine()
            
            # Perform complete analysis with mode selection
            results = engine.compare_and_analyze(
                file_a_path=file_a_path,
                file_b_path=file_b_path,
                file_a_name=f"File A: {selected_file_a}",
                file_b_name=f"File B: {selected_file_b}",
                fast_mode=fast_mode
            )
            
            # Store results in session state
            st.session_state.comparison_results = results
            
            success_msg = f"✅ Comparison and AI analysis completed using {mode_text}!"
            st.success(success_msg)
            
    except Exception as e:
        st.error(f"Comparison failed: {e}")
        st.exception(e)


def render_comparison_results():
    """Render the comparison results and AI analysis."""
    
    results = st.session_state.comparison_results
    
    st.subheader("📊 Comparison Results")
    
    # Summary metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Conflicts", results["conflict_count"])
    
    with col2:
        has_diff = "Yes" if results["summary"]["has_differences"] else "No"
        st.metric("Has Differences", has_diff)
    
    with col3:
        st.metric("Analysis Time", results["summary"]["analysis_timestamp"].split("T")[1][:8])
    
    # File comparison info
    st.write("**Comparing:**")
    st.write(f"- 📄 **File A:** {results['file_a_name']}")
    st.write(f"- 📄 **File B:** {results['file_b_name']}")
    
    # AI Analysis - Most Important Section
    st.markdown("---")
    st.subheader("🤖 AI Analysis (Siemens API)")
    
    if results["ai_analysis"]:
        st.markdown(results["ai_analysis"])
    else:
        st.info("No AI analysis available")
    
    # Detailed conflicts (collapsible)
    if results["conflicts"]:
        st.markdown("---")
        with st.expander(f"🔍 Detailed Conflicts ({len(results['conflicts'])} found)", expanded=False):
            
            for i, conflict in enumerate(results["conflicts"], 1):
                st.markdown(f"### Conflict #{i}")
                st.write(f"**Range:** {conflict['range']}")
                st.write(f"**Type:** {conflict['type']}")
                st.write(f"**Description:** {conflict['description']}")
                
                # Show conflict sections
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**File A Section:**")
                    st.code(conflict["file_a_section"], language="text")
                
                with col2:
                    st.write("**File B Section:**")
                    st.code(conflict["file_b_section"], language="text")
                
                if i < len(results["conflicts"]):
                    st.markdown("---")
    
    # Download results
    st.markdown("---")
    st.subheader("💾 Download Results")
    
    # Prepare downloadable data
    results_json = json.dumps(results, indent=2, default=str)
    
    st.download_button(
        label="📥 Download Complete Analysis (JSON)",
        data=results_json,
        file_name=f"comparison_analysis_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json"
    )
    
    # Clear results button
    if st.button("🗑️ Clear Results"):
        st.session_state.comparison_results = None
        st.rerun()


if __name__ == "__main__":
    render_comparison_page()
