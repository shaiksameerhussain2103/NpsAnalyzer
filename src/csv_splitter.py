"""
CSV File Splitter Module
An addon feature for splitting large CSV files into smaller manageable chunks.
This module provides functionality to split CSV files by rows, making them easier to process with AI/LLM systems.
"""

import csv
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import pandas as pd


class CSVSplitterError(Exception):
    """Custom exception for CSV splitting errors."""
    pass


class CSVSplitter:
    """
    A utility class for splitting large CSV files into smaller chunks.
    This is particularly useful for preparing data for AI/LLM processing.
    """
    
    def __init__(self, output_dir: str = "split_output"):
        """
        Initialize the CSV Splitter.
        
        Args:
            output_dir (str): Directory to save split files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Setup logging
        self.logger = self._setup_logging()
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration."""
        logger = logging.getLogger(f"{__name__}.CSVSplitter")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
    
    def analyze_csv_structure(self, csv_file: Union[str, Path]) -> Dict:
        """
        Analyze the structure of a CSV file to provide splitting recommendations.
        
        Args:
            csv_file: Path to the CSV file
            
        Returns:
            Dict: Analysis results with recommendations
        """
        try:
            self.logger.info(f"Analyzing CSV structure: {csv_file}")
            
            # Try different encodings
            encodings_to_try = ['utf-8', 'latin-1', 'cp1252']
            df = None
            
            for encoding in encodings_to_try:
                try:
                    df = pd.read_csv(csv_file, encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue
                    
            if df is None:
                raise CSVSplitterError("Could not read CSV file with any encoding")
            
            total_rows = len(df)
            total_columns = len(df.columns)
            
            # Calculate file size
            file_size = Path(csv_file).stat().st_size
            
            # Estimate memory usage
            memory_usage = df.memory_usage(deep=True).sum()
            
            # Recommend split sizes based on file characteristics
            recommended_rows_per_file = self._calculate_recommended_split_size(
                total_rows, file_size, memory_usage
            )
            
            analysis = {
                "file_path": str(csv_file),
                "total_rows": total_rows,
                "total_columns": total_columns,
                "column_names": list(df.columns),
                "file_size_bytes": file_size,
                "file_size_mb": round(file_size / (1024 * 1024), 2),
                "memory_usage_bytes": memory_usage,
                "memory_usage_mb": round(memory_usage / (1024 * 1024), 2),
                "recommended_rows_per_file": recommended_rows_per_file,
                "estimated_output_files": max(1, total_rows // recommended_rows_per_file),
                "data_types": df.dtypes.to_dict(),
                "sample_data": df.head(3).to_dict(orient='records')
            }
            
            self.logger.info(f"Analysis complete: {total_rows} rows, {total_columns} columns")
            return analysis
            
        except Exception as e:
            error_msg = f"Failed to analyze CSV file: {str(e)}"
            self.logger.error(error_msg)
            raise CSVSplitterError(error_msg) from e
    
    def _calculate_recommended_split_size(self, total_rows: int, file_size: int, 
                                        memory_usage: int) -> int:
        """Calculate recommended rows per file for splitting."""
        # Base recommendations
        if total_rows <= 100:
            return max(1, total_rows // 5)  # Very small files: 5 files max
        elif total_rows <= 1000:
            return 100  # Small files: 100 rows per file
        elif total_rows <= 10000:
            return 500  # Medium files: 500 rows per file
        elif total_rows <= 100000:
            return 1000  # Large files: 1000 rows per file
        else:
            return 2000  # Very large files: 2000 rows per file
    
    def split_by_rows(self, csv_file: Union[str, Path], rows_per_file: int = 100,
                     prefix: str = "split", include_headers: bool = True,
                     encoding: str = 'utf-8') -> List[Path]:
        """
        Split CSV file by number of rows.
        
        Args:
            csv_file: Path to the CSV file to split
            rows_per_file: Number of rows per output file
            prefix: Prefix for output file names
            include_headers: Whether to include headers in each split file
            encoding: File encoding
            
        Returns:
            List[Path]: List of created split files
        """
        try:
            self.logger.info(f"Splitting CSV by rows: {rows_per_file} rows per file")
            
            csv_path = Path(csv_file)
            if not csv_path.exists():
                raise CSVSplitterError(f"CSV file not found: {csv_path}")
            
            # Try different encodings
            encodings_to_try = [encoding, 'utf-8', 'latin-1', 'cp1252']
            df = None
            
            for enc in encodings_to_try:
                try:
                    df = pd.read_csv(csv_path, encoding=enc)
                    self.logger.info(f"Successfully read CSV with encoding: {enc}")
                    break
                except UnicodeDecodeError:
                    continue
                    
            if df is None:
                raise CSVSplitterError("Could not read CSV file with any encoding")
            
            total_rows = len(df)
            split_files = []
            
            # Calculate number of split files needed
            num_files = (total_rows + rows_per_file - 1) // rows_per_file
            
            for i in range(num_files):
                start_idx = i * rows_per_file
                end_idx = min((i + 1) * rows_per_file, total_rows)
                
                # Get chunk of data
                chunk = df.iloc[start_idx:end_idx]
                
                # Create output filename
                output_filename = f"{prefix}_part_{i+1:03d}_rows_{start_idx+1}_to_{end_idx}.csv"
                output_path = self.output_dir / output_filename
                
                # Save chunk to file
                chunk.to_csv(output_path, index=False, encoding='utf-8')
                split_files.append(output_path)
                
                self.logger.info(f"Created split file: {output_filename} ({len(chunk)} rows)")
            
            self.logger.info(f"Successfully split CSV into {len(split_files)} files")
            return split_files
            
        except Exception as e:
            error_msg = f"Failed to split CSV file: {str(e)}"
            self.logger.error(error_msg)
            raise CSVSplitterError(error_msg) from e
    
    def split_by_column_values(self, csv_file: Union[str, Path], column_name: str,
                              prefix: str = "split", encoding: str = 'utf-8') -> List[Path]:
        """
        Split CSV file based on unique values in a specific column.
        
        Args:
            csv_file: Path to the CSV file to split
            column_name: Column name to split by
            prefix: Prefix for output file names
            encoding: File encoding
            
        Returns:
            List[Path]: List of created split files
        """
        try:
            self.logger.info(f"Splitting CSV by column values: {column_name}")
            
            csv_path = Path(csv_file)
            if not csv_path.exists():
                raise CSVSplitterError(f"CSV file not found: {csv_path}")
            
            # Try different encodings
            encodings_to_try = [encoding, 'utf-8', 'latin-1', 'cp1252']
            df = None
            
            for enc in encodings_to_try:
                try:
                    df = pd.read_csv(csv_path, encoding=enc)
                    break
                except UnicodeDecodeError:
                    continue
                    
            if df is None:
                raise CSVSplitterError("Could not read CSV file with any encoding")
            
            if column_name not in df.columns:
                raise CSVSplitterError(f"Column '{column_name}' not found in CSV file")
            
            split_files = []
            unique_values = df[column_name].unique()
            
            for value in unique_values:
                # Filter data for this value
                filtered_df = df[df[column_name] == value]
                
                # Create safe filename
                safe_value = str(value).replace('/', '_').replace('\\', '_').replace(':', '_')
                safe_value = safe_value[:50]  # Limit filename length
                
                output_filename = f"{prefix}_by_{column_name}_{safe_value}.csv"
                output_path = self.output_dir / output_filename
                
                # Save filtered data
                filtered_df.to_csv(output_path, index=False, encoding='utf-8')
                split_files.append(output_path)
                
                self.logger.info(f"Created split file: {output_filename} ({len(filtered_df)} rows)")
            
            self.logger.info(f"Successfully split CSV into {len(split_files)} files by column values")
            return split_files
            
        except Exception as e:
            error_msg = f"Failed to split CSV by column values: {str(e)}"
            self.logger.error(error_msg)
            raise CSVSplitterError(error_msg) from e
    
    def split_by_size(self, csv_file: Union[str, Path], max_size_mb: float = 10.0,
                     prefix: str = "split", encoding: str = 'utf-8') -> List[Path]:
        """
        Split CSV file by maximum file size.
        
        Args:
            csv_file: Path to the CSV file to split
            max_size_mb: Maximum size per file in MB
            prefix: Prefix for output file names
            encoding: File encoding
            
        Returns:
            List[Path]: List of created split files
        """
        try:
            self.logger.info(f"Splitting CSV by size: {max_size_mb} MB per file")
            
            csv_path = Path(csv_file)
            if not csv_path.exists():
                raise CSVSplitterError(f"CSV file not found: {csv_path}")
            
            # Calculate approximate rows per file based on file size
            original_size_mb = csv_path.stat().st_size / (1024 * 1024)
            
            # Read a sample to estimate row size
            sample_df = pd.read_csv(csv_path, nrows=100, encoding=encoding)
            avg_row_size = csv_path.stat().st_size / len(pd.read_csv(csv_path, encoding=encoding))
            
            # Calculate rows per file
            max_size_bytes = max_size_mb * 1024 * 1024
            approx_rows_per_file = int(max_size_bytes / avg_row_size)
            
            # Use row-based splitting with calculated size
            return self.split_by_rows(csv_path, approx_rows_per_file, prefix, True, encoding)
            
        except Exception as e:
            error_msg = f"Failed to split CSV by size: {str(e)}"
            self.logger.error(error_msg)
            raise CSVSplitterError(error_msg) from e
    
    def split_by_hierarchical_structure(self, csv_file: Union[str, Path], 
                                       prefix: str = "hierarchical_split",
                                       encoding: str = 'utf-8') -> List[Path]:
        """
        Split CSV file based on hierarchical structure where main rows start with capital letters
        and their sub-rows (indented) belong to the same group.
        
        This is perfect for profiling data, call stacks, or any hierarchical data structure.
        
        Args:
            csv_file: Path to the CSV file to split
            prefix: Prefix for output file names
            encoding: File encoding
            
        Returns:
            List[Path]: List of created split files
        """
        try:
            self.logger.info(f"Splitting CSV by hierarchical structure")
            
            csv_path = Path(csv_file)
            if not csv_path.exists():
                raise CSVSplitterError(f"CSV file not found: {csv_path}")
            
            # Try different encodings
            encodings_to_try = [encoding, 'utf-8', 'latin-1', 'cp1252']
            df = None
            
            for enc in encodings_to_try:
                try:
                    df = pd.read_csv(csv_path, encoding=enc)
                    self.logger.info(f"Successfully read CSV with encoding: {enc}")
                    break
                except UnicodeDecodeError:
                    continue
                    
            if df is None:
                raise CSVSplitterError("Could not read CSV file with any encoding")
            
            split_files = []
            current_group = []
            current_group_name = None
            group_number = 0
            
            # Get the name column (assuming it's the first column)
            name_column = df.columns[0]
            
            for index, row in df.iterrows():
                name_value = str(row[name_column]).strip()
                
                # Remove quotes if present
                if name_value.startswith('"') and name_value.endswith('"'):
                    name_value = name_value[1:-1]
                
                # Check if this is a main heading (starts with capital letter, not indented)
                is_main_heading = (
                    len(name_value) > 0 and 
                    name_value[0].isupper() and 
                    not name_value.startswith(' ') and
                    not name_value.startswith('\t')
                )
                
                if is_main_heading:
                    # Save previous group if it exists
                    if current_group and current_group_name:
                        group_number += 1
                        split_file = self._save_hierarchical_group(
                            current_group, current_group_name, group_number, prefix, df.columns
                        )
                        split_files.append(split_file)
                        self.logger.info(f"Created split file for '{current_group_name}': {split_file.name} ({len(current_group)} rows)")
                    
                    # Start new group
                    current_group = [row]
                    current_group_name = name_value
                else:
                    # Add to current group (sub-row)
                    if current_group_name:  # Only add if we have a main heading
                        current_group.append(row)
            
            # Save the last group
            if current_group and current_group_name:
                group_number += 1
                split_file = self._save_hierarchical_group(
                    current_group, current_group_name, group_number, prefix, df.columns
                )
                split_files.append(split_file)
                self.logger.info(f"Created split file for '{current_group_name}': {split_file.name} ({len(current_group)} rows)")
            
            self.logger.info(f"Successfully split CSV into {len(split_files)} hierarchical groups")
            return split_files
            
        except Exception as e:
            error_msg = f"Failed to split CSV by hierarchical structure: {str(e)}"
            self.logger.error(error_msg)
            raise CSVSplitterError(error_msg) from e
    
    def _save_hierarchical_group(self, group_rows: List, group_name: str, 
                                group_number: int, prefix: str, columns) -> Path:
        """
        Save a hierarchical group to a CSV file.
        
        Args:
            group_rows: List of rows belonging to this group
            group_name: Name of the main heading
            group_number: Sequential number for this group
            prefix: File prefix
            columns: Column names
            
        Returns:
            Path: Path to the saved file
        """
        # Create safe filename from group name
        safe_group_name = group_name.replace('/', '_').replace('\\', '_').replace(':', '_')
        safe_group_name = safe_group_name.replace('"', '').replace("'", '')
        safe_group_name = ''.join(c for c in safe_group_name if c.isalnum() or c in '-_()[]')
        safe_group_name = safe_group_name[:50]  # Limit length
        
        # Create filename
        output_filename = f"{prefix}_group_{group_number:03d}_{safe_group_name}.csv"
        output_path = self.output_dir / output_filename
        
        # Create DataFrame from group rows
        group_df = pd.DataFrame(group_rows, columns=columns)
        
        # Save to file
        group_df.to_csv(output_path, index=False, encoding='utf-8')
        
        return output_path
    
    def create_split_manifest(self, split_files: List[Path], original_file: Union[str, Path]) -> Path:
        """
        Create a manifest file containing information about the split operation.
        
        Args:
            split_files: List of split file paths
            original_file: Path to the original file
            
        Returns:
            Path: Path to the manifest file
        """
        try:
            manifest_data = {
                "original_file": str(original_file),
                "split_timestamp": pd.Timestamp.now().isoformat(),
                "total_split_files": len(split_files),
                "split_files": []
            }
            
            for i, split_file in enumerate(split_files):
                file_info = {
                    "file_number": i + 1,
                    "filename": split_file.name,
                    "file_path": str(split_file),
                    "file_size_bytes": split_file.stat().st_size,
                    "file_size_mb": round(split_file.stat().st_size / (1024 * 1024), 2)
                }
                
                # Try to get row count
                try:
                    df = pd.read_csv(split_file)
                    file_info["row_count"] = len(df)
                    file_info["column_count"] = len(df.columns)
                except:
                    file_info["row_count"] = "unknown"
                    file_info["column_count"] = "unknown"
                
                manifest_data["split_files"].append(file_info)
            
            # Save manifest
            manifest_path = self.output_dir / "split_manifest.json"
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Created split manifest: {manifest_path}")
            return manifest_path
            
        except Exception as e:
            error_msg = f"Failed to create split manifest: {str(e)}"
            self.logger.error(error_msg)
            raise CSVSplitterError(error_msg) from e

    def split_by_brute_force_line_by_line(self, csv_file: Union[str, Path], prefix: str = "split") -> List[Path]:
        """
        Split CSV file by traversing line by line and identifying main headings that start with capital letters.
        This is a brute force approach that processes the file character by character to handle quoted fields properly.
        
        Args:
            csv_file: Path to the CSV file to split
            prefix: Prefix for output files
            
        Returns:
            List[Path]: Paths to the split files
        """
        try:
            csv_file = Path(csv_file)
            if not csv_file.exists():
                raise CSVSplitterError(f"CSV file not found: {csv_file}")
            
            self.logger.info(f"Starting brute force line-by-line split of: {csv_file}")
            
            split_files = []
            current_group_lines = []
            current_group_name = None
            group_number = 0
            header_line = None
            
            # Read file line by line
            with open(csv_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if not lines:
                raise CSVSplitterError("CSV file is empty")
            
            # First line is header
            header_line = lines[0].strip()
            self.logger.info(f"Header: {header_line}")
            
            # Process each data line
            for line_num, line in enumerate(lines[1:], start=2):
                line = line.strip()
                if not line:  # Skip empty lines
                    continue
                
                # Parse the first column value to check if it's a main heading
                first_column_value = self._extract_first_column_value(line)
                
                # Check if this is a main heading (starts with capital letter and no leading spaces)
                is_main_heading = self._is_main_heading_brute_force(first_column_value)
                
                if is_main_heading:
                    # Save previous group if it exists
                    if current_group_lines and current_group_name:
                        group_number += 1
                        split_file = self._save_brute_force_group(
                            current_group_lines, current_group_name, group_number, prefix, header_line
                        )
                        split_files.append(split_file)
                        self.logger.info(f"Created split file for '{current_group_name}': {split_file.name} ({len(current_group_lines)} lines)")
                    
                    # Start new group
                    current_group_lines = [line]
                    current_group_name = first_column_value
                    self.logger.debug(f"Started new group: '{current_group_name}' at line {line_num}")
                else:
                    # Add to current group (sub-row)
                    if current_group_name:  # Only add if we have a main heading
                        current_group_lines.append(line)
                    else:
                        # This shouldn't happen if CSV is well-formed, but handle gracefully
                        self.logger.warning(f"Found sub-row without main heading at line {line_num}: {line[:50]}...")
            
            # Save the last group
            if current_group_lines and current_group_name:
                group_number += 1
                split_file = self._save_brute_force_group(
                    current_group_lines, current_group_name, group_number, prefix, header_line
                )
                split_files.append(split_file)
                self.logger.info(f"Created split file for '{current_group_name}': {split_file.name} ({len(current_group_lines)} lines)")
            
            self.logger.info(f"Successfully split CSV into {len(split_files)} groups using brute force method")
            return split_files
            
        except Exception as e:
            error_msg = f"Failed to split CSV by brute force line-by-line: {str(e)}"
            self.logger.error(error_msg)
            raise CSVSplitterError(error_msg) from e
    
    def _extract_first_column_value(self, line: str) -> str:
        """
        Extract the first column value from a CSV line, handling quoted fields properly.
        PRESERVES original spacing/indentation.
        
        Args:
            line: CSV line to parse
            
        Returns:
            str: First column value with quotes removed but spacing preserved
        """
        if not line:
            return ""
        
        # Handle quoted fields
        if line.startswith('"'):
            # Find the closing quote
            end_quote_pos = 1
            while end_quote_pos < len(line):
                if line[end_quote_pos] == '"':
                    # Check if it's an escaped quote (double quote)
                    if end_quote_pos + 1 < len(line) and line[end_quote_pos + 1] == '"':
                        end_quote_pos += 2  # Skip escaped quote
                        continue
                    else:
                        # Found closing quote
                        return line[1:end_quote_pos].replace('""', '"')  # Preserve spacing
                end_quote_pos += 1
            
            # If we reach here, quote was not closed properly
            # Return everything after the opening quote
            return line[1:]  # Preserve spacing
        else:
            # Not quoted, find first comma
            comma_pos = line.find(',')
            if comma_pos != -1:
                return line[:comma_pos]  # Preserve spacing
            else:
                return line  # Preserve spacing
    
    def _is_main_heading_brute_force(self, value: str) -> bool:
        """
        Determine if a value represents a main heading based on brute force criteria.
        Main headings start with capital letters and have NO leading spaces.
        
        Args:
            value: The value to check
            
        Returns:
            bool: True if this is a main heading
        """
        if not value:
            return False
        
        # Remove any quotes but preserve original spacing
        clean_value = value.strip('"').strip("'")
        
        if not clean_value:
            return False
        
        # Check if the value starts with any spaces (indicating it's a sub-row)
        if clean_value.startswith(' ') or clean_value.startswith('\t'):
            return False
        
        # Check if first character is a capital letter
        first_char = clean_value[0]
        
        # Main heading criteria:
        # 1. First character must be uppercase letter
        # 2. Must not start with spaces (already checked above)
        # 3. Should not be "Self time" (this is always a sub-row)
        if first_char.isupper() and first_char.isalpha():
            # Special case: "Self time" is never a main heading
            if clean_value.strip() == "Self time":
                return False
            return True
        
        return False
    
    def _save_brute_force_group(self, group_lines: List[str], group_name: str, 
                               group_number: int, prefix: str, header_line: str) -> Path:
        """
        Save a brute force group to a CSV file.
        
        Args:
            group_lines: List of CSV lines belonging to this group
            group_name: Name of the main heading
            group_number: Sequential number for this group
            prefix: File prefix
            header_line: CSV header line
            
        Returns:
            Path: Path to the saved file
        """
        # Create safe filename from group name
        safe_group_name = group_name.replace('/', '_').replace('\\', '_').replace(':', '_')
        safe_group_name = safe_group_name.replace('"', '').replace("'", '')
        safe_group_name = ''.join(c for c in safe_group_name if c.isalnum() or c in '-_()[]')
        safe_group_name = safe_group_name[:50]  # Limit length
        
        # Create filename
        output_filename = f"{prefix}_brute_force_{group_number:03d}_{safe_group_name}.csv"
        output_path = self.output_dir / output_filename
        
        # Write the file
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            # Write header
            f.write(header_line + '\n')
            # Write group lines
            for line in group_lines:
                f.write(line + '\n')
        
        return output_path


if __name__ == "__main__":
    # Example usage
    splitter = CSVSplitter()
    
    try:
        # Analyze structure
        analysis = splitter.analyze_csv_structure("sample.csv")
        print("CSV Analysis:", analysis)
        
        # Split by rows
        split_files = splitter.split_by_rows("sample.csv", rows_per_file=100)
        print(f"Created {len(split_files)} split files")
        
        # Create manifest
        manifest = splitter.create_split_manifest(split_files, "sample.csv")
        print(f"Manifest created: {manifest}")
        
    except CSVSplitterError as e:
        print(f"Split operation failed: {e}")
