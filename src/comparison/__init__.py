"""
CSV Comparison and AI Analysis Module
=====================================

This module provides advanced CSV comparison functionality with AI-powered analysis.
It's designed as a standalone addon that integrates with the main file converter application.

Components:
- csv_comparison_engine.py: Core comparison algorithms and AI integration
- comparison_ui.py: Streamlit UI for the comparison functionality
"""

from .csv_comparison_engine import CSVComparisonEngine, ConflictRange

__all__ = ["CSVComparisonEngine", "ConflictRange"]
