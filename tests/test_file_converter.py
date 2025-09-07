"""
Unit tests for the file converter module.
"""

import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd
import pytest

from src.file_converter import FileConverter, FileConverterError


class TestFileConverter(unittest.TestCase):
    """Test cases for FileConverter class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.converter = FileConverter(output_dir="test_output")
        self.test_dir = Path("test_output")
        self.test_dir.mkdir(exist_ok=True)
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up test files
        if self.test_dir.exists():
            for item in self.test_dir.rglob("*"):
                if item.is_file():
                    try:
                        item.unlink()
                    except PermissionError:
                        pass  # Skip files that can't be deleted
            # Clean up directories
            for item in self.test_dir.rglob("*"):
                if item.is_dir():
                    try:
                        item.rmdir()
                    except (OSError, PermissionError):
                        pass  # Skip directories that can't be removed
            try:
                self.test_dir.rmdir()
            except (OSError, PermissionError):
                pass
    
    def create_test_csv(self, filename: str = "test.csv") -> Path:
        """Create a test CSV file."""
        test_data = {
            'Name': ['John', 'Jane', 'Bob'],
            'Age': [25, 30, 35],
            'City': ['New York', 'Los Angeles', 'Chicago']
        }
        df = pd.DataFrame(test_data)
        
        csv_path = self.test_dir / filename
        df.to_csv(csv_path, index=False)
        return csv_path
    
    def create_test_xml(self, filename: str = "test.xml") -> Path:
        """Create a test XML file."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <employees>
            <employee>
                <name>John Doe</name>
                <age>25</age>
                <department>Engineering</department>
            </employee>
            <employee>
                <name>Jane Smith</name>
                <age>30</age>
                <department>Marketing</department>
            </employee>
        </employees>"""
        
        xml_path = self.test_dir / filename
        with open(xml_path, 'w', encoding='utf-8') as f:
            f.write(xml_content)
        return xml_path
    
    def test_validate_file_exists(self):
        """Test file validation for existing files."""
        csv_file = self.create_test_csv()
        # Should not raise an exception
        self.converter.validate_file(csv_file)
    
    def test_validate_file_not_exists(self):
        """Test file validation for non-existing files."""
        with self.assertRaises(FileConverterError):
            self.converter.validate_file("nonexistent.csv")
    
    def test_validate_file_unsupported_extension(self):
        """Test file validation for unsupported extensions."""
        # Create a file with unsupported extension
        test_file = self.test_dir / "test.txt"
        test_file.write_text("test content")
        
        with self.assertRaises(FileConverterError):
            self.converter.validate_file(test_file)
    
    def test_csv_to_json_conversion(self):
        """Test CSV to JSON conversion."""
        csv_file = self.create_test_csv()
        result = self.converter.csv_to_json(csv_file)
        
        # Check result structure
        self.assertIn('metadata', result)
        self.assertIn('data', result)
        
        # Check metadata
        metadata = result['metadata']
        self.assertEqual(metadata['file_type'], 'csv')
        self.assertEqual(metadata['total_records'], 3)
        self.assertEqual(len(metadata['columns']), 3)
        
        # Check data
        data = result['data']
        self.assertEqual(len(data), 3)
        self.assertEqual(data[0]['Name'], 'John')
        self.assertEqual(data[0]['Age'], 25)
    
    def test_xml_to_json_conversion(self):
        """Test XML to JSON conversion."""
        xml_file = self.create_test_xml()
        result = self.converter.xml_to_json(xml_file)
        
        # Check result structure
        self.assertIn('metadata', result)
        self.assertIn('data', result)
        
        # Check metadata
        metadata = result['metadata']
        self.assertEqual(metadata['file_type'], 'xml')
        self.assertEqual(metadata['root_element'], 'employees')
        
        # Check data structure
        data = result['data']
        self.assertIn('employees', data)
    
    def test_convert_file_csv(self):
        """Test complete file conversion for CSV."""
        csv_file = self.create_test_csv()
        output_file = self.converter.convert_file(csv_file)
        
        # Check if output file exists
        self.assertTrue(output_file.exists())
        
        # Verify JSON content
        with open(output_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        self.assertIn('metadata', json_data)
        self.assertIn('data', json_data)
        self.assertEqual(len(json_data['data']), 3)
    
    def test_convert_file_xml(self):
        """Test complete file conversion for XML."""
        xml_file = self.create_test_xml()
        output_file = self.converter.convert_file(xml_file)
        
        # Check if output file exists
        self.assertTrue(output_file.exists())
        
        # Verify JSON content
        with open(output_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        self.assertIn('metadata', json_data)
        self.assertIn('data', json_data)
    
    def test_batch_convert(self):
        """Test batch conversion functionality."""
        # Create multiple test files
        csv_file1 = self.create_test_csv("test1.csv")
        csv_file2 = self.create_test_csv("test2.csv")
        xml_file1 = self.create_test_xml("test1.xml")
        
        # Run batch conversion
        results = self.converter.batch_convert(self.test_dir)
        
        # Should have 3 converted files
        self.assertEqual(len(results), 3)
        
        # Check if all output files exist
        for result_file in results:
            self.assertTrue(result_file.exists())
    
    def test_csv_encoding_handling(self):
        """Test CSV encoding detection and handling."""
        # Create CSV with different encoding
        test_data = {'Name': ['José', 'François'], 'City': ['São Paulo', 'Montréal']}
        df = pd.DataFrame(test_data)
        
        csv_path = self.test_dir / "test_encoding.csv"
        df.to_csv(csv_path, index=False, encoding='latin-1')
        
        # Should handle encoding automatically
        result = self.converter.csv_to_json(csv_path)
        self.assertEqual(len(result['data']), 2)


if __name__ == '__main__':
    unittest.main()
