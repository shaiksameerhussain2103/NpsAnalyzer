#!/usr/bin/env python3
"""
CSV Comparison and AI Analysis Engine
=====================================

This module provides robust CSV comparison functionality with AI-powered analysis.
It's designed as a standalone addon that reuses existing CSV separation logic.
"""

import os
import logging
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
import difflib
from dataclasses import dataclass
from openai import OpenAI
from dotenv import load_dotenv
import asyncio
import json
import time
from collections import Counter
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ConflictRange:
    """Represents a range of conflicting rows between two CSV files."""
    start_row: int
    end_row: int
    file_a_section: str
    file_b_section: str
    conflict_type: str
    description: str


@dataclass
class HotspotInfo:
    """Represents a performance hotspot with detailed timing information."""
    function_name: str
    class_name: str
    method_name: str
    line_number: Optional[str]
    file_a_time: float
    file_b_time: float
    time_delta: float
    regression_factor: float
    raw_line_a: str
    raw_line_b: str
    row_range: str
    impact_score: float  # Weighted score for ranking


@dataclass
class StackTraceMapping:
    """Maps stack trace information from CSV row data."""
    full_function_path: str
    class_name: str
    method_name: str
    line_number: Optional[str]
    timing_data: Dict[str, float]  # 'total_time', 'cpu_time', 'hits'
    raw_csv_line: str


class CSVComparisonEngine:
    """
    Advanced CSV comparison engine with AI analysis capabilities.
    
    Features:
    - Robust brute force comparison algorithm
    - Conflict detection and range identification
    - AI-powered analysis using Siemens API
    - Structured difference reporting
    """
    
    def __init__(self, output_dir: str = "comparison_output"):
        """Initialize the comparison engine."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Initialize multiple AI clients for parallel processing
        self.api_keys = [
            os.getenv("OPENAI_API_KEY"),
            os.getenv("OPENAI_API_KEY2"), 
            os.getenv("OPENAI_API_KEY3")
        ]
        
        # Filter out None values and create clients
        self.api_keys = [key for key in self.api_keys if key is not None]
        self.ai_clients = []
        
        for i, api_key in enumerate(self.api_keys):
            client = OpenAI(
                api_key=api_key,
                base_url="https://api.siemens.com/llm/v1",
            )
            self.ai_clients.append(client)
        
        # For backward compatibility, keep the original client reference
        self.ai_client = self.ai_clients[0] if self.ai_clients else None
        
        # Rate limiting: Each key allows 60 requests/minute (updated capacity)
        self.requests_per_minute_per_key = 60
        self.total_requests_per_minute = len(self.ai_clients) * self.requests_per_minute_per_key
        
        # Track usage per key to implement fair distribution
        self.key_usage_tracker = {i: {'requests': 0, 'last_reset': time.time()} for i in range(len(self.ai_clients))}
        
        logger.info(f"CSV Comparison Engine initialized with {len(self.ai_clients)} API keys")
        logger.info(f"Total capacity: {self.total_requests_per_minute} requests/minute")
    
    def _get_available_client(self) -> Tuple[int, OpenAI]:
        """
        Get an available API client using round-robin with rate limit checking.
        
        Returns:
            Tuple of (client_index, client) for the least used client
        """
        current_time = time.time()
        
        # Reset counters every minute
        for key_idx in self.key_usage_tracker:
            tracker = self.key_usage_tracker[key_idx]
            if current_time - tracker['last_reset'] >= 60:
                tracker['requests'] = 0
                tracker['last_reset'] = current_time
        
        # Find the client with least usage that hasn't hit rate limit
        available_clients = []
        for i, client in enumerate(self.ai_clients):
            requests_made = self.key_usage_tracker[i]['requests']
            if requests_made < self.requests_per_minute_per_key:
                available_clients.append((i, client, requests_made))
        
        if not available_clients:
            # All clients at rate limit, use the one with oldest reset time
            oldest_reset_idx = min(self.key_usage_tracker.keys(), 
                                 key=lambda k: self.key_usage_tracker[k]['last_reset'])
            logger.warning(f"All API keys at rate limit. Using key {oldest_reset_idx + 1}")
            return oldest_reset_idx, self.ai_clients[oldest_reset_idx]
        
        # Return the client with least usage
        client_idx, client, usage = min(available_clients, key=lambda x: x[2])
        self.key_usage_tracker[client_idx]['requests'] += 1
        
        logger.debug(f"Using API key {client_idx + 1} (usage: {usage + 1}/{self.requests_per_minute_per_key})")
        return client_idx, client
    
    def _make_api_request_with_retry(self, messages: List[Dict], max_retries: int = 3, 
                                   retry_different_key: bool = True) -> str:
        """
        Make API request with automatic retry and key rotation on failure.
        
        Args:
            messages: List of messages for the API call
            max_retries: Maximum retry attempts
            retry_different_key: Whether to try different keys on failure
            
        Returns:
            API response content
        """
        last_error = None
        used_keys = set()
        
        for attempt in range(max_retries + 1):
            try:
                # Get an available client
                client_idx, client = self._get_available_client()
                
                # If retrying with different key, avoid already used keys
                if retry_different_key and attempt > 0 and client_idx in used_keys:
                    # Try to find an unused key
                    for i, alt_client in enumerate(self.ai_clients):
                        if i not in used_keys:
                            client_idx, client = i, alt_client
                            self.key_usage_tracker[client_idx]['requests'] += 1
                            break
                
                used_keys.add(client_idx)
                
                # Make the API request
                completions = client.chat.completions.create(
                    model="gpt-4",
                    messages=messages,
                    temperature=0.1,
                    max_tokens=4000
                )
                
                logger.debug(f"API request successful using key {client_idx + 1}")
                return completions.choices[0].message.content
                
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    wait_time = min(10 * (attempt + 1), 30)  # Exponential backoff
                    logger.warning(f"API request attempt {attempt + 1} failed with key {client_idx + 1}: {e}")
                    logger.info(f"Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"All retry attempts failed. Last error: {e}")
        
        raise Exception(f"API request failed after {max_retries + 1} attempts: {last_error}")
    
    def load_separated_files(self, directory: str) -> Dict[str, str]:
        """
        Load all separated CSV files from a directory.
        
        Args:
            directory: Path to directory containing separated CSV files
            
        Returns:
            Dictionary mapping filename to file path
        """
        files = {}
        directory_path = Path(directory)
        
        if not directory_path.exists():
            logger.error(f"Directory does not exist: {directory}")
            return files
        
        for file_path in directory_path.glob("*.csv"):
            files[file_path.name] = str(file_path)
            
        logger.info(f"Loaded {len(files)} separated files from {directory}")
        return files
    
    def read_csv_content(self, file_path: str) -> pd.DataFrame:
        """
        Read CSV file content with robust error handling.
        
        Args:
            file_path: Path to the CSV file
            
        Returns:
            DataFrame containing the CSV data
        """
        try:
            # Try different encodings
            encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(file_path, encoding=encoding)
                    logger.info(f"Successfully read {file_path} with encoding: {encoding}")
                    return df
                except UnicodeDecodeError:
                    continue
                    
            # If all encodings fail, try with error handling
            df = pd.read_csv(file_path, encoding='utf-8', errors='replace')
            logger.warning(f"Read {file_path} with error replacement")
            return df
            
        except Exception as e:
            logger.error(f"Failed to read CSV file {file_path}: {e}")
            return pd.DataFrame()
    
    def brute_force_comparison(self, file_a_path: str, file_b_path: str) -> List[ConflictRange]:
        """
        Perform robust brute force comparison between two CSV files.
        
        This algorithm:
        1. Loads both CSV files
        2. Compares row by row
        3. Identifies conflicting ranges
        4. Extracts conflict sections for AI analysis
        
        Args:
            file_a_path: Path to first CSV file
            file_b_path: Path to second CSV file
            
        Returns:
            List of ConflictRange objects representing differences
        """
        logger.info(f"Starting brute force comparison: {file_a_path} vs {file_b_path}")
        
        # Read both files
        df_a = self.read_csv_content(file_a_path)
        df_b = self.read_csv_content(file_b_path)
        
        if df_a.empty or df_b.empty:
            logger.error("One or both CSV files could not be read")
            return []
        
        conflicts = []
        
        # Normalize column names (strip whitespace, handle case)
        df_a.columns = df_a.columns.str.strip()
        df_b.columns = df_b.columns.str.strip()
        
        # Get common columns
        common_columns = list(set(df_a.columns) & set(df_b.columns))
        if not common_columns:
            logger.warning("No common columns found between files")
            return []
        
        logger.info(f"Comparing {len(common_columns)} common columns: {common_columns}")
        
        # Compare row by row
        max_rows = max(len(df_a), len(df_b))
        conflict_start = None
        conflict_rows_a = []
        conflict_rows_b = []
        
        for i in range(max_rows):
            row_a = df_a.iloc[i] if i < len(df_a) else pd.Series()
            row_b = df_b.iloc[i] if i < len(df_b) else pd.Series()
            
            # Check if rows are different
            rows_different = False
            
            if i >= len(df_a) or i >= len(df_b):
                # Different file lengths
                rows_different = True
            else:
                # Compare common columns
                for col in common_columns:
                    val_a = str(row_a.get(col, "")).strip()
                    val_b = str(row_b.get(col, "")).strip()
                    
                    if val_a != val_b:
                        rows_different = True
                        break
            
            if rows_different:
                # Start or continue conflict range
                if conflict_start is None:
                    conflict_start = i
                
                # Add rows to conflict sections
                if i < len(df_a):
                    row_data = ', '.join([f'{col}={row_a.get(col, "N/A")}' for col in common_columns])
                    conflict_rows_a.append(f"Row {i+1}: {row_data}")
                else:
                    conflict_rows_a.append(f"Row {i+1}: [FILE A ENDS]")
                
                if i < len(df_b):
                    row_data = ', '.join([f'{col}={row_b.get(col, "N/A")}' for col in common_columns])
                    conflict_rows_b.append(f"Row {i+1}: {row_data}")
                else:
                    conflict_rows_b.append(f"Row {i+1}: [FILE B ENDS]")
            
            else:
                # Rows are the same - end conflict range if one was active
                if conflict_start is not None:
                    # Create conflict range
                    conflict = ConflictRange(
                        start_row=conflict_start + 1,  # 1-based indexing
                        end_row=i,  # 1-based indexing
                        file_a_section="\n".join(conflict_rows_a),
                        file_b_section="\n".join(conflict_rows_b),
                        conflict_type="data_mismatch",
                        description=f"Conflicting data found in rows {conflict_start + 1} to {i}"
                    )
                    conflicts.append(conflict)
                    
                    # Reset for next conflict
                    conflict_start = None
                    conflict_rows_a = []
                    conflict_rows_b = []
        
        # Handle case where file ends with conflicts
        if conflict_start is not None:
            conflict = ConflictRange(
                start_row=conflict_start + 1,
                end_row=max_rows,
                file_a_section="\n".join(conflict_rows_a),
                file_b_section="\n".join(conflict_rows_b),
                conflict_type="data_mismatch",
                description=f"Conflicting data found in rows {conflict_start + 1} to {max_rows}"
            )
            conflicts.append(conflict)
        
        logger.info(f"Found {len(conflicts)} conflict ranges")
        return conflicts
    
    def _preprocess_conflict_data(self, conflict_text: str) -> str:
        """
        Enhanced aggressive preprocessing to remove noise and compress repetitive content.
        
        Optimizations:
        - Compress repeated stack traces with counter notation
        - Remove irrelevant JDK boilerplate
        - Focus on delta rows between File A and B
        - Up to 90% size reduction target
        
        Args:
            conflict_text: Raw conflict section text
            
        Returns:
            Aggressively preprocessed and compressed conflict text
        """
        lines = conflict_text.strip().split('\n')
        processed_lines = []
        
        # Track repetitive patterns for compression
        line_frequency = Counter()
        
        # Pattern detection for different types of noise
        self_time_pattern = re.compile(r'Self time.*?0\.0 ms.*?0\.0 ms.*?1')
        java_internal_pattern = re.compile(r'(java\.(lang|util|awt|io|net|security)|javax\.|sun\.|jdk\.internal\.)', re.IGNORECASE)
        
        # First pass: analyze frequencies and patterns
        significant_lines = []
        consecutive_groups = []
        current_group = []
        current_pattern = None
        
        for line in lines:
            line_clean = line.strip().strip('"')
            
            # Skip empty lines
            if not line_clean:
                continue
                
            # Detect pattern type
            if self_time_pattern.search(line_clean):
                pattern_type = "SELF_TIME_ZERO"
            elif java_internal_pattern.search(line_clean):
                pattern_type = f"JAVA_INTERNAL_{self._extract_java_class(line_clean)}"
            elif any(jdk_noise in line_clean.lower() for jdk_noise in ['compiledmethod', 'interpreter', 'c1 compilation', 'c2 compilation']):
                pattern_type = "JVM_COMPILATION"
            else:
                pattern_type = "SIGNIFICANT"
            
            # Group consecutive similar patterns
            if pattern_type == current_pattern:
                current_group.append(line_clean)
            else:
                # Save previous group
                if current_group:
                    consecutive_groups.append((current_pattern, current_group))
                # Start new group
                current_pattern = pattern_type
                current_group = [line_clean]
        
        # Add final group
        if current_group:
            consecutive_groups.append((current_pattern, current_group))
        
        # Second pass: compress groups aggressively
        for pattern_type, group in consecutive_groups:
            if pattern_type == "SELF_TIME_ZERO":
                if len(group) >= 3:
                    processed_lines.append(f"[COMPRESSED] {len(group)}x repeated 'Self time, 0.0 ms' entries (noise removed)")
                else:
                    # Keep small groups as-is for context
                    processed_lines.extend(group[:2])  # Max 2 entries
                    
            elif pattern_type.startswith("JAVA_INTERNAL_"):
                if len(group) >= 2:
                    class_name = pattern_type.replace("JAVA_INTERNAL_", "")
                    processed_lines.append(f"[COMPRESSED] {len(group)}x {class_name} internal calls (JDK boilerplate)")
                else:
                    processed_lines.extend(group)
                    
            elif pattern_type == "JVM_COMPILATION":
                if len(group) >= 2:
                    processed_lines.append(f"[COMPRESSED] {len(group)}x JVM compilation entries (system internals)")
                else:
                    processed_lines.extend(group)
                    
            elif pattern_type == "SIGNIFICANT":
                # Keep all significant application logic
                processed_lines.extend(group)
            
            else:
                # Keep unclassified patterns but limit size
                if len(group) > 5:
                    processed_lines.extend(group[:3])  # Keep first 3
                    processed_lines.append(f"[COMPRESSED] {len(group)-3} similar entries truncated")
                else:
                    processed_lines.extend(group)
        
        # Third pass: further delta optimization - keep only rows that show meaningful differences
        final_lines = []
        for line in processed_lines:
            # Skip extremely verbose low-value entries
            if any(noise_pattern in line.lower() for noise_pattern in [
                '0.0 ms (0%)', 'compiled method', 'interpreter', 'vtable stub', 
                'runtime stub', 'deoptimization', 'uncommon trap'
            ]) and '[COMPRESSED]' not in line:
                continue
                
            # Keep timing data that shows actual differences
            if any(value_pattern in line for value_pattern in [
                'ms (', '%)', 'hits', '[COMPRESSED]'
            ]):
                final_lines.append(line)
        
        return '\n'.join(final_lines)
    
    def _extract_java_class(self, line: str) -> str:
        """Extract simplified Java class pattern for compression."""
        if 'java.lang.' in line:
            return 'Lang'
        elif 'java.util.' in line:
            return 'Util'  
        elif 'java.awt.' in line:
            return 'AWT'
        elif 'java.io.' in line:
            return 'IO'
        elif 'java.net.' in line:
            return 'Net'
        elif 'javax.' in line:
            return 'Extension'
        elif 'sun.' in line:
            return 'Sun'
        elif 'jdk.internal.' in line:
            return 'JDK'
        else:
            return 'System'
    
    def _parse_stack_trace_line(self, csv_line: str) -> Optional[StackTraceMapping]:
        """
        Parse a CSV line to extract stack trace and timing information.
        
        Args:
            csv_line: Raw CSV line containing stack trace data
            
        Returns:
            StackTraceMapping object or None if parsing fails
        """
        try:
            # Parse CSV line - format: "Name","Total Time","Total Time (CPU)","Hits"
            parts = csv_line.strip().split('","')
            if len(parts) < 4:
                return None
            
            # Clean up quoted fields
            name = parts[0].strip(' "')
            total_time_str = parts[1].strip(' "')
            cpu_time_str = parts[2].strip(' "')
            hits_str = parts[3].strip(' "')
            
            # Extract timing values
            timing_data = {}
            
            # Parse total time (e.g., "130.5 ms (25%)")
            time_match = re.search(r'(\d+\.?\d*)\s*ms', total_time_str)
            timing_data['total_time'] = float(time_match.group(1)) if time_match else 0.0
            
            # Parse CPU time
            cpu_time_match = re.search(r'(\d+\.?\d*)\s*ms', cpu_time_str)
            timing_data['cpu_time'] = float(cpu_time_match.group(1)) if cpu_time_match else 0.0
            
            # Parse hits
            hits_match = re.search(r'(\d+)', hits_str)
            timing_data['hits'] = float(hits_match.group(1)) if hits_match else 1.0
            
            # Parse stack trace information from name field
            class_name, method_name, line_number = self._extract_stack_trace_info(name)
            
            return StackTraceMapping(
                full_function_path=name,
                class_name=class_name,
                method_name=method_name,
                line_number=line_number,
                timing_data=timing_data,
                raw_csv_line=csv_line
            )
            
        except Exception as e:
            logger.debug(f"Failed to parse stack trace line: {e}")
            return None
    
    def _extract_stack_trace_info(self, function_path: str) -> Tuple[str, str, Optional[str]]:
        """
        Extract class name, method name, and line number from function path.
        
        Args:
            function_path: Full function path (e.g., "java.awt.EventQueue.dispatchEventImpl(EventQueue.java:101)")
            
        Returns:
            Tuple of (class_name, method_name, line_number)
        """
        try:
            # Pattern for Java stack trace: package.Class.method(File.java:line)
            java_pattern = r'([a-zA-Z0-9._]+)\.([a-zA-Z0-9_<>$]+)\([^:]*:?(\d+)?\)'
            java_match = re.search(java_pattern, function_path)
            
            if java_match:
                full_class = java_match.group(1)
                method_name = java_match.group(2)
                line_number = java_match.group(3)
                
                # Extract simple class name from full package path
                class_name = full_class.split('.')[-1] if '.' in full_class else full_class
                
                return class_name, method_name, line_number
            
            # Fallback: try to extract method-like patterns
            method_pattern = r'([a-zA-Z0-9_]+)\.([a-zA-Z0-9_<>$]+)'
            method_match = re.search(method_pattern, function_path)
            
            if method_match:
                class_name = method_match.group(1)
                method_name = method_match.group(2)
                return class_name, method_name, None
            
            # Last resort: treat entire string as method name
            return "Unknown", function_path, None
            
        except Exception:
            return "Unknown", function_path, None
    
    def _extract_hotspots_from_conflicts(self, conflicts: List[ConflictRange]) -> List[HotspotInfo]:
        """
        Extract performance hotspots from conflict ranges with precise line-level mapping.
        Guaranteed to find hotspots when timing regressions exist.
        
        Args:
            conflicts: List of conflict ranges to analyze
            
        Returns:
            List of HotspotInfo objects sorted by impact
        """
        hotspots = []
        logger.info(f"Analyzing {len(conflicts)} conflict ranges for hotspot detection")
        
        for conflict_idx, conflict in enumerate(conflicts):
            # Parse lines from both files
            file_a_lines = [line.strip() for line in conflict.file_a_section.strip().split('\n') if line.strip()]
            file_b_lines = [line.strip() for line in conflict.file_b_section.strip().split('\n') if line.strip()]
            
            logger.debug(f"Conflict {conflict_idx}: {len(file_a_lines)} vs {len(file_b_lines)} lines")
            
            # Create dictionaries to match function names between files
            file_a_functions = {}
            file_b_functions = {}
            
            # Parse File A functions
            for line_idx, line in enumerate(file_a_lines):
                trace = self._parse_stack_trace_line(line)
                if trace and trace.timing_data.get('total_time', 0) > 0:
                    function_key = f"{trace.class_name}.{trace.method_name}"
                    if function_key not in file_a_functions:
                        file_a_functions[function_key] = []
                    file_a_functions[function_key].append((line_idx, trace, line))
            
            # Parse File B functions and find matches
            for line_idx, line in enumerate(file_b_lines):
                trace = self._parse_stack_trace_line(line)
                if trace and trace.timing_data.get('total_time', 0) > 0:
                    function_key = f"{trace.class_name}.{trace.method_name}"
                    if function_key not in file_b_functions:
                        file_b_functions[function_key] = []
                    file_b_functions[function_key].append((line_idx, trace, line))
            
            # Find timing differences between matching functions
            all_function_keys = set(file_a_functions.keys()) | set(file_b_functions.keys())
            
            for function_key in all_function_keys:
                file_a_entries = file_a_functions.get(function_key, [])
                file_b_entries = file_b_functions.get(function_key, [])
                
                # Compare timing for same function (take the entry with highest timing)
                if file_a_entries and file_b_entries:
                    # Use the entry with highest total time from each file
                    _, best_trace_a, best_line_a = max(file_a_entries, key=lambda x: x[1].timing_data.get('total_time', 0))
                    _, best_trace_b, best_line_b = max(file_b_entries, key=lambda x: x[1].timing_data.get('total_time', 0))
                    
                    time_a = best_trace_a.timing_data.get('total_time', 0.0)
                    time_b = best_trace_b.timing_data.get('total_time', 0.0)
                    
                    # Only consider meaningful timing differences (> 0.01ms or 1% change)
                    time_delta = time_b - time_a
                    percent_change = abs(time_delta / time_a) if time_a > 0 else float('inf')
                    
                    if abs(time_delta) > 0.01 or percent_change > 0.01:
                        regression_factor = (time_b / time_a) if time_a > 0 else float('inf')
                        
                        # Enhanced impact scoring: combine timing delta with regression factor
                        base_impact = abs(time_delta)
                        regression_multiplier = max(1.0, abs(regression_factor - 1.0))
                        impact_score = base_impact * regression_multiplier
                        
                        # Create precise line mapping
                        line_info = best_trace_a.line_number if best_trace_a.line_number else "unknown"
                        exact_location = f"{best_trace_a.class_name}.{best_trace_a.method_name}"
                        if best_trace_a.line_number:
                            exact_location += f":{best_trace_a.line_number}"
                        
                        hotspot = HotspotInfo(
                            function_name=exact_location,
                            class_name=best_trace_a.class_name,
                            method_name=best_trace_a.method_name,
                            line_number=line_info,
                            file_a_time=time_a,
                            file_b_time=time_b,
                            time_delta=time_delta,
                            regression_factor=regression_factor,
                            raw_line_a=best_line_a,
                            raw_line_b=best_line_b,
                            row_range=f"Rows {conflict.start_row}-{conflict.end_row}",
                            impact_score=impact_score
                        )
                        
                        hotspots.append(hotspot)
                        logger.debug(f"Hotspot detected: {exact_location} - {time_a}ms → {time_b}ms ({regression_factor:.2f}x)")
                
                # Also check for functions that appear only in one file (new or removed functions)
                elif file_a_entries and not file_b_entries:
                    # Function removed in File B
                    _, trace_a, line_a = max(file_a_entries, key=lambda x: x[1].timing_data.get('total_time', 0))
                    time_a = trace_a.timing_data.get('total_time', 0.0)
                    
                    if time_a > 0.1:  # Only significant timing functions
                        exact_location = f"{trace_a.class_name}.{trace_a.method_name}"
                        if trace_a.line_number:
                            exact_location += f":{trace_a.line_number}"
                        
                        hotspot = HotspotInfo(
                            function_name=exact_location,
                            class_name=trace_a.class_name,
                            method_name=trace_a.method_name,
                            line_number=trace_a.line_number,
                            file_a_time=time_a,
                            file_b_time=0.0,
                            time_delta=-time_a,
                            regression_factor=0.0,
                            raw_line_a=line_a,
                            raw_line_b="[Function removed]",
                            row_range=f"Rows {conflict.start_row}-{conflict.end_row}",
                            impact_score=time_a  # Removal impact equals original timing
                        )
                        hotspots.append(hotspot)
                
                elif file_b_entries and not file_a_entries:
                    # Function added in File B
                    _, trace_b, line_b = max(file_b_entries, key=lambda x: x[1].timing_data.get('total_time', 0))
                    time_b = trace_b.timing_data.get('total_time', 0.0)
                    
                    if time_b > 0.1:  # Only significant timing functions
                        exact_location = f"{trace_b.class_name}.{trace_b.method_name}"
                        if trace_b.line_number:
                            exact_location += f":{trace_b.line_number}"
                        
                        hotspot = HotspotInfo(
                            function_name=exact_location,
                            class_name=trace_b.class_name,
                            method_name=trace_b.method_name,
                            line_number=trace_b.line_number,
                            file_a_time=0.0,
                            file_b_time=time_b,
                            time_delta=time_b,
                            regression_factor=float('inf'),
                            raw_line_a="[Function added]",
                            raw_line_b=line_b,
                            row_range=f"Rows {conflict.start_row}-{conflict.end_row}",
                            impact_score=time_b * 2.0  # New function impact multiplied
                        )
                        hotspots.append(hotspot)
        
        # Sort by impact score (highest impact first)
        hotspots.sort(key=lambda h: h.impact_score, reverse=True)
        
        logger.info(f"Hotspot analysis complete: {len(hotspots)} performance hotspots detected")
        return hotspots
    
    def _generate_hotspot_report(self, hotspots: List[HotspotInfo], top_n: int = 10) -> str:
        """
        Generate precise line-level hotspot report with exact timing deltas.
        
        Args:
            hotspots: List of HotspotInfo objects
            top_n: Number of top hotspots to include in detail
            
        Returns:
            Developer-friendly formatted hotspot report with exact mappings
        """
        if not hotspots:
            return "\n## 🔥 Performance Hotspots Analysis\n\n**Hotspots Detected: 0** (No significant timing regressions found)\n"
        
        # Header with exact count
        report = f"""
## 🔥 Performance Hotspots Analysis (Line-Level Mapping)

**Hotspots Detected: {len(hotspots)}**

"""
        
        # Top-N ranking with exact format you specified
        display_count = min(top_n, len(hotspots))
        if display_count > 0:
            report += f"**Top {display_count} Hotspots:**\n\n"
            
            for i, hotspot in enumerate(hotspots[:display_count], 1):
                # Format timing change
                if hotspot.time_delta > 0:
                    timing_change = f"+{hotspot.time_delta:.1f}ms ({hotspot.regression_factor:.1f}x slower)"
                    change_type = "REGRESSION"
                elif hotspot.time_delta < 0:
                    timing_change = f"{hotspot.time_delta:.1f}ms ({1/hotspot.regression_factor:.1f}x faster)" if hotspot.regression_factor > 0 else f"{hotspot.time_delta:.1f}ms (optimized)"
                    change_type = "IMPROVEMENT"
                else:
                    timing_change = "no change"
                    change_type = "UNCHANGED"
                
                # Exact line mapping format as requested
                location = hotspot.function_name
                if hotspot.line_number and hotspot.line_number != "unknown":
                    location_detail = f"{hotspot.class_name}.{hotspot.method_name}({hotspot.class_name}.java:{hotspot.line_number})"
                else:
                    location_detail = f"{hotspot.class_name}.{hotspot.method_name}"
                
                report += f"{i}. {location_detail} {timing_change}\n"
                report += f"   File A: {hotspot.file_a_time:.1f}ms → File B: {hotspot.file_b_time:.1f}ms ({hotspot.regression_factor:.1f}x)\n\n"
        
        # Add detailed analysis section
        if display_count > 0:
            report += "### 📊 Detailed Timing Analysis\n\n"
            
            for i, hotspot in enumerate(hotspots[:display_count], 1):
                report += f"**{i}. {hotspot.class_name}.{hotspot.method_name}**\n"
                if hotspot.line_number and hotspot.line_number != "unknown":
                    report += f"   - **Location**: Line {hotspot.line_number}\n"
                report += f"   - **Timing**: {hotspot.file_a_time:.2f}ms → {hotspot.file_b_time:.2f}ms\n"
                report += f"   - **Delta**: {hotspot.time_delta:+.2f}ms\n"
                report += f"   - **Factor**: {hotspot.regression_factor:.2f}x\n"
                report += f"   - **Impact**: {hotspot.impact_score:.1f}\n\n"
        
        # Summary for remaining hotspots
        if len(hotspots) > top_n:
            report += f"**Additional {len(hotspots) - top_n} hotspots** detected with impact scores ranging from {hotspots[top_n].impact_score:.1f} to {hotspots[-1].impact_score:.1f}\n\n"
        
        # Add targeted fix recommendations
        report += self._generate_hotspot_recommendations(hotspots[:top_n])
        
        return report
    
    def _generate_hotspot_recommendations(self, top_hotspots: List[HotspotInfo]) -> str:
        """
        Generate developer-oriented recommendations with line-specific fixes.
        
        Args:
            top_hotspots: List of top hotspot issues
            
        Returns:
            Formatted recommendations string with precise technical guidance
        """
        if not top_hotspots:
            return ""
        
        recommendations = """
### 🛠️ Targeted Fix Suggestions (Line-Specific)

"""
        
        for i, hotspot in enumerate(top_hotspots[:5], 1):  # Top 5 recommendations
            # Get specific technical recommendation
            specific_fix = self._get_specific_recommendation(hotspot)
            
            # Format the exact structure you requested
            recommendations += f"**{hotspot.function_name}:** {specific_fix}\n\n"
        
        return recommendations
    
    def _get_specific_recommendation(self, hotspot) -> str:
        """
        Generate line-specific technical recommendations based on hotspot patterns.
        
        Args:
            hotspot: HotspotInfo object or function name string
            
        Returns:
            Specific technical fix recommendation
        """
        # Handle both HotspotInfo objects and string inputs
        if isinstance(hotspot, str):
            function_name = hotspot.lower()
            class_name = ""
            method_name = ""
            timing_delta = 0
            # Try to extract class and method from function name
            if '.' in hotspot:
                parts = hotspot.split('.')
                if len(parts) >= 2:
                    class_name = parts[-2].lower()
                    method_name = parts[-1].lower()
        else:
            function_name = hotspot.function_name.lower()
            class_name = hotspot.class_name.lower()
            method_name = hotspot.method_name.lower()
            timing_delta = hotspot.time_delta
        
        # Exact pattern matching for specific fix recommendations
        
        # Event Dispatch Thread issues
        if 'eventqueue' in class_name and 'dispatch' in method_name:
            if timing_delta > 50:
                return "Blocked by synchronized section → refactor lock granularity or use concurrent collections"
            else:
                return "Event processing overhead → batch events or optimize listener callbacks"
        
        # AWT/UI Threading
        elif 'awt' in class_name or 'toolkit' in class_name:
            if 'eventloop' in method_name or 'run' in method_name:
                return "IO-bound → replace with async channel read/write or use NIO selectors"
            elif 'paint' in method_name or 'draw' in method_name:
                return "Rendering bottleneck → optimize graphics operations or use double buffering"
            else:
                return "UI thread blocking → move heavy operations to background threads"
        
        # I/O Operations
        elif 'io' in class_name or 'stream' in method_name or 'read' in method_name or 'write' in method_name:
            return "I/O bottleneck → implement async I/O with NIO channels or increase buffer sizes"
        
        # Network/Socket operations
        elif 'socket' in class_name or 'network' in method_name or 'connection' in method_name:
            return "Network latency → implement connection pooling or use non-blocking sockets"
        
        # ActiveMQ/Messaging
        elif 'activemq' in class_name or 'broker' in class_name or 'message' in method_name:
            if timing_delta > 100:
                return "Message processing bottleneck → tune broker configuration or implement message batching"
            else:
                return "Messaging overhead → optimize serialization or reduce message size"
        
        # NIO Operations
        elif 'nio' in class_name or 'selector' in method_name or 'channel' in method_name:
            return "NIO selector blocking → optimize selector key handling or use multiple selector threads"
        
        # Thread Management
        elif 'thread' in class_name or 'executor' in method_name or 'pool' in method_name:
            return "Thread contention → adjust pool size or reduce synchronization scope"
        
        # Memory/GC related
        elif 'gc' in method_name or 'memory' in method_name or 'heap' in method_name:
            return "Memory pressure → tune GC parameters or reduce object allocations"
        
        # Generic loop/algorithmic hotspots
        elif 'run' in method_name and timing_delta > 10:
            return "Algorithmic hotspot in inner loop → cache results or avoid object creation inside loop"
        
        # Database/persistence
        elif 'sql' in class_name or 'database' in method_name or 'query' in method_name:
            return "Database query performance → add indexes, optimize queries, or implement caching"
        
        # Serialization
        elif 'serial' in method_name or 'marshal' in method_name:
            return "Serialization overhead → use faster serialization libraries or reduce payload size"
        
        # Generic performance regression
        elif timing_delta > 0:
            if timing_delta > 100:
                return "Significant performance regression → profile with JProfiler to identify exact bottleneck"
            elif timing_delta > 20:
                return "Moderate regression → check for new synchronization blocks or algorithm changes"
            else:
                return "Minor regression → review recent code changes for unintended side effects"
        
        # Performance improvement
        else:
            return "Performance improvement detected → validate correctness of optimizations"

    def _chunk_large_conflicts(self, preprocessed_conflicts: str, max_chunk_size: int = 20000) -> List[str]:
        """
        Split large conflicts into manageable chunks for AI processing.
        
        Args:
            preprocessed_conflicts: Preprocessed conflict text
            max_chunk_size: Maximum characters per chunk
            
        Returns:
            List of conflict chunks
        """
        if len(preprocessed_conflicts) <= max_chunk_size:
            return [preprocessed_conflicts]
        
        chunks = []
        lines = preprocessed_conflicts.split('\n')
        current_chunk = []
        current_size = 0
        
        for line in lines:
            line_size = len(line) + 1  # +1 for newline
            
            if current_size + line_size > max_chunk_size and current_chunk:
                # Finalize current chunk
                chunks.append('\n'.join(current_chunk))
                current_chunk = [line]
                current_size = line_size
            else:
                current_chunk.append(line)
                current_size += line_size
        
        # Add final chunk
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
        
        return chunks
    
    def _analyze_conflict_chunk_with_retry(self, chunk: str, chunk_info: str, file_a_name: str, file_b_name: str, max_retries: int = 3) -> str:
        """
        Analyze a single conflict chunk with AI including retry logic and multi-key support.
        
        Args:
            chunk: Preprocessed conflict chunk
            chunk_info: Information about chunk (e.g., "Part 1 of 3")
            file_a_name: Name of first file
            file_b_name: Name of second file
            max_retries: Maximum retry attempts for failed requests
            
        Returns:
            AI analysis response for this chunk
        """
        try:
            result = self._analyze_conflict_chunk(chunk, chunk_info, file_a_name, file_b_name)
            return result
        except Exception as e:
            logger.error(f"Analysis failed for {chunk_info}: {e}")
            return f"Analysis failed for {chunk_info}: {str(e)}"
    
    def _analyze_chunks_parallel(self, chunks: List[str], file_a_name: str, file_b_name: str, max_workers: int = None) -> List[str]:
        """
        Analyze multiple conflict chunks in parallel using multiple API keys for 3x speed improvement.
        
        Args:
            chunks: List of preprocessed conflict chunks
            file_a_name: Name of first file  
            file_b_name: Name of second file
            max_workers: Maximum parallel workers (auto-calculated based on available keys)
            
        Returns:
            List of AI analysis responses in order
        """
        # Calculate optimal worker count based on available API keys
        # Each key can handle 60 requests/minute, so we can run more workers for better utilization
        if max_workers is None:
            max_workers = len(self.ai_clients) * 10  # 10 workers per key to better utilize 60 req/min capacity
        
        chunk_responses = [""] * len(chunks)  # Pre-allocate to maintain order
        
        logger.info(f"Starting parallel analysis with {max_workers} workers across {len(self.ai_clients)} API keys")
        logger.info(f"Total capacity: {self.total_requests_per_minute} requests/minute")
        
        def analyze_chunk_wrapper(chunk_index_tuple):
            index, chunk = chunk_index_tuple
            chunk_info = f"Conflict Analysis Part {index + 1} of {len(chunks)} (Chunk {index + 1}/{len(chunks)})"
            
            logger.info(f"Analyzing chunk {index + 1}/{len(chunks)} in parallel")
            response = self._analyze_conflict_chunk_with_retry(chunk, chunk_info, file_a_name, file_b_name)
            return index, response
        
        # Use ThreadPoolExecutor for I/O-bound AI requests with increased concurrency
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all chunks with their indices
            indexed_chunks = [(i, chunk) for i, chunk in enumerate(chunks)]
            future_to_index = {executor.submit(analyze_chunk_wrapper, chunk_tuple): chunk_tuple[0] 
                              for chunk_tuple in indexed_chunks}
            
            # Collect results as they complete
            completed = 0
            for future in as_completed(future_to_index):
                try:
                    index, response = future.result()
                    chunk_responses[index] = f"## Conflict Analysis Part {index + 1} of {len(chunks)}\n\n{response}"
                    completed += 1
                    logger.info(f"Completed chunk {index + 1}/{len(chunks)} ({completed}/{len(chunks)} total)")
                except Exception as e:
                    index = future_to_index[future]
                    logger.error(f"Parallel processing failed for chunk {index + 1}: {e}")
                    chunk_responses[index] = f"## Conflict Analysis Part {index + 1} of {len(chunks)}\n\nAnalysis failed: {str(e)}"
        
        logger.info(f"Parallel chunk analysis completed using multi-key processing")
        return chunk_responses
    
    def _create_fast_summary_analysis(self, conflicts: List[ConflictRange], file_a_name: str, file_b_name: str) -> str:
        """
        Enhanced two-pass summarization mode with line-level hotspot mapping.
        
        First pass: Extract hotspots and create structured diff summary locally
        Second pass: Send compact summary with hotspots to AI for reasoning
        
        Args:
            conflicts: List of conflict ranges
            file_a_name: Name of first file
            file_b_name: Name of second file
            
        Returns:
            Fast AI analysis with hotspot mapping
        """
        logger.info("Fast mode: Extracting hotspots and creating structured summary for AI analysis")
        
        # Extract hotspots with line-level mapping
        hotspots = self._extract_hotspots_from_conflicts(conflicts)
        
        # Generate hotspot report
        hotspot_report = self._generate_hotspot_report(hotspots, top_n=10)
        
        # First pass: Analyze conflicts locally and create structured summary (keeping original logic)
        timing_changes = []
        function_changes = []
        thread_changes = []
        
        for i, conflict in enumerate(conflicts, 1):
            # Extract key metrics from conflict
            file_a_lines = conflict.file_a_section.split('\n')
            file_b_lines = conflict.file_b_section.split('\n')
            
            # Look for timing differences
            timing_pattern = re.compile(r'(\d+\.?\d*)\s*ms\s*\((\d+\.?\d*)%\)')
            
            for line_a, line_b in zip(file_a_lines, file_b_lines):
                if line_a.strip() != line_b.strip():
                    # Extract function names
                    func_a = line_a.split(',')[0].strip(' "') if ',' in line_a else line_a.strip()
                    func_b = line_b.split(',')[0].strip(' "') if ',' in line_b else line_b.strip()
                    
                    # Extract timing data
                    timing_a = timing_pattern.findall(line_a)
                    timing_b = timing_pattern.findall(line_b)
                    
                    if timing_a and timing_b:
                        time_a = float(timing_a[0][0])
                        time_b = float(timing_b[0][0])
                        if abs(time_a - time_b) > 0.1:  # Significant timing difference
                            timing_changes.append({
                                'function': func_a,
                                'time_a': time_a,
                                'time_b': time_b,
                                'delta': time_b - time_a,
                                'delta_percent': ((time_b - time_a) / time_a * 100) if time_a > 0 else 0
                            })
                    
                    if func_a != func_b:
                        function_changes.append({
                            'conflict_range': i,
                            'function_a': func_a,
                            'function_b': func_b
                        })
                    
                    # Detect thread-related changes
                    if any(thread_keyword in line_a.lower() or thread_keyword in line_b.lower() 
                           for thread_keyword in ['thread', 'worker', 'executor', 'pool']):
                        thread_changes.append({
                            'conflict_range': i,
                            'description': f"Thread behavior change: {func_a} -> {func_b}"
                        })
        
        # Create structured summary
        summary = f"""
# STRUCTURED DIFF SUMMARY

## Files Compared:
- File A: {file_a_name}
- File B: {file_b_name}

## Conflict Statistics:
- Total conflicts: {len(conflicts)}
- Timing changes detected: {len(timing_changes)}
- Function changes detected: {len(function_changes)}
- Thread-related changes: {len(thread_changes)}

## Major Timing Changes (>0.1ms difference):
"""
        
        # Add top 20 timing changes
        timing_changes.sort(key=lambda x: abs(x['delta']), reverse=True)
        for change in timing_changes[:20]:
            summary += f"- {change['function']}: {change['time_a']:.2f}ms → {change['time_b']:.2f}ms ({change['delta']:+.2f}ms, {change['delta_percent']:+.1f}%)\n"
        
        if len(timing_changes) > 20:
            summary += f"... and {len(timing_changes) - 20} more timing changes\n"
        
        summary += "\n## Function Changes:\n"
        for change in function_changes[:15]:
            summary += f"- Range {change['conflict_range']}: {change['function_a']} → {change['function_b']}\n"
        
        if len(function_changes) > 15:
            summary += f"... and {len(function_changes) - 15} more function changes\n"
        
        summary += "\n## Thread-Related Changes:\n"
        for change in thread_changes[:10]:
            summary += f"- Range {change['conflict_range']}: {change['description']}\n"
        
        if len(thread_changes) > 10:
            summary += f"... and {len(thread_changes) - 10} more thread changes\n"
        
        # Integrate hotspot report into summary
        summary += f"\n{hotspot_report}\n"
        
        # Second pass: Send compact summary with hotspots to AI
        logger.info(f"Fast mode: Sending structured summary with hotspots ({len(summary)} chars) to AI for analysis")
        
        prompt = f"""You are a Java profiling expert analyzing a STRUCTURED SUMMARY with LINE-LEVEL HOTSPOT MAPPING between two profiling datasets.

{summary}

### ENHANCED ANALYSIS TASK:
Using the hotspot mapping and structured summary above, provide comprehensive diagnostic insights:

1. **Hotspot-Specific Analysis**: Focus on the line-level hotspots identified above. For each major hotspot:
   - Validate the root cause hypothesis
   - Assess the business impact
   - Prioritize fix urgency

2. **Performance Impact Analysis**: What do the timing changes indicate? Are these improvements or regressions?

3. **Root Cause Deep Dive**: For the top hotspots, explain WHY these specific methods/lines show regression:
   - Threading model changes
   - I/O blocking vs non-blocking patterns  
   - CPU vs memory bottlenecks
   - JVM optimization differences
   - Synchronization overhead

4. **Critical Issues Prioritization**: Rank the hotspots by business impact and fix difficulty

5. **Line-Level Action Plan**: For each top hotspot, provide specific steps:
   - Exact code locations to examine (class.method:line)
   - Configuration parameters to check
   - Performance tests to run
   - Code review focus areas

6. **Targeted Fix Recommendations**: Build upon the hotspot recommendations with additional context from the overall analysis

### CONTEXT:
This is Java profiling data with precise line-level hotspot mapping. The hotspot analysis has already identified the exact methods and timing regressions. Focus on validating and expanding these insights with actionable developer guidance."""
        
        messages = [
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        try:
            # Use the new multi-key API request system
            response = self._make_api_request_with_retry(messages, max_retries=3, retry_different_key=True)
            
            # Add metadata about fast mode with hotspot report
            final_response = (
                f"# Fast Mode Analysis Report with Line-Level Hotspot Mapping\n\n"
                f"**Processing Mode:** Two-pass summarization (Fast Mode) + Hotspot Analysis\n"
                f"**Summary Size:** {len(summary)} characters (vs full data: {sum(len(c.file_a_section) + len(c.file_b_section) for c in conflicts)} characters)\n"
                f"**Hotspots Detected:** {len(hotspots)}\n"
                f"**Processing Time:** ~95% faster than full analysis\n\n"
                f"{hotspot_report}\n\n"
                f"---\n\n"
                f"## AI Analysis Results\n\n"
                f"{response}\n\n"
                f"---\n\n"
                f"## Technical Note\n"
                f"This analysis used fast mode with local hotspot extraction, structured summarization, and line-level mapping.\n"
                f"The hotspot analysis provides exact function/method locations for performance regressions.\n"
                f"For detailed line-by-line analysis, use standard mode with full preprocessing.\n"
            )
            
            logger.info("Fast mode analysis with hotspots completed successfully")
            return final_response
            
        except Exception as e:
            logger.error(f"Fast mode AI analysis failed: {e}")
            return f"Fast mode analysis failed: {str(e)}\n\nStructured summary was:\n{summary}"

    def _analyze_conflict_chunk(self, chunk: str, chunk_info: str, file_a_name: str, file_b_name: str) -> str:
        """Analyze a single conflict chunk with AI using multi-key system."""
        prompt = (
            f"You are a Java profiling and debugging assistant analyzing profiling data in CSV format.\n\n"
            f"The CSV sections contain stack traces of Java code execution and timing data.\n"
            f"Input has been preprocessed to remove noise and may be summarized/chunked to fit size limits.\n"
            f"Treat summarized patterns (e.g., '200 repeated Self time rows') as equivalent to the expanded rows when reasoning.\n\n"
            f"{chunk_info}\n\n"
            f"FILE COMPARISON DETAILS:\n"
            f"========================\n"
            f"- File A: {file_a_name}\n"
            f"- File B: {file_b_name}\n\n"
            f"DETECTED CONFLICTS:\n"
            f"{chunk}\n\n"
            f"### STRICT INSTRUCTIONS:\n"
            f"You must provide detailed, developer-oriented diagnostic guidance. Avoid generic recommendations.\n\n"
            f"1. **Conflict Summary**: List exact mismatched functions/rows and what changed\n"
            f"2. **Root Cause Hypothesis**: Explain in detail why these differences may occur (e.g., thread handling differences, blocking vs non-blocking calls, selector differences, CPU vs wall-clock time, threading model changes)\n"
            f"3. **Impact**: How it affects performance, stability, correctness - be specific about timing implications\n"
            f"4. **Debugging Steps**: Step-by-step checks a developer should perform in code, configuration, or environment\n"
            f"5. **Suggested Fixes**: Concrete actions, config/code changes to try - provide actual code-level hints, configuration parameters, concurrency handling improvements\n\n"
            f"### CONTEXT FOR ANALYSIS:\n"
            f"- These are Java profiling traces with execution timings\n"
            f"- Look for patterns like: blocking I/O vs non-blocking, thread pool differences, synchronization issues\n"
            f"- Identify if differences indicate performance degradation or improvements\n"
            f"- Consider ActiveMQ configuration, NIO handling, thread models\n"
            f"- Analyze if timing differences suggest CPU-bound vs IO-bound execution changes\n\n"
            f"Your goal: Give developer-oriented actionable insights with technical depth, not high-level summaries."
        )

        messages = [
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        try:
            # Use the new multi-key API request system
            response = self._make_api_request_with_retry(messages, max_retries=3, retry_different_key=True)
            return response
            
        except Exception as e:
            logger.error(f"AI analysis failed for chunk {chunk_info}: {e}")
            return f"AI analysis failed for {chunk_info} due to error: {str(e)}"

    def analyze_conflicts_with_ai(self, conflicts: List[ConflictRange], file_a_name: str, file_b_name: str, fast_mode: bool = False) -> str:
        """
        Analyze conflicts using Siemens AI API with preprocessing and compression.
        
        Args:
            conflicts: List of conflict ranges to analyze
            file_a_name: Name of first file
            file_b_name: Name of second file
            fast_mode: If True, use two-pass summarization for ~95% faster processing
            
        Returns:
            AI analysis response
        """
        if not conflicts:
            return "No conflicts found between the files. The CSV files are identical."
        
        # Fast mode: Use two-pass summarization for extremely fast analysis
        if fast_mode:
            logger.info("Using fast mode for analysis (two-pass summarization)")
            return self._create_fast_summary_analysis(conflicts, file_a_name, file_b_name)
        
        try:
            # Prepare conflict sections with preprocessing
            conflict_sections = []
            total_raw_size = 0
            
            for i, conflict in enumerate(conflicts, 1):
                # Preprocess conflict data to remove noise and compress repetitive content
                processed_file_a = self._preprocess_conflict_data(conflict.file_a_section)
                processed_file_b = self._preprocess_conflict_data(conflict.file_b_section)
                
                section = f"""
CONFLICT RANGE #{i} (Rows {conflict.start_row}-{conflict.end_row}):

File A ({file_a_name}):
{processed_file_a}

File B ({file_b_name}):
{processed_file_b}

Conflict Type: {conflict.conflict_type}
Description: {conflict.description}
{'='*80}
"""
                conflict_sections.append(section)
                total_raw_size += len(conflict.file_a_section) + len(conflict.file_b_section)
            
            all_conflicts = "\n".join(conflict_sections)
            compressed_size = len(all_conflicts)
            
            # Calculate compression percentage
            compression_percent = 100 - (compressed_size/total_raw_size)*100
            logger.info(f"Conflict data preprocessed: {total_raw_size} -> {compressed_size} chars ({compression_percent:.1f}% reduction)")
            
            # Performance Optimization: Larger chunks for better throughput
            # Siemens AI can handle up to ~32k tokens, using 18k chars (conservative estimate)
            max_chunk_size = 18000  # Increased from 5000 for ~3x fewer chunks and better performance
            
            if len(all_conflicts) <= max_chunk_size:
                # Small conflicts - send directly
                logger.info("Sending preprocessed conflicts directly to AI (within size limits)")
                
                prompt = (
                    f"You are a Java profiling and debugging assistant analyzing profiling data in CSV format.\n\n"
                    f"The CSV sections contain stack traces of Java code execution and timing data.\n"
                    f"Input has been preprocessed to remove noise and may be summarized/chunked to fit size limits.\n"
                    f"Treat summarized patterns (e.g., '200 repeated Self time rows') as equivalent to the expanded rows when reasoning.\n\n"
                    f"Here are the conflicting sections extracted after brute-force comparison:\n\n"
                    f"FILE COMPARISON DETAILS:\n"
                    f"========================\n"
                    f"- File A: {file_a_name}\n"
                    f"- File B: {file_b_name}\n\n"
                    f"DETECTED CONFLICTS:\n"
                    f"{all_conflicts}\n\n"
                    f"### STRICT INSTRUCTIONS:\n"
                    f"You must provide detailed, developer-oriented diagnostic guidance. Avoid generic recommendations.\n\n"
                    f"1. **Conflict Summary**: List exact mismatched functions/rows and what changed\n"
                    f"2. **Root Cause Hypothesis**: Explain in detail why these differences may occur (e.g., thread handling differences, blocking vs non-blocking calls, selector differences, CPU vs wall-clock time, threading model changes)\n"
                    f"3. **Impact**: How it affects performance, stability, correctness - be specific about timing implications\n"
                    f"4. **Debugging Steps**: Step-by-step checks a developer should perform in code, configuration, or environment\n"
                    f"5. **Suggested Fixes**: Concrete actions, config/code changes to try - provide actual code-level hints, configuration parameters, concurrency handling improvements\n\n"
                    f"### CONTEXT FOR ANALYSIS:\n"
                    f"- These are Java profiling traces with execution timings\n"
                    f"- Look for patterns like: blocking I/O vs non-blocking, thread pool differences, synchronization issues\n"
                    f"- Identify if differences indicate performance degradation or improvements\n"
                    f"- Consider ActiveMQ configuration, NIO handling, thread models\n"
                    f"- Analyze if timing differences suggest CPU-bound vs IO-bound execution changes\n\n"
                    f"Your goal: Give developer-oriented actionable insights with technical depth, not high-level summaries."
                )

                messages = [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]

                try:
                    logger.info("Sending conflicts to Siemens AI for analysis...")
                    
                    # Use the new multi-key API request system
                    ai_response = self._make_api_request_with_retry(messages, max_retries=3, retry_different_key=True)
                    logger.info("AI analysis completed successfully")
                    return ai_response
                    
                except Exception as e:
                    logger.error(f"AI analysis failed: {e}")
                    return f"AI analysis failed due to error: {str(e)}\n\nPreprocessed conflicts detected:\n{all_conflicts}"
            
            else:
                # Large conflicts - need chunking with parallel processing
                chunks = self._chunk_large_conflicts(all_conflicts, max_chunk_size)
                estimated_time_sequential = len(chunks) * 15  # ~15 seconds per chunk sequentially
                estimated_time_parallel = max(10, len(chunks) * 1.5)  # ~1.5 seconds per chunk with 10x faster API (60 req/min)
                
                logger.info(f"Large conflicts detected. Splitting into {len(chunks)} chunks for AI analysis")
                logger.info(f"Multi-key parallel processing: Using {len(self.ai_clients)} API keys ({self.total_requests_per_minute} requests/min capacity)")
                logger.info(f"Performance boost: Estimated time {estimated_time_parallel//60}m {estimated_time_parallel%60}s vs {estimated_time_sequential//60}m {estimated_time_sequential%60}s sequential (~{estimated_time_sequential//estimated_time_parallel}x faster)")
                
                # Use multi-key parallel processing for significant performance improvement  
                start_time = time.time()
                chunk_responses = self._analyze_chunks_parallel(chunks, file_a_name, file_b_name)  # Auto-calculate workers
                processing_time = time.time() - start_time
                
                logger.info(f"Multi-key parallel analysis completed in {processing_time:.1f}s ({len(chunks)} chunks)")
                logger.info(f"Speedup achieved: ~{estimated_time_sequential/processing_time:.1f}x faster than sequential processing")
                
                # Calculate compression percentage
                compression_percent = 100 - (compressed_size/total_raw_size)*100
                
                # Assemble final report
                final_report = (
                    f"# Complete Conflict Analysis Report\n\n"
                    f"**Files Compared:**\n"
                    f"- File A: {file_a_name}\n"
                    f"- File B: {file_b_name}\n\n"
                    f"**Analysis Summary:**\n"
                    f"- Total conflicts processed: {len(conflicts)}\n"
                    f"- Data compression achieved: {compression_percent:.1f}% size reduction\n"
                    f"- Analysis split into {len(chunks)} chunks due to size constraints\n"
                    f"- Multi-key parallel processing: {len(self.ai_clients)} API keys ({self.total_requests_per_minute} requests/min)\n"
                    f"- Processing time: {processing_time:.1f}s (~{estimated_time_sequential/processing_time:.1f}x faster than sequential)\n\n"
                    f"---\n\n"
                ) + "\n\n---\n\n".join(chunk_responses) + (
                    f"\n\n---\n\n"
                    f"## Consolidated Summary\n\n"
                    f"The analysis above has been split into {len(chunks)} parts due to the large size of the conflict data. \n"
                    f"Each part provides detailed technical analysis of specific conflict ranges. Review all parts \n"
                    f"for complete understanding of the differences between the two profiling datasets.\n\n"
                    f"**Key Analysis Areas Covered:**\n"
                    f"- Conflict identification and technical root causes\n"
                    f"- Performance impact assessment  \n"
                    f"- Developer debugging guidance\n"
                    f"- Specific fix recommendations\n"
                )
                
                logger.info(f"Complete conflict analysis assembled from {len(chunks)} chunks")
                return final_report
                
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return f"AI analysis failed due to error: {str(e)}\n\nPreprocessed conflicts detected:\n{all_conflicts}"
    
    def compare_and_analyze(self, file_a_path: str, file_b_path: str, file_a_name: str = None, file_b_name: str = None, fast_mode: bool = False) -> Dict[str, Any]:
        """
        Complete comparison and analysis workflow.
        
        Args:
            file_a_path: Path to first CSV file
            file_b_path: Path to second CSV file
            file_a_name: Display name for first file
            file_b_name: Display name for second file
            fast_mode: If True, use fast two-pass summarization mode
            
        Returns:
            Dictionary containing comparison results and AI analysis
        """
        # Use filenames if names not provided
        if not file_a_name:
            file_a_name = Path(file_a_path).name
        if not file_b_name:
            file_b_name = Path(file_b_path).name
        
        mode_info = "Fast Mode" if fast_mode else "Standard Mode"
        logger.info(f"Starting complete analysis ({mode_info}): {file_a_name} vs {file_b_name}")
        
        # Step 1: Brute force comparison
        conflicts = self.brute_force_comparison(file_a_path, file_b_path)
        
        # Step 2: AI analysis of conflicts with mode selection
        ai_analysis = self.analyze_conflicts_with_ai(conflicts, file_a_name, file_b_name, fast_mode=fast_mode)
        
        # Step 3: Prepare results
        results = {
            "file_a_name": file_a_name,
            "file_b_name": file_b_name,
            "conflict_count": len(conflicts),
            "conflicts": [
                {
                    "range": f"Rows {c.start_row}-{c.end_row}",
                    "type": c.conflict_type,
                    "description": c.description,
                    "file_a_section": c.file_a_section,
                    "file_b_section": c.file_b_section
                }
                for c in conflicts
            ],
            "ai_analysis": ai_analysis,
            "summary": {
                "total_conflicts": len(conflicts),
                "has_differences": len(conflicts) > 0,
                "analysis_timestamp": pd.Timestamp.now().isoformat()
            }
        }
        
        logger.info(f"Analysis complete: {len(conflicts)} conflicts found")
        return results


if __name__ == "__main__":
    # Test the comparison engine
    engine = CSVComparisonEngine()
    print("CSV Comparison Engine - Test Mode")
    print("="*50)
