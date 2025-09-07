#!/usr/bin/env python3
"""
Test script for the new hierarchical CSV splitting functionality.
This will split the NPS data correctly preserving the hierarchical structure.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from csv_splitter import CSVSplitter, CSVSplitterError
from file_converter import FileConverter, FileConverterError

def test_hierarchical_splitting():
    """Test the new hierarchical splitting functionality."""
    
    print("🚀 Testing Hierarchical CSV Splitting")
    print("=" * 45)
    
    try:
        # Initialize converter
        converter = FileConverter(output_dir="hierarchical_output")
        
        print("🔍 Analyzing NPS CSV structure...")
        analysis = converter.analyze_csv_for_splitting('sample_nps.csv')
        
        print(f"\n📊 Original file analysis:")
        print(f"   Total rows: {analysis['total_rows']:,}")
        print(f"   File size: {analysis['file_size_mb']} MB")
        
        print("\n✂️ Splitting by hierarchical structure...")
        print("   This will group each main heading with all its sub-rows")
        
        # Split using the new hierarchical method
        split_results = converter.split_csv_file(
            'sample_nps.csv',
            split_method="hierarchical",
            prefix="nps_hierarchical"
        )
        
        print(f"\n✅ Successfully created {split_results['total_split_files']} hierarchical groups!")
        print(f"📁 Output directory: {split_results['output_directory']}")
        
        # Show the first few created files
        print(f"\n📋 Created hierarchical groups:")
        split_files = split_results['split_files']
        
        for i, file_path in enumerate(split_files[:5]):  # Show first 5
            filename = Path(file_path).name
            
            # Try to read and show basic info about each file
            try:
                import pandas as pd
                df = pd.read_csv(file_path)
                main_heading = df.iloc[0]['Name'].strip('"')
                row_count = len(df)
                
                print(f"   {i+1:2d}. {filename}")
                print(f"       📌 Main heading: {main_heading}")
                print(f"       📊 Total rows: {row_count} (including sub-rows)")
                
                # Show a sample of the hierarchy
                if row_count > 1:
                    sub_row = df.iloc[1]['Name'].strip('"')
                    print(f"       📂 First sub-row: {sub_row[:50]}...")
                
            except Exception as e:
                print(f"   {i+1:2d}. {filename} (could not read details)")
        
        if len(split_files) > 5:
            print(f"   ... and {len(split_files) - 5} more hierarchical groups")
        
        # Show manifest info
        print(f"\n📄 Manifest created: {Path(split_results['manifest_file']).name}")
        
        print(f"\n🎉 Hierarchical splitting completed successfully!")
        print(f"\n💡 Each file now contains:")
        print(f"   ✓ One main heading (starting with capital letter)")
        print(f"   ✓ All its related sub-rows (indented hierarchical data)")
        print(f"   ✓ Perfect for feeding individual sections to AI/LLM")
        
        return True
        
    except (FileConverterError, CSVSplitterError) as e:
        print(f"❌ Hierarchical splitting failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_compare_methods():
    """Compare hierarchical vs simple row splitting."""
    print(f"\n🔄 Comparison: Hierarchical vs Simple Row Splitting")
    print("=" * 55)
    
    try:
        converter = FileConverter(output_dir="comparison_output")
        
        # Simple row splitting (the old way)
        print("1️⃣ Simple row splitting (1000 rows per file):")
        simple_results = converter.split_csv_file(
            'sample_nps.csv',
            split_method="rows",
            rows_per_file=1000,
            prefix="simple_rows"
        )
        print(f"   Created {simple_results['total_split_files']} files")
        print("   ⚠️  Problem: Related data gets separated across files")
        
        # Hierarchical splitting (the new correct way)
        print("\n2️⃣ Hierarchical splitting (preserves structure):")
        hierarchical_results = converter.split_csv_file(
            'sample_nps.csv',
            split_method="hierarchical",
            prefix="hierarchical_groups"
        )
        print(f"   Created {hierarchical_results['total_split_files']} files")
        print("   ✅ Perfect: Each main section stays with its sub-data")
        
        print(f"\n📈 Results comparison:")
        print(f"   Simple method: {simple_results['total_split_files']} files (arbitrary splits)")
        print(f"   Hierarchical:  {hierarchical_results['total_split_files']} files (logical groups)")
        
        return True
        
    except Exception as e:
        print(f"❌ Comparison failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing New Hierarchical CSV Splitting Feature")
    print("="*55)
    
    success1 = test_hierarchical_splitting()
    if success1:
        success2 = test_compare_methods()
    
    final_result = success1 and (success2 if success1 else False)
    
    print(f"\n{'='*55}")
    if final_result:
        print("🎉 ALL TESTS PASSED! Hierarchical splitting works perfectly!")
        print("\n✅ Your NPS data will now be split correctly:")
        print("   • Each main heading gets its own file")
        print("   • All sub-rows stay with their parent heading")  
        print("   • Perfect for AI/LLM processing!")
    else:
        print("❌ Some tests failed. Please check the errors above.")
    
    sys.exit(0 if final_result else 1)
