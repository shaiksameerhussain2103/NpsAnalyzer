#!/usr/bin/env python3
"""
Test the improved repository file finder with the actual failing case
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from stack_trace_analyzer.repo_file_finder import RepositoryFileFinder
from stack_trace_analyzer.stack_trace_parser import StackTraceParser

def test_pinlist_decoration_style():
    """Test finding PinListDecorationStyle.java file"""
    
    print("🔍 Testing Improved Repository File Finder")
    print("=" * 60)
    
    # Set up the repository path and class we're looking for
    repo_path = r"C:\Users\Z0055DXU\mgnoscan\repo\iesd-25\datamodel_src"
    class_input = "chs.common.styles.PinListDecorationStyle.refreshDecorations()"
    
    print(f"Repository: {repo_path}")
    print(f"Input: {class_input}")
    print()
    
    try:
        # Parse the input
        print("1️⃣ Parsing input...")
        parser = StackTraceParser()
        stack_info = parser.parse_single_line(class_input)
        
        print(f"  Class: {stack_info.class_name}")
        print(f"  Package: {stack_info.package_path}")
        print(f"  File: {stack_info.file_name}")
        print(f"  Method: {stack_info.method_name}")
        print()
        
        # Initialize file finder with improved logic
        print("2️⃣ Initializing enhanced file finder...")
        finder = RepositoryFileFinder(repo_path)
        
        # Show discovered source directories
        cache_stats = finder.get_cache_stats()
        print(f"  Discovered {cache_stats['source_directories']} source directories:")
        for src_dir in cache_stats['source_directory_paths']:
            print(f"    📁 {src_dir}")
        print()
        
        # Search for the file
        print("3️⃣ Searching for file...")
        results = finder.find_file(stack_info)
        
        print(f"Found {len(results)} result(s):")
        for i, result in enumerate(results, 1):
            print(f"  {i}. {result.relative_path}")
            print(f"     Strategy: {result.search_strategy}")
            print(f"     Package: {result.package_path}")
            print(f"     Size: {result.file_size} bytes")
            print()
        
        if results:
            print("✅ SUCCESS: File found!")
            print(f"🎯 Actual location: {results[0].absolute_path}")
        else:
            print("❌ FAILED: File not found")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

def test_directory_discovery():
    """Test what directories are discovered in the repository"""
    
    print("\n🔧 Testing Directory Discovery")
    print("=" * 60)
    
    repo_path = r"C:\Users\Z0055DXU\mgnoscan\repo\iesd-25\datamodel_src"
    
    try:
        finder = RepositoryFileFinder(repo_path)
        cache_stats = finder.get_cache_stats()
        
        print(f"Repository: {repo_path}")
        print(f"Discovered {cache_stats['source_directories']} source directories:")
        print()
        
        for i, src_dir in enumerate(cache_stats['source_directory_paths'], 1):
            print(f"{i:2}. {src_dir}")
        
        print()
        print("🎯 Expected directory should be: src/impl/cofImpl/src")
        
        expected_found = any("src/impl/cofImpl/src" in path for path in cache_stats['source_directory_paths'])
        if expected_found:
            print("✅ SUCCESS: Expected directory structure found!")
        else:
            print("❌ ISSUE: Expected directory structure not found")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    test_directory_discovery()
    test_pinlist_decoration_style()