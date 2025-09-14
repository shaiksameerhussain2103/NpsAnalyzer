# Stack Trace → Repo Code Analyzer 🔍

## Overview

The Stack Trace → Repo Code Analyzer is a powerful new feature that allows you to analyze Java methods directly from stack trace lines. This tool dynamically searches your repository, extracts relevant code, and provides AI-powered analysis - all without preprocessing the entire repository.

## ✨ Features

### 🎯 **Smart Stack Trace Parsing**
- Parse single or multiple stack trace lines
- Support for various Java stack trace formats
- Extract package path, class name, method name, and line numbers
- Validate parsed information for accuracy

### 🔍 **Dynamic Repository Search**
- Multiple search strategies (exact path, fuzzy matching, broad search)
- No need to preprocess entire repository
- Support for common Java project structures
- Smart source directory detection

### 📝 **Method Extraction**
- Extract target method with proper context
- Include dependent methods and class fields
- Handle large files with intelligent chunking
- Preserve method signatures and dependencies

### 🤖 **AI-Powered Analysis**
- Performance issue detection
- Logic error identification
- Code quality assessment
- Custom analysis questions
- Chunking strategy for large code blocks

### 💾 **Smart Caching**
- JSON-based cache for extracted code
- Cache AI analysis results
- Automatic cache expiration
- Thread-safe operations
- Persistent storage across sessions

## 🚀 Quick Start

### 1. Access the Feature
1. Open the application at `http://localhost:8505`
2. Click on the **"Stack Trace Analyzer"** tab
3. You'll see the complete workflow interface

### 2. Basic Workflow
```
Stack Trace Input → Repository Search → Code Extraction → AI Analysis
```

### 3. Example Usage

**Input Stack Trace:**
```
chs.common.styles.PinListDecorationStyle.refreshDecorations()
```

**Repository Path:**
```
C:\Users\YourName\Projects\YourJavaRepo
```

**Result:**
- Parsed method information
- Located Java file
- Extracted method code with dependencies
- AI analysis with recommendations

## 📁 Module Structure

```
src/stack_trace_analyzer/
├── __init__.py                 # Module initialization
├── analyzer.py                 # Main orchestrator class
├── stack_trace_parser.py       # Stack trace parsing logic
├── repo_file_finder.py         # Dynamic repository search
├── method_extractor.py         # Java method extraction
├── ai_analyzer.py              # AI analysis integration
├── cache_manager.py            # Caching system
└── stack_trace_ui.py           # Streamlit UI interface
```

## 🔧 Technical Details

### Supported Stack Trace Formats
- `package.Class.method()`
- `package.Class.method(File.java:123)`
- `at package.Class.method(File.java:123)`
- `at package.Class.method()`

### Search Strategies
1. **Exact Path**: Direct package path matching
2. **Fuzzy Path**: Partial package path matching  
3. **Broad Search**: Class name search across repository

### Code Extraction Strategies
1. **Complete**: For reasonably-sized files (< 1000 lines)
2. **Chunking**: For large files with windowing approach

### AI Analysis Features
- **Default Analysis**: Performance, logic, quality assessment
- **Custom Questions**: User-defined analysis queries
- **Chunked Analysis**: For large code blocks
- **Context Preservation**: Maintains method dependencies

## 📊 Cache Management

### Cache Types
- **Extracted Code Cache**: Stores method extraction results
- **Analysis Results Cache**: Stores AI analysis outputs

### Cache Features
- Automatic expiration (7 days default)
- LRU eviction for size management
- Thread-safe operations
- JSON persistence

### Cache Statistics
Access cache statistics through the UI:
- Total cached entries
- Cache hit rates
- Average entry age
- Storage location

## 🎮 User Interface

### Step-by-Step Workflow

#### 1. **Stack Trace Input**
- Single line input
- Multiple lines (full stack trace)
- File upload (.txt, .log)

#### 2. **Repository Selection**
- Browse for repository root
- Automatic validation
- Source directory detection

#### 3. **File Search Results**
- View found files
- Multiple search strategies
- File selection options

#### 4. **Code Extraction**
- Preview extracted code
- View extraction details
- Method dependencies

#### 5. **Analysis Options**
- Default comprehensive analysis
- Custom analysis questions
- Export results

## 🔌 Integration

### Seamless Integration
- **No Existing Code Modified**: Complete separate module
- **Tabbed Interface**: Integrated as new tab in main UI
- **Preserved Functionality**: All existing features work unchanged
- **Independent Operation**: Can be used standalone

### AI Pipeline Integration
- Uses existing AI analysis infrastructure
- Consistent response formats
- Compatible with current AI models
- Maintains analysis patterns

## 🛠️ Configuration

### Environment Setup
```python
# The analyzer automatically configures itself
from src.stack_trace_analyzer.analyzer import StackTraceAnalyzer

analyzer = StackTraceAnalyzer()
result = analyzer.analyze_stack_trace(stack_trace_line, repo_path)
```

### Custom Configuration
```python
from src.stack_trace_analyzer.cache_manager import StackTraceAnalyzerCache

# Custom cache configuration
cache = StackTraceAnalyzerCache(
    cache_dir="custom_cache",
    max_age_days=14,
    max_entries=500
)
```

## 📈 Performance

### Optimizations
- **Dynamic Loading**: No upfront repository preprocessing
- **Smart Caching**: Avoid repeated analysis of same methods
- **Chunking Strategy**: Handle large files efficiently
- **Lazy Loading**: Components loaded on demand

### Scalability
- **Repository Size**: Handles large repositories efficiently
- **File Size**: Intelligent chunking for large Java files
- **Memory Usage**: Efficient caching with size limits
- **Response Time**: Fast subsequent analyses via caching

## 🧪 Testing

### Built-in Testing
Each module includes comprehensive test cases:

```bash
# Test individual modules
python src/stack_trace_analyzer/stack_trace_parser.py
python src/stack_trace_analyzer/cache_manager.py
python src/stack_trace_analyzer/analyzer.py
```

### Example Test Cases
- Various stack trace formats
- Different repository structures
- Large file handling
- Cache operations
- Error scenarios

## 🚨 Important Notes

### Complete Independence
- **No Existing Code Changed**: This feature is completely separate
- **Preserved Functionality**: All existing CSV comparison features work exactly as before
- **Modular Design**: Can be enabled/disabled independently
- **Clean Integration**: Added as new tab without disrupting existing workflows

### Error Handling
- Graceful degradation for unsupported formats
- Clear error messages for users
- Comprehensive logging for debugging
- Fallback strategies for edge cases

## 🎯 Use Cases

### Development Scenarios
1. **Stack Trace Investigation**: Analyze problematic methods from production logs
2. **Code Review**: Examine specific methods for quality issues
3. **Performance Debugging**: Identify bottlenecks in critical code paths
4. **Legacy Code Analysis**: Understand complex methods in large codebases

### Team Collaboration
1. **Share Analysis Results**: Export and share method analysis
2. **Custom Questions**: Ask specific questions about code behavior
3. **Documentation**: Generate code analysis documentation
4. **Knowledge Transfer**: Help team understand complex code

## 🔮 Future Enhancements

### Planned Features
- Support for additional languages (Python, C#, etc.)
- Integration with version control systems
- Batch processing for multiple stack traces
- Advanced visualization of code dependencies
- Integration with IDE plugins

### Extensibility
- Plugin architecture for custom analyzers
- Configurable AI prompts
- Custom extraction strategies
- External tool integrations

---

## 📞 Support

For questions or issues related to the Stack Trace Analyzer:
1. Check the logs in the Streamlit interface
2. Review the module documentation in each file
3. Test individual components using the built-in test cases
4. Verify repository path and stack trace format

**The Stack Trace → Repo Code Analyzer is ready to use and fully integrated! 🎉**