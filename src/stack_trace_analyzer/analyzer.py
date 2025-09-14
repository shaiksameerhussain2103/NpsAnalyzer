"""
Stack Trace Analyzer Main Module

Main orchestrator for the Stack Trace → Repo Code Analyzer feature.
Provides a unified interface that combines all components.

This is the entry point for the complete stack trace analysis workflow.
"""

import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

from .stack_trace_parser import StackTraceParser, StackTraceInfo
from .repo_file_finder import RepositoryFileFinder, FileLocation
from .method_extractor import JavaMethodExtractor, ExtractedCode
from .ai_analyzer import StackTraceAIAnalyzer
from .cache_manager import get_cache

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StackTraceAnalyzer:
    """Main analyzer class that orchestrates the complete workflow"""
    
    def __init__(self):
        """Initialize all components"""
        self.parser = StackTraceParser()
        self.extractor = JavaMethodExtractor()
        self.ai_analyzer = StackTraceAIAnalyzer()
        self.cache = get_cache()
        
        logger.info("Stack Trace Analyzer initialized")
    
    def analyze_stack_trace(self, 
                           stack_trace_line: str, 
                           repo_path: str,
                           custom_question: Optional[str] = None) -> Dict[str, Any]:
        """
        Complete analysis workflow from stack trace line to AI results
        
        Args:
            stack_trace_line: Stack trace line to analyze
            repo_path: Path to the repository
            custom_question: Optional custom analysis question
            
        Returns:
            Complete analysis results
        """
        logger.info(f"Starting analysis for: {stack_trace_line}")
        
        result = {
            "success": False,
            "stack_trace_line": stack_trace_line,
            "repo_path": repo_path,
            "custom_question": custom_question,
            "steps": {}
        }
        
        try:
            # Step 1: Parse stack trace
            parsed_info = self.parser.parse_single_line(stack_trace_line)
            if not parsed_info:
                result["error"] = "Failed to parse stack trace line"
                return result
            
            result["steps"]["parsing"] = {
                "success": True,
                "parsed_info": parsed_info.to_dict()
            }
            logger.info(f"✅ Parsed: {parsed_info.class_name}.{parsed_info.method_name}")
            
            # Step 2: Find files in repository
            finder = RepositoryFileFinder(repo_path)
            found_files = finder.find_file(parsed_info)
            
            if not found_files:
                result["error"] = "No matching files found in repository"
                result["steps"]["file_search"] = {"success": False, "found_files": []}
                return result
            
            result["steps"]["file_search"] = {
                "success": True,
                "found_files": [f.to_dict() for f in found_files]
            }
            logger.info(f"✅ Found {len(found_files)} file(s)")
            
            # Step 3: Extract code (use first found file)
            file_location = found_files[0]
            extracted_code = self.extractor.extract_method(file_location, parsed_info)
            
            if not extracted_code:
                result["error"] = "Failed to extract method code"
                result["steps"]["code_extraction"] = {"success": False}
                return result
            
            result["steps"]["code_extraction"] = {
                "success": True,
                "extracted_code": extracted_code.to_dict()
            }
            logger.info(f"✅ Extracted method: {parsed_info.method_name}")
            
            # Step 4: AI Analysis
            analysis_result = self.ai_analyzer.analyze_extracted_code(
                extracted_code, parsed_info, repo_path, custom_question
            )
            
            result["steps"]["ai_analysis"] = {
                "success": True,
                "analysis_result": analysis_result
            }
            logger.info("✅ AI analysis completed")
            
            result["success"] = True
            result["final_result"] = analysis_result
            
        except Exception as e:
            result["error"] = str(e)
            result["exception"] = type(e).__name__
            logger.error(f"Analysis failed: {e}")
        
        return result
    
    def analyze_multiple_stack_traces(self, 
                                    stack_trace_text: str,
                                    repo_path: str) -> Dict[str, Any]:
        """
        Analyze multiple stack trace lines
        
        Args:
            stack_trace_text: Multi-line stack trace text
            repo_path: Path to the repository
            
        Returns:
            Results for all analyzed lines
        """
        logger.info("Starting multiple stack trace analysis")
        
        # Parse all lines
        parsed_lines = self.parser.parse_multiple_lines(stack_trace_text)
        
        if not parsed_lines:
            return {
                "success": False,
                "error": "No valid stack trace lines found",
                "results": []
            }
        
        results = []
        for i, parsed_info in enumerate(parsed_lines, 1):
            logger.info(f"Analyzing line {i}/{len(parsed_lines)}: {parsed_info.method_name}")
            
            line_result = self.analyze_stack_trace(
                f"{parsed_info.full_class_path}.{parsed_info.method_name}()",
                repo_path
            )
            
            line_result["line_number"] = i
            results.append(line_result)
        
        successful_analyses = sum(1 for r in results if r["success"])
        
        return {
            "success": True,
            "total_lines": len(parsed_lines),
            "successful_analyses": successful_analyses,
            "results": results,
            "summary": f"Analyzed {successful_analyses}/{len(parsed_lines)} stack trace lines successfully"
        }
    
    def get_cache_summary(self) -> Dict[str, Any]:
        """Get summary of cached analyses"""
        return self.cache.get_cache_stats()
    
    def clear_cache(self):
        """Clear all cached data"""
        self.cache.clear_cache()
        logger.info("Cache cleared")

# Convenience functions for direct usage
def analyze_single_stack_trace(stack_trace_line: str, 
                              repo_path: str,
                              custom_question: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to analyze a single stack trace line
    
    Args:
        stack_trace_line: Stack trace line to analyze
        repo_path: Path to the repository
        custom_question: Optional custom analysis question
        
    Returns:
        Analysis results
    """
    analyzer = StackTraceAnalyzer()
    return analyzer.analyze_stack_trace(stack_trace_line, repo_path, custom_question)

def analyze_multiple_stack_traces(stack_trace_text: str, repo_path: str) -> Dict[str, Any]:
    """
    Convenience function to analyze multiple stack trace lines
    
    Args:
        stack_trace_text: Multi-line stack trace text
        repo_path: Path to the repository
        
    Returns:
        Analysis results for all lines
    """
    analyzer = StackTraceAnalyzer()
    return analyzer.analyze_multiple_stack_traces(stack_trace_text, repo_path)

# Example usage
if __name__ == "__main__":
    print("Stack Trace Analyzer - Main Module")
    print("=" * 50)
    
    # Example usage
    example_stack_trace = "chs.common.styles.PinListDecorationStyle.refreshDecorations()"
    example_repo_path = "C:\\Users\\Z0055DXU\\mgnoscan\\repo\\iesd-25\\chs_home"
    
    print(f"Example stack trace: {example_stack_trace}")
    print(f"Example repo path: {example_repo_path}")
    print()
    print("To use this analyzer:")
    print("1. Create an analyzer: analyzer = StackTraceAnalyzer()")
    print("2. Run analysis: result = analyzer.analyze_stack_trace(stack_trace, repo_path)")
    print("3. Check results: print(result)")
    print()
    print("Available methods:")
    analyzer = StackTraceAnalyzer()
    print("- analyze_stack_trace()")
    print("- analyze_multiple_stack_traces()")
    print("- get_cache_summary()")
    print("- clear_cache()")
    print()
    print("Cache stats:")
    stats = analyzer.get_cache_summary()
    for key, value in stats.items():
        print(f"  {key}: {value}")