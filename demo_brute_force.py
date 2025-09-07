#!/usr/bin/env python3
"""
Demo script showing the brute force CSV splitting with JSON conversion.
"""

from src.file_converter import FileConverter
import os
import json
from pathlib import Path

def demo_brute_force_split_and_convert():
    """Demonstrate the brute force method with JSON conversion."""
    print("🚀 Brute Force CSV Splitting & JSON Conversion Demo")
    print("=" * 60)
    
    try:
        # Initialize converter with output directory
        converter = FileConverter('demo_output')
        
        print("📁 Testing brute force split with JSON conversion...")
        
        # Split and convert to JSON
        results = converter.split_and_convert_csv(
            'sample_nps.csv',
            split_method='brute_force',
            convert_splits=True,
            prefix='nps_demo'
        )
        
        print(f"✅ Success!")
        print(f"📊 Original file: {results['original_file']}")
        print(f"🔧 Split method: {results['split_method']}")
        print(f"📈 Total split files: {results['total_split_files']}")
        print(f"📄 JSON files created: {results['total_json_files']}")
        print()
        
        # Show first few files
        print("📂 First 5 split files:")
        for i, file_path in enumerate(results['split_files'][:5]):
            file_name = os.path.basename(file_path)
            print(f"  {i+1}. {file_name}")
            
        print()
        print("📂 First 5 JSON files:")
        for i, file_path in enumerate(results['json_files'][:5]):
            file_name = os.path.basename(file_path)
            print(f"  {i+1}. {file_name}")
        
        print()
        
        # Show sample JSON content
        if results['json_files']:
            sample_json_file = results['json_files'][0]
            print(f"📋 Sample JSON content from {os.path.basename(sample_json_file)}:")
            print("-" * 40)
            
            with open(sample_json_file, 'r', encoding='utf-8') as f:
                sample_data = json.load(f)
                # Show first 3 records
                for i, record in enumerate(sample_data[:3]):
                    print(f"Record {i+1}: {json.dumps(record, indent=2)}")
                    if i < 2:
                        print()
                
                if len(sample_data) > 3:
                    print(f"... and {len(sample_data) - 3} more records")
        
        print()
        print(f"📁 All files saved to: {results['output_directory']}")
        print(f"📋 Manifest file: {results['manifest_file']}")
        
        return results
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    demo_brute_force_split_and_convert()
