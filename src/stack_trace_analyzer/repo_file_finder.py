"""
Dynamic Repository File Finder

Dynamically searches through repository directories to locate Java files
based on parsed package structure without preprocessing the entire repository.

Features:
- Smart directory traversal based on package path hints
- Multiple search strategies (exact path, fuzzy matching, broad search)
- Caching of discovered file locations
- Support for multiple source directories (src/main/java, src, etc.)
"""

import os
import logging
from typing import List, Optional, Dict, Set
from pathlib import Path
from dataclasses import dataclass
import fnmatch

from .stack_trace_parser import StackTraceInfo

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class FileLocation:
    """Information about a located Java file"""
    absolute_path: str
    relative_path: str
    package_path: str
    class_name: str
    file_size: int
    search_strategy: str  # How this file was found
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "absolute_path": self.absolute_path,
            "relative_path": self.relative_path, 
            "package_path": self.package_path,
            "class_name": self.class_name,
            "file_size": self.file_size,
            "search_strategy": self.search_strategy
        }

class RepositoryFileFinder:
    """Finds Java files in repositories using dynamic search strategies"""
    
    # Common source directory patterns in Java projects
    COMMON_SRC_PATTERNS = [
        "src/main/java",
        "src/java", 
        "src",
        "java",
        "main/java",
        "source/java",
        "sources",
        # Additional enterprise patterns
        "src/impl/*/src",  # Pattern like src/impl/cofImpl/src
        "src/test/java",
        "src/test",
        "test/java",
        "tests/src",
        "src/main/resources",
        "impl/*/src"  # Pattern for impl/cofImpl/src
    ]
    
    def __init__(self, repo_root: str):
        """
        Initialize the repository file finder
        
        Args:
            repo_root: Root directory of the repository to search
        """
        self.repo_root = Path(repo_root).resolve()
        self.file_cache: Dict[str, List[FileLocation]] = {}
        self.src_directories: List[Path] = []
        
        if not self.repo_root.exists():
            raise ValueError(f"Repository root does not exist: {repo_root}")
        
        logger.info(f"Initialized RepositoryFileFinder for: {self.repo_root}")
        self._discover_source_directories()
    
    def _discover_source_directories(self):
        """Discover common source directories in the repository"""
        logger.info("Discovering source directories...")
        
        found_dirs = set()  # Use set to avoid duplicates
        
        # Strategy 1: Look for standard patterns
        for pattern in self.COMMON_SRC_PATTERNS:
            potential_dirs = list(self.repo_root.glob(f"**/{pattern}"))
            
            for src_dir in potential_dirs:
                if src_dir.is_dir() and self._looks_like_java_source_dir(src_dir):
                    found_dirs.add(src_dir)
                    logger.info(f"Found source directory: {src_dir.relative_to(self.repo_root)}")
        
        # Strategy 2: Deep search for directories with Java files (more comprehensive)
        logger.info("Performing deep search for Java source directories...")
        
        # Find all directories containing Java files
        java_dirs = set()
        try:
            for java_file in self.repo_root.glob("**/*.java"):
                java_dirs.add(java_file.parent)
        except OSError as e:
            logger.warning(f"Error during deep search: {e}")
        
        # Add directories that have significant Java content
        for java_dir in java_dirs:
            if self._looks_like_significant_java_source_dir(java_dir):
                found_dirs.add(java_dir)
                logger.info(f"Found Java source directory: {java_dir.relative_to(self.repo_root)}")
        
        self.src_directories = list(found_dirs)
        
        # If no source directories found, use repo root
        if not self.src_directories:
            logger.info("No source directories found, using repo root")
            self.src_directories = [self.repo_root]
        
        logger.info(f"Total source directories found: {len(self.src_directories)}")
    
    def _looks_like_significant_java_source_dir(self, directory: Path) -> bool:
        """Check if a directory looks like a significant Java source directory"""
        try:
            # Count Java files in this directory and immediate subdirectories
            java_files = list(directory.glob("*.java"))  # Direct files
            java_files_recursive = list(directory.glob("**/*.java"))  # All files
            
            # Consider it significant if it has:
            # - At least 2 Java files directly, OR
            # - More than 5 Java files in total, OR
            # - Has typical Java package structure (contains directories with Java files)
            has_direct_java = len(java_files) >= 2
            has_many_java = len(java_files_recursive) > 5
            has_package_structure = any(
                subdir.is_dir() and list(subdir.glob("*.java"))
                for subdir in directory.iterdir()
                if subdir.is_dir()
            )
            
            return has_direct_java or has_many_java or has_package_structure
            
        except OSError:
            return False
    
    def _looks_like_java_source_dir(self, directory: Path) -> bool:
        """Check if a directory looks like a Java source directory (basic check)"""
        # Look for .java files or typical package structure
        try:
            java_files = list(directory.glob("**/*.java"))
            return len(java_files) > 0
        except OSError:
            return False
    
    def find_file(self, stack_trace_info: StackTraceInfo) -> List[FileLocation]:
        """
        Find Java file(s) by following the package path sequentially
        
        Args:
            stack_trace_info: Parsed stack trace information
            
        Returns:
            List of FileLocation objects for matching files
        """
        cache_key = f"{stack_trace_info.package_path}/{stack_trace_info.class_name}"
        
        # Check cache first
        if cache_key in self.file_cache:
            logger.info(f"Found cached result for: {cache_key}")
            return self.file_cache[cache_key]
        
        logger.info(f"Searching for: {stack_trace_info.full_class_path}")
        
        found_files = []
        
        # NEW EFFICIENT APPROACH: Sequential path following
        sequential_matches = self._find_by_sequential_path(stack_trace_info)
        found_files.extend(sequential_matches)
        
        # Fallback: Only if sequential approach fails
        if not found_files:
            logger.info("Sequential search failed, trying exact path search as fallback")
            exact_matches = self._find_by_exact_path(stack_trace_info)
            found_files.extend(exact_matches)
        
        # Cache the results
        self.file_cache[cache_key] = found_files
        
        logger.info(f"Found {len(found_files)} file(s) for {stack_trace_info.class_name}")
        return found_files
    
    def _find_by_sequential_path(self, stack_trace_info: StackTraceInfo) -> List[FileLocation]:
        """
        Find files by following package path sequentially from USER PROVIDED PATH.
        
        Example: User provides: C:/path/to/chs and stack trace is chs.common.attr.AttributeValidatorFactoryDescriptionTest
        - Package parts: [chs, common, attr]  
        - Skip first part (chs) since user path already ends with chs
        - Look for 'common' folder in user path
        - Look for 'attr' folder inside common
        - Look for 'AttributeValidatorFactoryDescriptionTest.java' inside attr
        """
        logger.info(f"Sequential search from user path: {stack_trace_info.package_path}/{stack_trace_info.file_name}")
        
        found_files = []
        package_parts = stack_trace_info.package_path.split('.')
        filename = stack_trace_info.file_name
        
        # Start from USER PROVIDED PATH (repo_root)
        current_path = self.repo_root
        
        # Check if user path already contains first package part
        user_path_name = self.repo_root.name.lower()
        first_package = package_parts[0].lower()
        
        # Skip first package part if user path already ends with it
        if user_path_name == first_package:
            package_parts_to_search = package_parts[1:]  # Skip first part
            logger.info(f"User path ends with '{first_package}', skipping to: {package_parts_to_search}")
        else:
            package_parts_to_search = package_parts
            logger.info(f"Searching for all parts: {package_parts_to_search}")
        
        # Follow remaining package path step by step
        for package_part in package_parts_to_search:
            # Look for the package folder (try exact match first, then lowercase)
            potential_paths = [
                current_path / package_part,           # exact match
                current_path / package_part.lower(),   # lowercase version
            ]
            
            found = False
            for potential_path in potential_paths:
                if potential_path.exists() and potential_path.is_dir():
                    current_path = potential_path
                    logger.info(f"Found folder: {package_part} -> {current_path}")
                    found = True
                    break
            
            if not found:
                logger.info(f"❌ Folder not found: {package_part} in {current_path}")
                return found_files  # Path not found
        
        # All package parts found, now look for the Java file
        java_file_path = current_path / filename
        if java_file_path.exists() and java_file_path.is_file():
            file_location = FileLocation(
                absolute_path=str(java_file_path),
                relative_path=str(java_file_path.relative_to(self.repo_root.parent) if self.repo_root.parent else java_file_path.name),
                package_path=stack_trace_info.package_path,
                class_name=stack_trace_info.class_name,
                file_size=java_file_path.stat().st_size,
                search_strategy="sequential_from_user_path"
            )
            found_files.append(file_location)
            logger.info(f"✅ Found Java file: {java_file_path}")
        else:
            logger.info(f"❌ Java file not found: {java_file_path}")
        
        return found_files
    
    def _find_by_exact_path(self, stack_trace_info: StackTraceInfo) -> List[FileLocation]:
        """Find files using exact package path matching"""
        logger.info(f"Strategy 1: Exact path search for {stack_trace_info.package_path}/{stack_trace_info.file_name}")
        
        found_files = []
        target_path = f"{stack_trace_info.package_path}/{stack_trace_info.file_name}"
        
        for src_dir in self.src_directories:
            potential_file = src_dir / target_path
            
            if potential_file.exists() and potential_file.is_file():
                file_location = FileLocation(
                    absolute_path=str(potential_file),
                    relative_path=str(potential_file.relative_to(self.repo_root)),
                    package_path=stack_trace_info.package_path,
                    class_name=stack_trace_info.class_name,
                    file_size=potential_file.stat().st_size,
                    search_strategy="exact_path"
                )
                found_files.append(file_location)
                logger.info(f"✅ Found exact match: {potential_file.relative_to(self.repo_root)}")
        
        return found_files
    
    def _find_by_fuzzy_path(self, stack_trace_info: StackTraceInfo) -> List[FileLocation]:
        """Find files using fuzzy package path matching"""
        logger.info(f"Strategy 2: Fuzzy path search for {stack_trace_info.class_name}")
        
        found_files = []
        package_parts = stack_trace_info.package_path.split('/')
        
        # Try different combinations of package path parts
        for i in range(len(package_parts)):
            partial_path = '/'.join(package_parts[i:])
            search_pattern = f"**/{partial_path}/{stack_trace_info.file_name}"
            
            for src_dir in self.src_directories:
                matches = list(src_dir.glob(search_pattern))
                
                for match in matches:
                    if match.is_file():
                        # Extract the actual package path from the file location
                        actual_package_path = str(match.parent.relative_to(self._find_java_root(match)))
                        
                        file_location = FileLocation(
                            absolute_path=str(match),
                            relative_path=str(match.relative_to(self.repo_root)),
                            package_path=actual_package_path,
                            class_name=stack_trace_info.class_name,
                            file_size=match.stat().st_size,
                            search_strategy="fuzzy_path"
                        )
                        found_files.append(file_location)
                        logger.info(f"✅ Found fuzzy match: {match.relative_to(self.repo_root)}")
        
        return found_files
    
    def _find_by_class_name(self, stack_trace_info: StackTraceInfo) -> List[FileLocation]:
        """Find files by searching for class name across the entire repository"""
        logger.info(f"Strategy 3: Broad class name search for {stack_trace_info.file_name}")
        
        found_files = []
        search_pattern = f"**/{stack_trace_info.file_name}"
        
        for src_dir in self.src_directories:
            matches = list(src_dir.glob(search_pattern))
            
            for match in matches:
                if match.is_file() and self._verify_class_match(match, stack_trace_info.class_name):
                    # Try to determine the package path from the file location
                    try:
                        java_root = self._find_java_root(match)
                        actual_package_path = str(match.parent.relative_to(java_root))
                    except:
                        actual_package_path = "unknown"
                    
                    file_location = FileLocation(
                        absolute_path=str(match),
                        relative_path=str(match.relative_to(self.repo_root)),
                        package_path=actual_package_path,
                        class_name=stack_trace_info.class_name,
                        file_size=match.stat().st_size,
                        search_strategy="broad_search"
                    )
                    found_files.append(file_location)
                    logger.info(f"✅ Found broad match: {match.relative_to(self.repo_root)}")
        
        return found_files
    
    def _find_java_root(self, java_file: Path) -> Path:
        """Find the Java source root for a given Java file"""
        for src_dir in self.src_directories:
            try:
                if java_file.is_relative_to(src_dir):
                    return src_dir
            except ValueError:
                continue
        return self.repo_root
    
    def _verify_class_match(self, file_path: Path, expected_class_name: str) -> bool:
        """Verify that a file actually contains the expected class"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                # Read first few lines to check for class declaration
                for i, line in enumerate(f):
                    if i > 50:  # Don't read too much
                        break
                    if f"class {expected_class_name}" in line or f"interface {expected_class_name}" in line:
                        return True
        except Exception as e:
            logger.warning(f"Could not verify class match for {file_path}: {e}")
        
        return False
    
    def search_multiple_files(self, stack_trace_infos: List[StackTraceInfo]) -> Dict[str, List[FileLocation]]:
        """
        Search for multiple files at once
        
        Args:
            stack_trace_infos: List of parsed stack trace information
            
        Returns:
            Dictionary mapping class names to their file locations
        """
        results = {}
        
        for info in stack_trace_infos:
            key = f"{info.full_class_path}.{info.method_name}"
            results[key] = self.find_file(info)
        
        return results
    
    def _find_by_repo_wide_search(self, stack_trace_info: StackTraceInfo) -> List[FileLocation]:
        """Find files by searching the entire repository (fallback strategy)"""
        logger.info(f"Strategy 4: Repository-wide search for {stack_trace_info.file_name}")
        
        found_files = []
        search_pattern = f"**/{stack_trace_info.file_name}"
        
        try:
            # Search from repository root, ignoring source directory restrictions
            matches = list(self.repo_root.glob(search_pattern))
            
            for match in matches:
                if match.is_file() and self._verify_class_match(match, stack_trace_info.class_name):
                    # Try to determine the package path from the file location
                    try:
                        java_root = self._find_java_root(match)
                        actual_package_path = str(match.parent.relative_to(java_root))
                    except:
                        # If we can't determine the java root, use the parent path from repo root
                        actual_package_path = str(match.parent.relative_to(self.repo_root))
                    
                    file_location = FileLocation(
                        absolute_path=str(match),
                        relative_path=str(match.relative_to(self.repo_root)),
                        package_path=actual_package_path,
                        class_name=stack_trace_info.class_name,
                        file_size=match.stat().st_size,
                        search_strategy="repo_wide"
                    )
                    found_files.append(file_location)
                    logger.info(f"✅ Found repo-wide match: {match.relative_to(self.repo_root)}")
        
        except OSError as e:
            logger.error(f"Error in repository-wide search: {e}")
        
        return found_files

    def get_cache_stats(self) -> Dict:
        """Get statistics about the file cache"""
        return {
            "cached_files": len(self.file_cache),
            "source_directories": len(self.src_directories),
            "source_directory_paths": [str(d.relative_to(self.repo_root)) for d in self.src_directories]
        }

# Example usage and testing
if __name__ == "__main__":
    # This is just for testing - in real usage, a valid repo path would be provided
    print("Repository File Finder Test")
    print("=" * 50)
    print("Note: This test requires a valid Java repository path.")
    print("Example usage:")
    print()
    print("from stack_trace_parser import StackTraceParser")
    print("from repo_file_finder import RepositoryFileFinder")
    print()
    print("# Parse stack trace")
    print('parser = StackTraceParser()')
    print('info = parser.parse_single_line("chs.common.styles.PinListDecorationStyle.refreshDecorations()")')
    print()
    print("# Find file in repository")
    print('finder = RepositoryFileFinder("/path/to/repo")')
    print('locations = finder.find_file(info)')
    print()
    print("# Display results")
    print('for loc in locations:')
    print('    print(f"Found: {loc.relative_path} (Strategy: {loc.search_strategy})")')