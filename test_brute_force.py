#!/usr/bin/env python3
"""
Test script for the new brute force CSV splitting method.
"""

from src.file_converter import FileConverter
import os

def test_brute_force_splitting():
    """Test the new brute force method."""
    print("Testing brute force CSV splitting...")
    
    try:
        # Initialize converter
        converter = FileConverter('output_test')
        
        # Test with the sample NPS file
        results = converter.split_csv_file(
            'sample_nps.csv', 
            split_method='brute_force',
            prefix='nps_brute_force'
        )
        
        print(f"✅ Success! Created {results['total_split_files']} files")
        print(f"📁 Output directory: {results['output_directory']}")
        print(f"📋 Manifest: {results['manifest_file']}")
        print()
        print("First few split files:")
        for i, file_path in enumerate(results['split_files'][:5]):
            file_name = os.path.basename(file_path)
            print(f"  {i+1}. {file_name}")
        
        if len(results['split_files']) > 5:
            print(f"  ... and {len(results['split_files']) - 5} more files")
            
        return results
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_brute_force_splitting()
