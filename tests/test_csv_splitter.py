"""
Unit tests for the CSV splitter module.
"""

import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd
import pytest

from src.csv_splitter import CSVSplitter, CSVSplitterError


class TestCSVSplitter(unittest.TestCase):
    """Test cases for CSVSplitter class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.splitter = CSVSplitter(output_dir="test_split_output")
        self.test_dir = Path("test_split_output")
        self.test_dir.mkdir(exist_ok=True)
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up test files
        if self.test_dir.exists():
            for file in self.test_dir.glob("*"):
                if file.is_file():
                    file.unlink()
            self.test_dir.rmdir()
    
    def create_test_csv(self, filename: str = "test.csv", rows: int = 100) -> Path:
        """Create a test CSV file with specified number of rows."""
        departments = ['Engineering', 'Marketing', 'Sales', 'HR', 'Finance']
        test_data = {
            'ID': range(1, rows + 1),
            'Name': [f'Person_{i}' for i in range(1, rows + 1)],
            'Age': [20 + (i % 50) for i in range(rows)],
            'City': [f'City_{i % 10}' for i in range(rows)],
            'Department': [departments[i % 5] for i in range(rows)]
        }
        df = pd.DataFrame(test_data)
        
        csv_path = self.test_dir / filename
        df.to_csv(csv_path, index=False)
        return csv_path
    
    def test_analyze_csv_structure(self):
        """Test CSV structure analysis."""
        csv_file = self.create_test_csv("test_analysis.csv", 50)
        
        analysis = self.splitter.analyze_csv_structure(csv_file)
        
        # Check analysis results
        self.assertEqual(analysis['total_rows'], 50)
        self.assertEqual(analysis['total_columns'], 5)
        self.assertIn('ID', analysis['column_names'])
        self.assertIn('Name', analysis['column_names'])
        self.assertGreater(analysis['file_size_bytes'], 0)
        self.assertGreater(analysis['recommended_rows_per_file'], 0)
        self.assertIn('sample_data', analysis)
    
    def test_split_by_rows(self):
        """Test splitting CSV by number of rows."""
        csv_file = self.create_test_csv("test_split_rows.csv", 150)
        
        split_files = self.splitter.split_by_rows(csv_file, rows_per_file=50)
        
        # Should create 3 files (150 rows / 50 rows per file)
        self.assertEqual(len(split_files), 3)
        
        # Check if all files exist
        for split_file in split_files:
            self.assertTrue(split_file.exists())
        
        # Check row counts
        total_rows = 0
        for split_file in split_files:
            df = pd.read_csv(split_file)
            total_rows += len(df)
            self.assertLessEqual(len(df), 50)  # Should not exceed rows_per_file
        
        self.assertEqual(total_rows, 150)  # Total rows should match original
    
    def test_split_by_column_values(self):
        """Test splitting CSV by column values."""
        csv_file = self.create_test_csv("test_split_column.csv", 100)
        
        split_files = self.splitter.split_by_column_values(csv_file, 'Department')
        
        # Should create 5 files (one for each department)
        self.assertEqual(len(split_files), 5)
        
        # Check if all files exist
        for split_file in split_files:
            self.assertTrue(split_file.exists())
        
        # Check that each file contains only one department
        departments = set()
        total_rows = 0
        
        for split_file in split_files:
            df = pd.read_csv(split_file)
            unique_departments = df['Department'].unique()
            self.assertEqual(len(unique_departments), 1)  # Only one department per file
            departments.add(unique_departments[0])
            total_rows += len(df)
        
        self.assertEqual(len(departments), 5)  # All departments should be present
        self.assertEqual(total_rows, 100)  # Total rows should match original
    
    def test_split_by_size(self):
        """Test splitting CSV by file size."""
        # Create a larger CSV for size-based splitting
        csv_file = self.create_test_csv("test_split_size.csv", 500)
        
        split_files = self.splitter.split_by_size(csv_file, max_size_mb=0.1)  # Very small size
        
        # Should create multiple files
        self.assertGreater(len(split_files), 1)
        
        # Check if all files exist
        for split_file in split_files:
            self.assertTrue(split_file.exists())
    
    def test_create_split_manifest(self):
        """Test manifest creation."""
        csv_file = self.create_test_csv("test_manifest.csv", 100)
        split_files = self.splitter.split_by_rows(csv_file, rows_per_file=25)
        
        manifest_path = self.splitter.create_split_manifest(split_files, csv_file)
        
        # Check if manifest exists
        self.assertTrue(manifest_path.exists())
        
        # Load and verify manifest content
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        self.assertEqual(manifest['total_split_files'], 4)  # 100 rows / 25 = 4 files
        self.assertEqual(len(manifest['split_files']), 4)
        self.assertIn('original_file', manifest)
        self.assertIn('split_timestamp', manifest)
        
        # Check individual file information
        for file_info in manifest['split_files']:
            self.assertIn('filename', file_info)
            self.assertIn('file_size_bytes', file_info)
            self.assertIn('row_count', file_info)
    
    def test_invalid_csv_file(self):
        """Test handling of invalid CSV file."""
        with self.assertRaises(CSVSplitterError):
            self.splitter.analyze_csv_structure("nonexistent.csv")
    
    def test_invalid_column_name(self):
        """Test splitting by non-existent column."""
        csv_file = self.create_test_csv("test_invalid_column.csv", 50)
        
        with self.assertRaises(CSVSplitterError):
            self.splitter.split_by_column_values(csv_file, 'NonExistentColumn')
    
    def test_empty_csv_handling(self):
        """Test handling of empty CSV file."""
        # Create empty CSV with just headers
        empty_csv = self.test_dir / "empty.csv"
        pd.DataFrame(columns=['A', 'B', 'C']).to_csv(empty_csv, index=False)
        
        analysis = self.splitter.analyze_csv_structure(empty_csv)
        self.assertEqual(analysis['total_rows'], 0)
        self.assertEqual(analysis['total_columns'], 3)


if __name__ == '__main__':
    unittest.main()
