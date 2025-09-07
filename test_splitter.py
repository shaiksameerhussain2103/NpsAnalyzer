#!/usr/bin/env python3
"""Test script for the CSV splitter functionality."""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from csv_splitter import CSVSplitter, CSVSplitterError

def test_splitter():
    """Test the CSV splitter with the NPS file."""
    try:
        splitter = CSVSplitter(output_dir="split_test_output")
        
        print("🔍 Analyzing NPS CSV file...")
        analysis = splitter.analyze_csv_structure('sample_nps.csv')
        
        print("\n📊 CSV Analysis Results:")
        print(f"   Total rows: {analysis['total_rows']:,}")
        print(f"   Total columns: {analysis['total_columns']}")
        print(f"   File size: {analysis['file_size_mb']} MB")
        print(f"   Memory usage: {analysis['memory_usage_mb']} MB")
        print(f"   Recommended rows per file: {analysis['recommended_rows_per_file']:,}")
        print(f"   Estimated output files: {analysis['estimated_output_files']}")
        
        print(f"\n📋 Column names: {', '.join(analysis['column_names'])}")
        
        print("\n✂️ Splitting CSV file by rows (1000 rows per file)...")
        split_results = splitter.split_by_rows(
            'sample_nps.csv', 
            rows_per_file=1000, 
            prefix="nps_split"
        )
        
        print(f"✅ Successfully created {len(split_results)} split files:")
        for i, split_file in enumerate(split_results[:3]):  # Show first 3 files
            print(f"   {i+1}. {split_file.name}")
        
        if len(split_results) > 3:
            print(f"   ... and {len(split_results) - 3} more files")
        
        # Create manifest
        print("\n📄 Creating manifest...")
        manifest_path = splitter.create_split_manifest(split_results, 'sample_nps.csv')
        print(f"✅ Manifest created: {manifest_path}")
        
        print(f"\n🎉 Split operation completed successfully!")
        print(f"📁 Output directory: {splitter.output_dir}")
        
        return True
        
    except CSVSplitterError as e:
        print(f"❌ CSV splitter error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_splitter()
    sys.exit(0 if success else 1)
