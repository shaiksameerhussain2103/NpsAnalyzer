"""
File Converter Application
A production-ready application to convert CSV and XML files to JSON format.
"""

import json
import logging
import os
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Union

import pandas as pd
import xmltodict
from lxml import etree

# Import the CSV splitter addon
try:
    from .csv_splitter import CSVSplitter, CSVSplitterError
except ImportError:
    from csv_splitter import CSVSplitter, CSVSplitterError


class FileConverterError(Exception):
    """Custom exception for file conversion errors."""
    pass


class FileConverter:
    """
    A robust file converter class that handles CSV and XML to JSON conversion.
    """
    
    def __init__(self, output_dir: str = "output"):
        """
        Initialize the FileConverter.
        
        Args:
            output_dir (str): Directory to save converted files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Initialize CSV splitter for preprocessing
        self.csv_splitter = CSVSplitter(output_dir=str(self.output_dir / "split_files"))
        
        # Setup logging
        self.logger = self._setup_logging()
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration."""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
    
    def validate_file(self, file_path: Union[str, Path]) -> None:
        """
        Validate if the file exists and has a supported extension.
        
        Args:
            file_path: Path to the file to validate
            
        Raises:
            FileConverterError: If file doesn't exist or has unsupported extension
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileConverterError(f"File not found: {file_path}")
            
        if not file_path.is_file():
            raise FileConverterError(f"Path is not a file: {file_path}")
            
        supported_extensions = {'.csv', '.xml'}
        if file_path.suffix.lower() not in supported_extensions:
            raise FileConverterError(
                f"Unsupported file type: {file_path.suffix}. "
                f"Supported types: {', '.join(supported_extensions)}"
            )
    
    def csv_to_json(self, csv_file: Union[str, Path], encoding: str = 'utf-8') -> Dict:
        """
        Convert CSV file to JSON format.
        
        Args:
            csv_file: Path to the CSV file
            encoding: File encoding (default: utf-8)
            
        Returns:
            Dict: JSON representation of the CSV data
            
        Raises:
            FileConverterError: If conversion fails
        """
        try:
            self.logger.info(f"Converting CSV file: {csv_file}")
            
            # Try different encodings if utf-8 fails
            encodings_to_try = [encoding, 'utf-8', 'latin-1', 'cp1252']
            df = None
            
            for enc in encodings_to_try:
                try:
                    df = pd.read_csv(csv_file, encoding=enc)
                    self.logger.info(f"Successfully read CSV with encoding: {enc}")
                    break
                except UnicodeDecodeError:
                    continue
                    
            if df is None:
                raise FileConverterError("Could not read CSV file with any encoding")
            
            # Handle missing values
            df = df.fillna("")
            
            # Convert to JSON format
            json_data = {
                "metadata": {
                    "source_file": str(csv_file),
                    "total_records": len(df),
                    "columns": list(df.columns),
                    "file_type": "csv"
                },
                "data": df.to_dict(orient='records')
            }
            
            self.logger.info(f"Successfully converted CSV with {len(df)} records")
            return json_data
            
        except Exception as e:
            error_msg = f"Failed to convert CSV file: {str(e)}"
            self.logger.error(error_msg)
            raise FileConverterError(error_msg) from e
    
    def xml_to_json(self, xml_file: Union[str, Path]) -> Dict:
        """
        Convert XML file to JSON format.
        
        Args:
            xml_file: Path to the XML file
            
        Returns:
            Dict: JSON representation of the XML data
            
        Raises:
            FileConverterError: If conversion fails
        """
        try:
            self.logger.info(f"Converting XML file: {xml_file}")
            
            with open(xml_file, 'r', encoding='utf-8') as file:
                xml_content = file.read()
            
            # Parse XML using xmltodict
            xml_dict = xmltodict.parse(xml_content)
            
            # Create structured JSON
            json_data = {
                "metadata": {
                    "source_file": str(xml_file),
                    "file_type": "xml",
                    "root_element": list(xml_dict.keys())[0] if xml_dict else None
                },
                "data": xml_dict
            }
            
            self.logger.info("Successfully converted XML file")
            return json_data
            
        except Exception as e:
            error_msg = f"Failed to convert XML file: {str(e)}"
            self.logger.error(error_msg)
            raise FileConverterError(error_msg) from e
    
    def convert_file(self, input_file: Union[str, Path], 
                    output_file: Optional[Union[str, Path]] = None,
                    encoding: str = 'utf-8') -> Path:
        """
        Convert a file (CSV or XML) to JSON format.
        
        Args:
            input_file: Path to the input file
            output_file: Path for the output JSON file (optional)
            encoding: File encoding for CSV files
            
        Returns:
            Path: Path to the generated JSON file
            
        Raises:
            FileConverterError: If conversion fails
        """
        input_path = Path(input_file)
        self.validate_file(input_path)
        
        # Generate output filename if not provided
        if output_file is None:
            output_file = self.output_dir / f"{input_path.stem}.json"
        else:
            output_file = Path(output_file)
        
        try:
            # Convert based on file extension
            if input_path.suffix.lower() == '.csv':
                json_data = self.csv_to_json(input_path, encoding)
            elif input_path.suffix.lower() == '.xml':
                json_data = self.xml_to_json(input_path)
            else:
                raise FileConverterError(f"Unsupported file type: {input_path.suffix}")
            
            # Write JSON to file
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Conversion completed. Output saved to: {output_file}")
            return output_file
            
        except Exception as e:
            error_msg = f"Conversion failed: {str(e)}"
            self.logger.error(error_msg)
            raise FileConverterError(error_msg) from e
    
    def batch_convert(self, input_dir: Union[str, Path], 
                     file_pattern: str = "*") -> List[Path]:
        """
        Convert multiple files in a directory.
        
        Args:
            input_dir: Directory containing files to convert
            file_pattern: Pattern to match files (default: "*")
            
        Returns:
            List[Path]: List of generated JSON files
        """
        input_path = Path(input_dir)
        if not input_path.is_dir():
            raise FileConverterError(f"Directory not found: {input_path}")
        
        converted_files = []
        supported_extensions = {'.csv', '.xml'}
        
        for file_path in input_path.glob(file_pattern):
            if file_path.suffix.lower() in supported_extensions:
                try:
                    output_file = self.convert_file(file_path)
                    converted_files.append(output_file)
                except FileConverterError as e:
                    self.logger.error(f"Failed to convert {file_path}: {e}")
                    continue
        
        self.logger.info(f"Batch conversion completed. {len(converted_files)} files converted.")
        return converted_files
    
    def analyze_csv_for_splitting(self, csv_file: Union[str, Path]) -> Dict:
        """
        Analyze CSV file structure to provide splitting recommendations.
        
        Args:
            csv_file: Path to the CSV file to analyze
            
        Returns:
            Dict: Analysis results with splitting recommendations
        """
        try:
            self.validate_file(csv_file)
            if Path(csv_file).suffix.lower() != '.csv':
                raise FileConverterError("File splitting is only supported for CSV files")
            
            analysis = self.csv_splitter.analyze_csv_structure(csv_file)
            self.logger.info(f"CSV analysis completed for: {csv_file}")
            return analysis
            
        except CSVSplitterError as e:
            error_msg = f"CSV analysis failed: {str(e)}"
            self.logger.error(error_msg)
            raise FileConverterError(error_msg) from e
    
    def split_csv_file(self, csv_file: Union[str, Path], split_method: str = "rows",
                      **kwargs) -> Dict:
        """
        Split a CSV file into smaller chunks for easier AI/LLM processing.
        
        Args:
            csv_file: Path to the CSV file to split
            split_method: Method to use for splitting ("rows", "size", "column", "hierarchical", "brute_force")
            **kwargs: Additional arguments for splitting methods
                - rows_per_file: Number of rows per file (for "rows" method)
                - max_size_mb: Maximum file size in MB (for "size" method)
                - column_name: Column name to split by (for "column" method)
                - prefix: Prefix for output filenames
                - encoding: File encoding
        
        Returns:
            Dict: Results containing split files and manifest information
        """
        try:
            self.validate_file(csv_file)
            if Path(csv_file).suffix.lower() != '.csv':
                raise FileConverterError("File splitting is only supported for CSV files")
            
            self.logger.info(f"Starting CSV split operation: {split_method} method")
            
            # Get parameters with defaults
            prefix = kwargs.get('prefix', Path(csv_file).stem)
            encoding = kwargs.get('encoding', 'utf-8')
            
            split_files = []
            
            if split_method == "rows":
                rows_per_file = kwargs.get('rows_per_file', 100)
                split_files = self.csv_splitter.split_by_rows(
                    csv_file, rows_per_file, prefix, True, encoding
                )
                
            elif split_method == "size":
                max_size_mb = kwargs.get('max_size_mb', 10.0)
                split_files = self.csv_splitter.split_by_size(
                    csv_file, max_size_mb, prefix, encoding
                )
                
            elif split_method == "column":
                column_name = kwargs.get('column_name')
                if not column_name:
                    raise FileConverterError("column_name is required for column-based splitting")
                split_files = self.csv_splitter.split_by_column_values(
                    csv_file, column_name, prefix, encoding
                )
                
            elif split_method == "hierarchical":
                split_files = self.csv_splitter.split_by_hierarchical_structure(
                    csv_file, prefix, encoding
                )
                
            elif split_method == "brute_force":
                split_files = self.csv_splitter.split_by_brute_force_line_by_line(
                    csv_file, prefix
                )
                
            else:
                raise FileConverterError(f"Unsupported split method: {split_method}")
            
            # Create manifest
            manifest_path = self.csv_splitter.create_split_manifest(split_files, csv_file)
            
            # Prepare results
            results = {
                "original_file": str(csv_file),
                "split_method": split_method,
                "total_split_files": len(split_files),
                "split_files": [str(f) for f in split_files],
                "manifest_file": str(manifest_path),
                "output_directory": str(self.csv_splitter.output_dir)
            }
            
            self.logger.info(f"CSV split completed: {len(split_files)} files created")
            return results
            
        except CSVSplitterError as e:
            error_msg = f"CSV splitting failed: {str(e)}"
            self.logger.error(error_msg)
            raise FileConverterError(error_msg) from e
    
    def split_and_convert_csv(self, csv_file: Union[str, Path], split_method: str = "rows",
                             convert_splits: bool = True, **kwargs) -> Dict:
        """
        Split CSV file and optionally convert split files to JSON.
        
        Args:
            csv_file: Path to the CSV file
            split_method: Method to use for splitting
            convert_splits: Whether to convert split files to JSON
            **kwargs: Additional arguments for splitting
            
        Returns:
            Dict: Results containing split files and converted JSON files
        """
        try:
            # First split the file
            split_results = self.split_csv_file(csv_file, split_method, **kwargs)
            
            converted_files = []
            
            if convert_splits:
                self.logger.info("Converting split files to JSON...")
                
                for split_file_path in split_results["split_files"]:
                    try:
                        json_file = self.convert_file(split_file_path, encoding=kwargs.get('encoding', 'utf-8'))
                        converted_files.append(str(json_file))
                    except Exception as e:
                        self.logger.warning(f"Failed to convert {split_file_path}: {e}")
            
            # Update results
            split_results["converted_json_files"] = converted_files
            split_results["total_json_files"] = len(converted_files)
            
            self.logger.info(f"Split and convert completed: {len(converted_files)} JSON files created")
            return split_results
            
        except Exception as e:
            error_msg = f"Split and convert operation failed: {str(e)}"
            self.logger.error(error_msg)
            raise FileConverterError(error_msg) from e


if __name__ == "__main__":
    # Example usage
    converter = FileConverter()
    
    # Example CSV conversion
    try:
        result = converter.convert_file("sample.csv")
        print(f"Conversion successful: {result}")
    except FileConverterError as e:
        print(f"Conversion failed: {e}")
