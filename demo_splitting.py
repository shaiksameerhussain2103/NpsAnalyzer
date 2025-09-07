#!/usr/bin/env python3
"""
Example usage of the enhanced File Converter with CSV splitting functionality.
This demonstrates the new features added for AI/LLM data preparation.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from file_converter import FileConverter, FileConverterError

def main():
    """Demonstrate the new CSV splitting features."""
    
    print("🚀 Enhanced File Converter - CSV Splitting Demo")
    print("=" * 55)
    
    # Initialize converter
    converter = FileConverter(output_dir="demo_output")
    
    # Example 1: Analyze CSV structure
    print("\n📊 1. Analyzing CSV Structure")
    print("-" * 30)
    
    try:
        analysis = converter.analyze_csv_for_splitting('sample_nps.csv')
        
        print(f"📁 File: {analysis['file_path']}")
        print(f"📊 Total rows: {analysis['total_rows']:,}")
        print(f"📈 Total columns: {analysis['total_columns']}")
        print(f"💾 File size: {analysis['file_size_mb']} MB")
        print(f"💡 Recommended rows per file: {analysis['recommended_rows_per_file']:,}")
        print(f"📦 Estimated output files: {analysis['estimated_output_files']}")
        
    except FileConverterError as e:
        print(f"❌ Analysis failed: {e}")
        return
    
    # Example 2: Split by rows (perfect for AI/LLM processing)
    print("\n✂️ 2. Splitting CSV by Rows (AI/LLM Ready)")
    print("-" * 45)
    
    try:
        split_results = converter.split_csv_file(
            'sample_nps.csv',
            split_method="rows",
            rows_per_file=500,  # 500 rows per file for AI processing
            prefix="ai_ready"
        )
        
        print(f"✅ Created {split_results['total_split_files']} split files")
        print(f"📁 Output directory: {split_results['output_directory']}")
        print(f"📄 Manifest file: {split_results['manifest_file']}")
        
        # Show first few files
        print("\n📋 Created files:")
        for i, file_path in enumerate(split_results['split_files'][:3]):
            filename = Path(file_path).name
            print(f"   {i+1}. {filename}")
        
        if len(split_results['split_files']) > 3:
            remaining = len(split_results['split_files']) - 3
            print(f"   ... and {remaining} more files")
            
    except FileConverterError as e:
        print(f"❌ Splitting failed: {e}")
        return
    
    # Example 3: Split and convert to JSON in one operation
    print("\n🔄 3. Split and Convert to JSON (Complete Workflow)")
    print("-" * 52)
    
    try:
        json_results = converter.split_and_convert_csv(
            'sample_nps.csv',
            split_method="rows",
            rows_per_file=1000,
            convert_splits=True,
            prefix="json_ready"
        )
        
        print(f"✅ Created {json_results['total_split_files']} CSV files")
        print(f"✅ Created {json_results['total_json_files']} JSON files")
        print(f"📁 All files saved to: {json_results['output_directory']}")
        
    except FileConverterError as e:
        print(f"❌ Split and convert failed: {e}")
        return
    
    # Example 4: Split by column values (if applicable)
    print("\n🗂️ 4. Alternative: Split by Column Values")
    print("-" * 40)
    
    try:
        # For the NPS data, we could split by the first level of the hierarchical data
        # This is just an example - the NPS data might not have clear categories to split by
        print("💡 For categorical data, you can split by column values:")
        print("   converter.split_csv_file('data.csv', split_method='column', column_name='Category')")
        print("   This creates separate files for each unique value in the specified column.")
        
    except Exception as e:
        print(f"ℹ️ Column-based splitting example (not applicable to current data)")
    
    print("\n🎉 Demo completed successfully!")
    print("\nKey Benefits for AI/LLM Processing:")
    print("✓ Manageable file sizes for upload limits")
    print("✓ Structured data with metadata")
    print("✓ Batch processing capabilities")
    print("✓ Automatic JSON conversion")
    print("✓ Comprehensive error handling")
    print("✓ Detailed operation tracking with manifests")


if __name__ == "__main__":
    main()
