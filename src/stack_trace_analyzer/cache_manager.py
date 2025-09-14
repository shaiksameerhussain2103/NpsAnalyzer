"""
Cache Management System for Stack Trace Analyzer

Provides JSON-based caching to store extracted code snippets and analysis results.
This simulates memory across stateless API calls by persisting data to disk.

Features:
- Store and retrieve extracted code snippets
- Cache AI analysis results
- Automatic cache expiration and cleanup
- Persistent storage across application restarts
- Thread-safe operations
"""

import json
import hashlib
import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Any, List
from dataclasses import asdict, dataclass
import time

from .method_extractor import ExtractedCode
from .stack_trace_parser import StackTraceInfo

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class CacheEntry:
    """A single cache entry with metadata"""
    key: str
    data: Dict
    timestamp: datetime
    access_count: int
    last_accessed: datetime
    entry_type: str  # 'extracted_code', 'analysis_result', etc.
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "key": self.key,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat(),
            "entry_type": self.entry_type
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CacheEntry':
        """Create CacheEntry from dictionary"""
        return cls(
            key=data["key"],
            data=data["data"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            access_count=data["access_count"],
            last_accessed=datetime.fromisoformat(data["last_accessed"]),
            entry_type=data["entry_type"]
        )

class StackTraceAnalyzerCache:
    """Thread-safe cache for stack trace analyzer results"""
    
    def __init__(self, cache_dir: str = None, max_age_days: int = 7, max_entries: int = 1000):
        """
        Initialize the cache system
        
        Args:
            cache_dir: Directory to store cache files (defaults to ./cache)
            max_age_days: Maximum age of cache entries in days
            max_entries: Maximum number of entries before cleanup
        """
        self.cache_dir = Path(cache_dir) if cache_dir else Path("cache")
        self.max_age = timedelta(days=max_age_days)
        self.max_entries = max_entries
        
        # Thread safety
        self.lock = threading.RLock()
        
        # In-memory cache for fast access
        self.memory_cache: Dict[str, CacheEntry] = {}
        
        # Initialize cache directory and files
        self._initialize_cache()
        
        logger.info(f"Initialized cache at: {self.cache_dir.absolute()}")
        logger.info(f"Max age: {max_age_days} days, Max entries: {max_entries}")
    
    def _initialize_cache(self):
        """Initialize cache directory and load existing cache"""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache files
        self.extracted_code_file = self.cache_dir / "extracted_code.json"
        self.analysis_results_file = self.cache_dir / "analysis_results.json"
        self.cache_metadata_file = self.cache_dir / "cache_metadata.json"
        
        # Load existing cache
        self._load_cache()
    
    def _generate_key(self, stack_trace_info: StackTraceInfo, repo_path: str) -> str:
        """Generate a unique cache key for a stack trace analysis"""
        key_string = f"{repo_path}::{stack_trace_info.full_class_path}::{stack_trace_info.method_name}"
        return hashlib.sha256(key_string.encode()).hexdigest()[:16]
    
    def _load_cache(self):
        """Load cache from disk into memory"""
        with self.lock:
            try:
                # Load extracted code cache
                if self.extracted_code_file.exists():
                    with open(self.extracted_code_file, 'r', encoding='utf-8') as f:
                        extracted_data = json.load(f)
                        for key, entry_data in extracted_data.items():
                            self.memory_cache[key] = CacheEntry.from_dict(entry_data)
                
                # Load analysis results cache
                if self.analysis_results_file.exists():
                    with open(self.analysis_results_file, 'r', encoding='utf-8') as f:
                        analysis_data = json.load(f)
                        for key, entry_data in analysis_data.items():
                            analysis_key = f"analysis_{key}"
                            self.memory_cache[analysis_key] = CacheEntry.from_dict(entry_data)
                
                logger.info(f"Loaded {len(self.memory_cache)} entries from cache")
                
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}")
                self.memory_cache = {}
    
    def _save_cache(self):
        """Save cache from memory to disk"""
        with self.lock:
            try:
                extracted_cache = {}
                analysis_cache = {}
                
                for key, entry in self.memory_cache.items():
                    if entry.entry_type == 'extracted_code':
                        extracted_cache[key] = entry.to_dict()
                    elif entry.entry_type == 'analysis_result':
                        analysis_key = key.replace('analysis_', '')
                        analysis_cache[analysis_key] = entry.to_dict()
                
                # Save extracted code cache
                if extracted_cache:
                    with open(self.extracted_code_file, 'w', encoding='utf-8') as f:
                        json.dump(extracted_cache, f, indent=2)
                
                # Save analysis results cache
                if analysis_cache:
                    with open(self.analysis_results_file, 'w', encoding='utf-8') as f:
                        json.dump(analysis_cache, f, indent=2)
                
                # Save metadata
                metadata = {
                    "last_updated": datetime.now().isoformat(),
                    "total_entries": len(self.memory_cache),
                    "cache_stats": self.get_cache_stats()
                }
                with open(self.cache_metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2)
                
                logger.info(f"Saved {len(self.memory_cache)} entries to cache")
                
            except Exception as e:
                logger.error(f"Failed to save cache: {e}")
    
    def store_extracted_code(self, stack_trace_info: StackTraceInfo, repo_path: str, extracted_code: ExtractedCode):
        """
        Store extracted code in cache
        
        Args:
            stack_trace_info: Stack trace information
            repo_path: Repository path
            extracted_code: Extracted code to cache
        """
        with self.lock:
            key = self._generate_key(stack_trace_info, repo_path)
            
            entry = CacheEntry(
                key=key,
                data=extracted_code.to_dict(),
                timestamp=datetime.now(),
                access_count=0,
                last_accessed=datetime.now(),
                entry_type='extracted_code'
            )
            
            self.memory_cache[key] = entry
            
            logger.info(f"Cached extracted code for {stack_trace_info.class_name}.{stack_trace_info.method_name}")
            
            # Auto-save periodically
            if len(self.memory_cache) % 10 == 0:
                self._save_cache()
    
    def get_extracted_code(self, stack_trace_info: StackTraceInfo, repo_path: str) -> Optional[ExtractedCode]:
        """
        Retrieve extracted code from cache
        
        Args:
            stack_trace_info: Stack trace information
            repo_path: Repository path
            
        Returns:
            ExtractedCode if found in cache, None otherwise
        """
        with self.lock:
            key = self._generate_key(stack_trace_info, repo_path)
            
            if key in self.memory_cache:
                entry = self.memory_cache[key]
                
                # Check if entry is still valid
                if datetime.now() - entry.timestamp <= self.max_age:
                    # Update access statistics
                    entry.access_count += 1
                    entry.last_accessed = datetime.now()
                    
                    logger.info(f"Cache hit for {stack_trace_info.class_name}.{stack_trace_info.method_name}")
                    
                    # Convert back to ExtractedCode object
                    # Note: This is a simplified conversion - in practice you might want to 
                    # reconstruct the full ExtractedCode object with all its dataclass fields
                    return entry.data
                else:
                    # Entry is too old, remove it
                    del self.memory_cache[key]
                    logger.info(f"Removed expired cache entry for {key}")
            
            return None
    
    def store_analysis_result(self, stack_trace_info: StackTraceInfo, repo_path: str, analysis_result: Dict):
        """
        Store AI analysis result in cache
        
        Args:
            stack_trace_info: Stack trace information
            repo_path: Repository path
            analysis_result: Analysis result to cache
        """
        with self.lock:
            base_key = self._generate_key(stack_trace_info, repo_path)
            key = f"analysis_{base_key}"
            
            entry = CacheEntry(
                key=key,
                data=analysis_result,
                timestamp=datetime.now(),
                access_count=0,
                last_accessed=datetime.now(),
                entry_type='analysis_result'
            )
            
            self.memory_cache[key] = entry
            
            logger.info(f"Cached analysis result for {stack_trace_info.class_name}.{stack_trace_info.method_name}")
            
            # Auto-save periodically
            if len(self.memory_cache) % 10 == 0:
                self._save_cache()
    
    def get_analysis_result(self, stack_trace_info: StackTraceInfo, repo_path: str) -> Optional[Dict]:
        """
        Retrieve AI analysis result from cache
        
        Args:
            stack_trace_info: Stack trace information
            repo_path: Repository path
            
        Returns:
            Analysis result if found in cache, None otherwise
        """
        with self.lock:
            base_key = self._generate_key(stack_trace_info, repo_path)
            key = f"analysis_{base_key}"
            
            if key in self.memory_cache:
                entry = self.memory_cache[key]
                
                # Check if entry is still valid
                if datetime.now() - entry.timestamp <= self.max_age:
                    # Update access statistics
                    entry.access_count += 1
                    entry.last_accessed = datetime.now()
                    
                    logger.info(f"Cache hit for analysis of {stack_trace_info.class_name}.{stack_trace_info.method_name}")
                    return entry.data
                else:
                    # Entry is too old, remove it
                    del self.memory_cache[key]
                    logger.info(f"Removed expired analysis cache entry for {key}")
            
            return None
    
    def cleanup_cache(self):
        """Remove old and excessive cache entries"""
        with self.lock:
            now = datetime.now()
            removed_count = 0
            
            # Remove expired entries
            expired_keys = []
            for key, entry in self.memory_cache.items():
                if now - entry.timestamp > self.max_age:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.memory_cache[key]
                removed_count += 1
            
            # Remove least recently used entries if cache is too large
            if len(self.memory_cache) > self.max_entries:
                sorted_entries = sorted(
                    self.memory_cache.items(),
                    key=lambda x: x[1].last_accessed
                )
                
                entries_to_remove = len(self.memory_cache) - self.max_entries
                for i in range(entries_to_remove):
                    key = sorted_entries[i][0]
                    del self.memory_cache[key]
                    removed_count += 1
            
            if removed_count > 0:
                logger.info(f"Cleaned up {removed_count} cache entries")
                self._save_cache()
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        with self.lock:
            if not self.memory_cache:
                return {
                    "total_entries": 0,
                    "extracted_code_entries": 0,
                    "analysis_result_entries": 0,
                    "cache_hit_rate": 0.0,
                    "average_age_hours": 0.0
                }
            
            extracted_count = sum(1 for e in self.memory_cache.values() if e.entry_type == 'extracted_code')
            analysis_count = sum(1 for e in self.memory_cache.values() if e.entry_type == 'analysis_result')
            
            total_access_count = sum(e.access_count for e in self.memory_cache.values())
            total_entries = len(self.memory_cache)
            
            # Calculate average age
            now = datetime.now()
            total_age_hours = sum((now - e.timestamp).total_seconds() / 3600 for e in self.memory_cache.values())
            average_age = total_age_hours / total_entries if total_entries > 0 else 0
            
            return {
                "total_entries": total_entries,
                "extracted_code_entries": extracted_count,
                "analysis_result_entries": analysis_count,
                "total_access_count": total_access_count,
                "average_age_hours": round(average_age, 2),
                "cache_directory": str(self.cache_dir.absolute())
            }
    
    def clear_cache(self):
        """Clear all cache entries"""
        with self.lock:
            self.memory_cache.clear()
            
            # Remove cache files
            for cache_file in [self.extracted_code_file, self.analysis_results_file, self.cache_metadata_file]:
                if cache_file.exists():
                    cache_file.unlink()
            
            logger.info("Cache cleared")
    
    def save_and_close(self):
        """Save cache and cleanup resources"""
        with self.lock:
            self._save_cache()
            logger.info("Cache saved and closed")

# Global cache instance
_global_cache: Optional[StackTraceAnalyzerCache] = None

def get_cache() -> StackTraceAnalyzerCache:
    """Get the global cache instance"""
    global _global_cache
    if _global_cache is None:
        _global_cache = StackTraceAnalyzerCache()
    return _global_cache

# Example usage and testing
if __name__ == "__main__":
    print("Stack Trace Analyzer Cache Test")
    print("=" * 50)
    
    # Initialize cache
    cache = StackTraceAnalyzerCache(cache_dir="test_cache")
    
    # Show cache stats
    stats = cache.get_cache_stats()
    print("Cache Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Cleanup test cache
    cache.clear_cache()
    print("\\nCache test completed")