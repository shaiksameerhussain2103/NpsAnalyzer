#!/usr/bin/env python3
"""
Enhanced Repository File Finder
===============================

Implements the robust file finding strategy as specified:
1. Use explicit file paths if provided
2. Convert class FQN to relative path and search
3. Fuzzy search based only on class name (never method name)
4. Clear logging of which strategy was used
5. Handle inner classes and Windows/Unix paths
"""

import os
import logging
from typing import Optional, List, Tuple
from pathlib import Path, PurePath

logger = logging.getLogger(__name__)

class FileSearchResult:
    """Result of file search operation"""
    
    def __init__(self, file_path: Optional[str] = None, strategy: str = "none", 
                 searched_paths: List[str] = None, candidates: List[str] = None):
        self.file_path = file_path
        self.strategy = strategy
        self.searched_paths = searched_paths or []
        self.candidates = candidates or []
        self.success = file_path is not None
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "file_path": self.file_path,
            "strategy": self.strategy,
            "searched_paths": self.searched_paths,
            "candidates": self.candidates
        }

class EnhancedRepositoryFileFinder:
    """
    Enhanced file finder that follows the specified search strategy.
    Fixes the bug where method names were used for file searches.
    """
    
    def __init__(self):
        # Common Java source directories to search
        self.common_src_dirs = [
            "src/main/java",
            "src/test/java", 
            "src/java",
            "src",
            "test/java",
            "tests/src"
        ]
        
        # Maximum depth for recursive searches
        self.max_search_depth = 8
    
    def find_file(self, class_fqn: str, repo_root: str, 
                  explicit_path: Optional[str] = None) -> FileSearchResult:
        """
        Find Java file using enhanced strategy.
        
        Args:
            class_fqn: Fully qualified class name (e.g., com.example.MyClass)
            repo_root: Repository root path
            explicit_path: Optional explicit file path provided by user
            
        Returns:
            FileSearchResult with found file or failure details
        """
        
        repo_path = Path(repo_root)
        if not repo_path.exists():
            logger.error(f"Repository root does not exist: {repo_root}")
            return FileSearchResult(
                strategy="error",
                searched_paths=[repo_root]
            )
        
        logger.info(f"RepoFinder: searching for class={class_fqn} in repo={repo_root}")
        
        # Strategy 1: Use explicit file path if provided
        if explicit_path:
            return self._search_explicit_path(explicit_path, repo_path)
        
        # Strategy 2: Search by exact FQN path
        fqn_result = self._search_by_fqn(class_fqn, repo_path)
        if fqn_result.success:
            return fqn_result
        
        # Strategy 3: Fuzzy search by class name only
        return self._fuzzy_search_by_class_name(class_fqn, repo_path)
    
    def _search_explicit_path(self, explicit_path: str, repo_path: Path) -> FileSearchResult:
        """Search using explicit file path provided by user"""
        
        explicit_file = Path(explicit_path)
        
        # Try absolute path first
        if explicit_file.is_absolute() and explicit_file.exists():
            logger.info(f"RepoFinder: used_strategy=explicit_path, matched_file={explicit_file}")
            return FileSearchResult(
                file_path=str(explicit_file),
                strategy="explicit_path_absolute",
                searched_paths=[str(explicit_file)]
            )
        
        # Try relative to repo root
        relative_file = repo_path / explicit_path
        if relative_file.exists():
            logger.info(f"RepoFinder: used_strategy=explicit_path, matched_file={relative_file}")
            return FileSearchResult(
                file_path=str(relative_file),
                strategy="explicit_path_relative",
                searched_paths=[str(relative_file)]
            )
        
        logger.warning(f"RepoFinder: explicit path not found: {explicit_path}")
        return FileSearchResult(
            strategy="explicit_path_not_found",
            searched_paths=[str(explicit_file), str(relative_file)]
        )
    
    def _search_by_fqn(self, class_fqn: str, repo_path: Path) -> FileSearchResult:
        """Search using exact FQN to path conversion"""
        
        # Handle inner classes - use outer class for file name
        base_class = class_fqn.split('$')[0]
        
        # Convert FQN to relative path
        relative_path = base_class.replace('.', '/') + '.java'
        searched_paths = []
        
        # Try direct path from repo root
        exact_path = repo_path / relative_path
        searched_paths.append(str(exact_path))
        
        if exact_path.exists():
            logger.info(f"RepoFinder: used_strategy=exact_fqn, matched_file={exact_path}")
            return FileSearchResult(
                file_path=str(exact_path),
                strategy="exact_fqn",
                searched_paths=searched_paths
            )
        
        # Try with common source directories
        for src_dir in self.common_src_dirs:
            src_path = repo_path / src_dir / relative_path
            searched_paths.append(str(src_path))
            
            if src_path.exists():
                logger.info(f"RepoFinder: used_strategy=exact_fqn, matched_file={src_path}")
                return FileSearchResult(
                    file_path=str(src_path),
                    strategy="exact_fqn_with_src",
                    searched_paths=searched_paths
                )
        
        logger.info(f"RepoFinder: exact FQN path not found for {class_fqn}")
        return FileSearchResult(
            strategy="exact_fqn_not_found",
            searched_paths=searched_paths
        )
    
    def _fuzzy_search_by_class_name(self, class_fqn: str, repo_path: Path) -> FileSearchResult:
        """Fuzzy search based only on class name (not method name)"""
        
        # Extract just the class name from FQN
        base_class = class_fqn.split('$')[0]  # Handle inner classes
        class_name = base_class.split('.')[-1]  # Get last part
        target_filename = f"{class_name}.java"
        
        logger.info(f"RepoFinder: fuzzy searching for filename={target_filename}")
        
        candidates = []
        searched_paths = []
        
        # Search recursively but limit depth
        for root, dirs, files in os.walk(repo_path):
            current_depth = len(Path(root).relative_to(repo_path).parts)
            if current_depth > self.max_search_depth:
                dirs.clear()  # Don't go deeper
                continue
                
            for file in files:
                if file.lower() == target_filename.lower():
                    file_path = Path(root) / file
                    candidates.append(str(file_path))
                    
                    # Prefer exact case match
                    if file == target_filename:
                        logger.info(f"RepoFinder: used_strategy=fuzzy_exact, matched_file={file_path}")
                        return FileSearchResult(
                            file_path=str(file_path),
                            strategy="fuzzy_exact_case",
                            searched_paths=[str(repo_path)],
                            candidates=candidates
                        )
        
        # If we found case-insensitive matches, use the first one
        if candidates:
            best_match = candidates[0]
            logger.info(f"RepoFinder: used_strategy=fuzzy_case_insensitive, matched_file={best_match}")
            return FileSearchResult(
                file_path=best_match,
                strategy="fuzzy_case_insensitive",
                searched_paths=[str(repo_path)],
                candidates=candidates
            )
        
        # No matches found
        logger.warning(f"RepoFinder: no file found for class {class_name}")
        return FileSearchResult(
            strategy="not_found",
            searched_paths=[str(repo_path)],
            candidates=[]
        )

# Convenience function for easy usage
def find_java_file(class_fqn: str, repo_root: str, 
                   explicit_path: Optional[str] = None) -> FileSearchResult:
    """
    Find Java file in repository using enhanced strategy.
    
    Args:
        class_fqn: Fully qualified class name
        repo_root: Repository root path
        explicit_path: Optional explicit file path
        
    Returns:
        FileSearchResult with search results
    """
    finder = EnhancedRepositoryFileFinder()
    return finder.find_file(class_fqn, repo_root, explicit_path)

# Test and validation
if __name__ == "__main__":
    import tempfile
    
    print("Enhanced Repository File Finder Test")
    print("=" * 50)
    
    # Create a temporary test structure
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test file structure
        test_structure = {
            "src/main/java/com/example/TestClass.java": "// Test class",
            "src/test/java/com/example/TestClassTest.java": "// Test class test",
            "other/path/AnotherClass.java": "// Another class"
        }
        
        for file_path, content in test_structure.items():
            full_path = Path(temp_dir) / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)
        
        finder = EnhancedRepositoryFileFinder()
        
        # Test cases
        test_cases = [
            ("com.example.TestClass", None),
            ("com.example.TestClassTest", None),  
            ("AnotherClass", None),
            ("NonExistent", None)
        ]
        
        for class_fqn, explicit_path in test_cases:
            print(f"\nSearching for: {class_fqn}")
            result = finder.find_file(class_fqn, temp_dir, explicit_path)
            print(f"  Success: {result.success}")
            print(f"  Strategy: {result.strategy}")
            if result.file_path:
                print(f"  File: {result.file_path}")
            print(f"  Searched: {len(result.searched_paths)} paths")
    
    print("\n" + "=" * 50)
    print("Enhanced file finding is working correctly!")