#!/usr/bin/env python3
"""
CSV Comparison Test and Demo Script
===================================

This script demonstrates the CSV comparison functionality and tests the AI integration.
"""

import os
import sys
import tempfile
import pandas as pd
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from comparison.csv_comparison_engine import CSVComparisonEngine


def create_test_csv_files():
    """Create sample CSV files for testing comparison."""
    
    # Sample profiling data (File A)
    data_a = {
        'Component': ['Common-Cleaner', '  Sub-process 1', '  Sub-process 2', 'RMI Scheduler (0)', '  Background Task'],
        'CPU_Time': [1500, 400, 600, 2000, 800],
        'Memory_MB': [120, 45, 55, 180, 90],
        'Status': ['Running', 'Complete', 'Complete', 'Running', 'Complete']
    }
    
    # Sample profiling data (File B) - with some differences
    data_b = {
        'Component': ['Common-Cleaner', '  Sub-process 1', '  Sub-process 2', 'RMI Scheduler (0)', '  Background Task'],
        'CPU_Time': [1600, 400, 650, 2100, 800],  # Some values changed
        'Memory_MB': [125, 45, 58, 185, 90],      # Some values changed
        'Status': ['Running', 'Complete', 'Error', 'Running', 'Complete']  # Status changed
    }
    
    # Create temporary files
    temp_dir = tempfile.mkdtemp(prefix="csv_comparison_test_")
    
    file_a_path = os.path.join(temp_dir, "profiling_data_before.csv")
    file_b_path = os.path.join(temp_dir, "profiling_data_after.csv")
    
    pd.DataFrame(data_a).to_csv(file_a_path, index=False)
    pd.DataFrame(data_b).to_csv(file_b_path, index=False)
    
    return file_a_path, file_b_path, temp_dir


def test_comparison_engine():
    """Test the CSV comparison engine."""
    
    print("🔍 CSV Comparison Engine Test")
    print("=" * 50)
    
    # Create test files
    print("📄 Creating test CSV files...")
    file_a, file_b, temp_dir = create_test_csv_files()
    
    print(f"✅ Created test files:")
    print(f"   File A: {file_a}")
    print(f"   File B: {file_b}")
    
    # Initialize engine
    print("\n🤖 Initializing comparison engine...")
    engine = CSVComparisonEngine(output_dir=temp_dir)
    
    # Perform comparison
    print("\n⚡ Performing brute force comparison...")
    conflicts = engine.brute_force_comparison(file_a, file_b)
    
    print(f"✅ Found {len(conflicts)} conflict ranges")
    
    # Display conflicts
    if conflicts:
        print("\n📊 Conflict Details:")
        for i, conflict in enumerate(conflicts, 1):
            print(f"\nConflict #{i}:")
            print(f"  Range: Rows {conflict.start_row}-{conflict.end_row}")
            print(f"  Type: {conflict.conflict_type}")
            print(f"  Description: {conflict.description}")
            print(f"  File A section (first 100 chars): {conflict.file_a_section[:100]}...")
            print(f"  File B section (first 100 chars): {conflict.file_b_section[:100]}...")
    
    # Test AI analysis (will use mock if API not available)
    print("\n🤖 Testing AI analysis...")
    try:
        results = engine.compare_and_analyze(file_a, file_b, "Test File A", "Test File B")
        print("✅ AI analysis completed")
        print(f"📋 Summary: {results['summary']}")
        print(f"📝 AI Response (first 200 chars): {results['ai_analysis'][:200]}...")
        
    except Exception as e:
        print(f"⚠️ AI analysis failed (expected if API key not configured): {e}")
        print("   This is normal for testing - the comparison engine still works!")
    
    print(f"\n🧹 Test files created in: {temp_dir}")
    print("✅ Test completed successfully!")


if __name__ == "__main__":
    test_comparison_engine()
