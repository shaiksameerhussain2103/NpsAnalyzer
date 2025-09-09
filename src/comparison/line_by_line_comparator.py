#!/usr/bin/env python3
"""
Line-by-Line CSV Comparison Module
==================================

This module provides line-by-line comparison functionality between two CSV files,
focusing on execution time differences and structural changes. It serves as an
intermediate step before AI analysis, giving users control over what to analyze.

Features:
- Line-by-line execution time comparison
- Structural awareness of CSV profiling data
- Conflict detection and highlighting
- User choice for proceeding to AI analysis
- Efficient handling of large CSV files
"""

import pandas as pd
import re
import json
import logging
from typing import Dict, List, Tuple, Optional, Any, NamedTuple
from dataclasses import dataclass
from pathlib import Path
import streamlit as st

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class LineConflict:
    """Represents a conflict between two lines in CSV files."""
    line_number: int
    file_a_content: str
    file_b_content: str
    file_a_time: Optional[float]
    file_b_time: Optional[float]
    time_delta: Optional[float]
    conflict_type: str  # 'content_diff', 'time_diff', 'both'
    function_name: str
    stack_level: int


@dataclass
class CSVStructure:
    """Represents the structure of a CSV profiling file."""
    headers: List[str]
    time_column_index: int
    cpu_time_column_index: int
    hits_column_index: int
    name_column_index: int
    has_percentage: bool
    time_unit: str  # 'ms', 's', etc.


class LineByLineComparator:
    """
    Performs line-by-line comparison between two CSV profiling files.
    
    This component analyzes execution time differences and structural changes
    without requiring AI analysis, giving users immediate visibility into
    performance variations.
    """
    
    def __init__(self):
        """Initialize the line-by-line comparator."""
        self.logger = logging.getLogger(f"{__name__}.LineByLineComparator")
        
    def _is_java_internal_line(self, function_name: str) -> bool:
        """
        Check if a function name belongs to Java internal/system packages.
        
        Args:
            function_name: Function name from CSV (e.g., "java.awt.EventQueue.dispatchEventImpl")
            
        Returns:
            True if this is a Java internal line that should be filtered out
        """
        if not function_name:
            return False
            
        function_name_lower = function_name.lower().strip()
        
        # Java internal/system package patterns to filter out
        java_internal_prefixes = [
            'java.',           # Core Java packages
            'javax.',          # Java extensions
            'sun.',            # Sun/Oracle internal packages  
            'com.sun.',        # Sun internal packages
            'jdk.internal.',   # JDK internal packages
            'oracle.',         # Oracle internal packages
            'com.oracle.',     # Oracle packages
        ]
        
        # Check if function name starts with any Java internal prefix
        for prefix in java_internal_prefixes:
            if function_name_lower.startswith(prefix):
                return True
                
        return False
        
    def analyze_csv_structure(self, file_path: str) -> CSVStructure:
        """
        Analyze the structure of a CSV profiling file to understand its format.
        
        Args:
            file_path: Path to the CSV file
            
        Returns:
            CSVStructure object with file format information
        """
        try:
            # Read first few rows to understand structure
            df_sample = pd.read_csv(file_path, nrows=10)
            headers = df_sample.columns.tolist()
            
            # Identify key columns
            time_col_idx = -1
            cpu_time_col_idx = -1
            hits_col_idx = -1
            name_col_idx = -1
            
            for i, header in enumerate(headers):
                header_lower = header.lower()
                if 'total time' in header_lower and 'cpu' not in header_lower:
                    time_col_idx = i
                elif 'total time' in header_lower and 'cpu' in header_lower:
                    cpu_time_col_idx = i
                elif 'hits' in header_lower:
                    hits_col_idx = i
                elif 'name' in header_lower:
                    name_col_idx = i
            
            # Check for percentage indicators and time units
            has_percentage = False
            time_unit = 'ms'  # default
            
            if time_col_idx >= 0 and len(df_sample) > 0:
                sample_time = str(df_sample.iloc[0, time_col_idx])
                has_percentage = '%' in sample_time
                if 'ms' in sample_time:
                    time_unit = 'ms'
                elif ' s' in sample_time:
                    time_unit = 's'
            
            return CSVStructure(
                headers=headers,
                time_column_index=time_col_idx,
                cpu_time_column_index=cpu_time_col_idx,
                hits_column_index=hits_col_idx,
                name_column_index=name_col_idx,
                has_percentage=has_percentage,
                time_unit=time_unit
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing CSV structure: {e}")
            raise
    
    def extract_timing_value(self, timing_str: str, time_unit: str = 'ms') -> Optional[float]:
        """
        Extract numeric timing value from formatted string.
        
        Args:
            timing_str: String like "131,697 ms (-0%)" or "0.0 ms (0%)"
            time_unit: Expected time unit
            
        Returns:
            Float value in milliseconds, or None if parsing fails
        """
        if not timing_str or pd.isna(timing_str):
            return None
            
        try:
            # Remove commas and extract number before unit
            clean_str = str(timing_str).replace(',', '')
            
            # Look for pattern like "123.45 ms" or "123 ms" or "123.45 s"
            pattern = r'(\d+\.?\d*)\s*(ms|s)'
            match = re.search(pattern, clean_str)
            
            if match:
                value = float(match.group(1))
                unit = match.group(2)
                # Convert to milliseconds if needed
                if unit == 's':
                    value *= 1000
                return value
            
            return None
            
        except (ValueError, AttributeError) as e:
            self.logger.debug(f"Could not parse timing value '{timing_str}': {e}")
            return None
    
    def extract_function_name(self, name_str: str) -> Tuple[str, int]:
        """
        Extract function name and stack level from the name column.
        
        Args:
            name_str: String like "  java.lang.Thread.run ()" or "Self time"
            
        Returns:
            Tuple of (function_name, stack_level)
        """
        if not name_str or pd.isna(name_str):
            return "unknown", 0
        
        # Count leading spaces to determine stack level
        clean_name = str(name_str)
        stack_level = len(clean_name) - len(clean_name.lstrip(' '))
        
        # Extract function name (remove leading spaces)
        function_name = clean_name.strip()
        
        return function_name, stack_level
    
    def compare_files_line_by_line(self, file_a_path: str, file_b_path: str) -> List[LineConflict]:
        """
        Perform line-by-line comparison between two CSV files.
        
        Args:
            file_a_path: Path to first CSV file
            file_b_path: Path to second CSV file
            
        Returns:
            List of LineConflict objects representing differences
        """
        conflicts = []
        
        try:
            # Analyze structure of both files
            structure_a = self.analyze_csv_structure(file_a_path)
            structure_b = self.analyze_csv_structure(file_b_path)
            
            # Read both files
            df_a = pd.read_csv(file_a_path)
            df_b = pd.read_csv(file_b_path)
            
            # Ensure we have the required columns
            if (structure_a.time_column_index < 0 or structure_a.name_column_index < 0 or
                structure_b.time_column_index < 0 or structure_b.name_column_index < 0):
                raise ValueError("Required columns (Name, Total Time) not found in CSV files")
            
            self.logger.info(f"Comparing {len(df_a)} lines from File A with {len(df_b)} lines from File B")
            
            # Create dictionaries for faster lookup
            # Key: (function_name, stack_level), Value: (line_number, timing)
            file_a_map = {}
            file_b_map = {}
            
            # Process File A
            for idx, row in df_a.iterrows():
                name_str = row[structure_a.headers[structure_a.name_column_index]]
                time_str = row[structure_a.headers[structure_a.time_column_index]]
                
                function_name, stack_level = self.extract_function_name(name_str)
                
                # Filter out Java internal/system packages - focus only on application code
                if self._is_java_internal_line(function_name):
                    continue
                
                timing_value = self.extract_timing_value(time_str, structure_a.time_unit)
                
                key = (function_name, stack_level)
                file_a_map[key] = (idx, timing_value, name_str, time_str)
            
            # Process File B
            for idx, row in df_b.iterrows():
                name_str = row[structure_b.headers[structure_b.name_column_index]]
                time_str = row[structure_b.headers[structure_b.time_column_index]]
                
                function_name, stack_level = self.extract_function_name(name_str)
                
                # Filter out Java internal/system packages - focus only on application code
                if self._is_java_internal_line(function_name):
                    continue
                
                timing_value = self.extract_timing_value(time_str, structure_b.time_unit)
                
                key = (function_name, stack_level)
                file_b_map[key] = (idx, timing_value, name_str, time_str)
            
            # Find conflicts
            all_keys = set(file_a_map.keys()) | set(file_b_map.keys())
            
            for key in all_keys:
                function_name, stack_level = key
                
                a_data = file_a_map.get(key)
                b_data = file_b_map.get(key)
                
                if a_data is None:
                    # Function exists only in File B
                    b_idx, b_timing, b_name, b_time_str = b_data
                    conflicts.append(LineConflict(
                        line_number=b_idx + 1,
                        file_a_content="",
                        file_b_content=b_name,
                        file_a_time=None,
                        file_b_time=b_timing,
                        time_delta=None,
                        conflict_type="content_diff",
                        function_name=function_name,
                        stack_level=stack_level
                    ))
                    
                elif b_data is None:
                    # Function exists only in File A
                    a_idx, a_timing, a_name, a_time_str = a_data
                    conflicts.append(LineConflict(
                        line_number=a_idx + 1,
                        file_a_content=a_name,
                        file_b_content="",
                        file_a_time=a_timing,
                        file_b_time=None,
                        time_delta=None,
                        conflict_type="content_diff",
                        function_name=function_name,
                        stack_level=stack_level
                    ))
                    
                else:
                    # Function exists in both files - check for differences
                    a_idx, a_timing, a_name, a_time_str = a_data
                    b_idx, b_timing, b_name, b_time_str = b_data
                    
                    content_different = a_name.strip() != b_name.strip()
                    
                    # Check timing differences (only if both have valid timings)
                    time_different = False
                    time_delta = None
                    
                    if a_timing is not None and b_timing is not None:
                        time_delta = b_timing - a_timing
                        # Consider significant if difference > 1ms or > 5% of original
                        threshold = max(1.0, abs(a_timing) * 0.05) if a_timing != 0 else 1.0
                        time_different = abs(time_delta) > threshold
                    
                    # Only add to conflicts if there's a meaningful difference
                    if content_different or time_different:
                        conflict_type = "both" if (content_different and time_different) else (
                            "content_diff" if content_different else "time_diff"
                        )
                        
                        conflicts.append(LineConflict(
                            line_number=min(a_idx, b_idx) + 1,
                            file_a_content=a_name,
                            file_b_content=b_name,
                            file_a_time=a_timing,
                            file_b_time=b_timing,
                            time_delta=time_delta,
                            conflict_type=conflict_type,
                            function_name=function_name,
                            stack_level=stack_level
                        ))
            
            # Sort conflicts by line number for better presentation
            conflicts.sort(key=lambda x: x.line_number)
            
            self.logger.info(f"Found {len(conflicts)} conflicts between the files")
            return conflicts
            
        except Exception as e:
            self.logger.error(f"Error during line-by-line comparison: {e}")
            raise
    
    def format_conflicts_for_display(self, conflicts: List[LineConflict]) -> Dict[str, Any]:
        """
        Format conflicts for user-friendly display.
        
        Args:
            conflicts: List of LineConflict objects
            
        Returns:
            Dictionary with formatted conflict data for display
        """
        if not conflicts:
            return {
                "total_conflicts": 0,
                "summary": "No conflicts found - files are identical",
                "conflicts_by_type": {},
                "formatted_conflicts": []
            }
        
        # Categorize conflicts
        conflicts_by_type = {
            "content_diff": [],
            "time_diff": [],
            "both": []
        }
        
        for conflict in conflicts:
            conflicts_by_type[conflict.conflict_type].append(conflict)
        
        # Format for display
        formatted_conflicts = []
        for conflict in conflicts[:50]:  # Limit to first 50 for performance
            formatted_conflict = {
                "line_number": conflict.line_number,
                "function_name": conflict.function_name,
                "stack_level": conflict.stack_level,
                "file_a_content": conflict.file_a_content or "(not present)",
                "file_b_content": conflict.file_b_content or "(not present)",
                "file_a_time": f"{conflict.file_a_time:.2f} ms" if conflict.file_a_time is not None else "N/A",
                "file_b_time": f"{conflict.file_b_time:.2f} ms" if conflict.file_b_time is not None else "N/A",
                "time_delta": f"{conflict.time_delta:+.2f} ms" if conflict.time_delta is not None else "N/A",
                "conflict_type": conflict.conflict_type,
                "severity": self._assess_conflict_severity(conflict)
            }
            formatted_conflicts.append(formatted_conflict)
        
        summary = f"Found {len(conflicts)} conflicts: "
        summary += f"{len(conflicts_by_type['content_diff'])} content differences, "
        summary += f"{len(conflicts_by_type['time_diff'])} timing differences, "
        summary += f"{len(conflicts_by_type['both'])} both"
        
        return {
            "total_conflicts": len(conflicts),
            "summary": summary,
            "conflicts_by_type": {k: len(v) for k, v in conflicts_by_type.items()},
            "formatted_conflicts": formatted_conflicts,
            "has_more": len(conflicts) > 50
        }
    
    def _assess_conflict_severity(self, conflict: LineConflict) -> str:
        """
        Assess the severity of a conflict for prioritization.
        
        Args:
            conflict: LineConflict object
            
        Returns:
            Severity level: "high", "medium", "low"
        """
        if conflict.time_delta is None:
            return "medium"  # Content differences
        
        abs_delta = abs(conflict.time_delta)
        
        if abs_delta > 1000:  # > 1 second
            return "high"
        elif abs_delta > 100:  # > 100ms
            return "medium"
        else:
            return "low"
    
    def export_conflicts_for_ai(self, conflicts: List[LineConflict]) -> str:
        """
        Export conflicts in a format suitable for AI analysis.
        
        Args:
            conflicts: List of LineConflict objects
            
        Returns:
            Formatted string ready for AI analysis
        """
        if not conflicts:
            return "No conflicts found between the files."
        
        # Group conflicts by severity and type
        high_severity = [c for c in conflicts if self._assess_conflict_severity(c) == "high"]
        medium_severity = [c for c in conflicts if self._assess_conflict_severity(c) == "medium"]
        
        output_lines = []
        output_lines.append("=== LINE-BY-LINE COMPARISON CONFLICTS ===")
        output_lines.append(f"Total conflicts: {len(conflicts)}")
        output_lines.append(f"High severity: {len(high_severity)}")
        output_lines.append(f"Medium severity: {len(medium_severity)}")
        output_lines.append("")
        
        # Show high severity conflicts first
        if high_severity:
            output_lines.append("HIGH SEVERITY CONFLICTS (>1000ms difference):")
            for conflict in high_severity[:20]:  # Limit for token efficiency
                output_lines.append(f"Line {conflict.line_number}: {conflict.function_name}")
                output_lines.append(f"  File A: {conflict.file_a_content}")
                output_lines.append(f"  File B: {conflict.file_b_content}")
                if conflict.time_delta is not None:
                    output_lines.append(f"  Time change: {conflict.time_delta:+.2f} ms")
                output_lines.append("")
        
        # Show medium severity conflicts
        if medium_severity:
            output_lines.append("MEDIUM SEVERITY CONFLICTS:")
            for conflict in medium_severity[:30]:  # Limit for token efficiency
                output_lines.append(f"Line {conflict.line_number}: {conflict.function_name}")
                if conflict.time_delta is not None:
                    output_lines.append(f"  Time change: {conflict.time_delta:+.2f} ms")
                else:
                    output_lines.append(f"  Content difference detected")
                output_lines.append("")
        
        return "\n".join(output_lines)


def render_line_by_line_comparison_ui(file_a_path: str, file_b_path: str, 
                                     file_a_name: str, file_b_name: str) -> Optional[str]:
    """
    Render the line-by-line comparison UI in Streamlit.
    
    Args:
        file_a_path: Path to first CSV file
        file_b_path: Path to second CSV file
        file_a_name: Display name for first file
        file_b_name: Display name for second file
        
    Returns:
        Formatted conflicts string if user chooses AI analysis, None otherwise
    """
    st.subheader("🔍 Line-by-Line Comparison")
    st.markdown(f"**Comparing:** `{file_a_name}` vs `{file_b_name}`")
    
    # Initialize comparator
    comparator = LineByLineComparator()
    
    with st.spinner("Performing line-by-line comparison..."):
        try:
            # Perform comparison
            conflicts = comparator.compare_files_line_by_line(file_a_path, file_b_path)
            formatted_results = comparator.format_conflicts_for_display(conflicts)
            
            # Display summary
            st.success(formatted_results["summary"])
            
            if formatted_results["total_conflicts"] == 0:
                st.info("✅ Files are identical - no conflicts detected!")
                return None
            
            # Show conflict statistics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Conflicts", formatted_results["total_conflicts"])
            with col2:
                st.metric("Content Differences", formatted_results["conflicts_by_type"]["content_diff"])
            with col3:
                st.metric("Timing Differences", formatted_results["conflicts_by_type"]["time_diff"])
            with col4:
                st.metric("Both Types", formatted_results["conflicts_by_type"]["both"])
            
            # Display conflicts in an expandable section
            with st.expander(f"📋 View Detailed Conflicts ({len(formatted_results['formatted_conflicts'])} shown)", expanded=True):
                if formatted_results["formatted_conflicts"]:
                    # Create DataFrame for better display
                    df_conflicts = pd.DataFrame(formatted_results["formatted_conflicts"])
                    
                    # Color-code by severity
                    def highlight_severity(row):
                        if row['severity'] == 'high':
                            return ['background-color: #ffebee'] * len(row)
                        elif row['severity'] == 'medium':
                            return ['background-color: #fff3e0'] * len(row)
                        else:
                            return ['background-color: #f3e5f5'] * len(row)
                    
                    # Display formatted table
                    st.dataframe(
                        df_conflicts[['line_number', 'function_name', 'conflict_type', 
                                    'file_a_time', 'file_b_time', 'time_delta', 'severity']].style.apply(highlight_severity, axis=1),
                        use_container_width=True,
                        height=400
                    )
                    
                    if formatted_results["has_more"]:
                        st.info("💡 Showing first 50 conflicts. More conflicts exist but are not displayed for performance.")
            
            # User choice for AI analysis
            st.markdown("---")
            st.subheader("🤖 AI Analysis Decision")
            
            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown("""
                **What would you like to do next?**
                - **Continue to AI Analysis**: Send these conflicts to AI for detailed technical analysis
                - **Stop Here**: Review conflicts manually without AI analysis
                """)
            
            with col2:
                proceed_to_ai = st.button(
                    "🚀 Continue to AI Analysis",
                    type="primary",
                    help="Send conflict data to AI for detailed analysis and recommendations"
                )
                
                stop_here = st.button(
                    "⏹️ Stop at Line Comparison",
                    help="End analysis here - no AI processing"
                )
            
            if proceed_to_ai:
                # Export conflicts for AI analysis
                ai_ready_data = comparator.export_conflicts_for_ai(conflicts)
                st.success("✅ Proceeding to AI analysis with conflict data!")
                return ai_ready_data
            
            elif stop_here:
                st.info("✅ Analysis stopped at line-by-line comparison as requested.")
                return None
            
            return None
            
        except Exception as e:
            st.error(f"❌ Error during line-by-line comparison: {str(e)}")
            logger.error(f"Line-by-line comparison error: {e}")
            return None
