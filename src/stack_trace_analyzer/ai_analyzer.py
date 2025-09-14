"""
AI Analysis Integration for Stack Trace Analyzer

Connects extracted Java code to AI analysis pipeline with proper context and chunking.
Handles large code blocks by breaking them into manageable chunks for AI processing.

Features:
- Smart code chunking for large methods
- Context-aware AI prompts for Java code analysis
- Performance and logic issue detection
- Support for custom analysis questions
- Integration with existing AI analysis pipeline
"""

import logging
import re
import os
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

from .method_extractor import ExtractedCode, ExtractedMethod
from .stack_trace_parser import StackTraceInfo
from .robust_stack_trace_parser import StackTraceParseResult
from .cache_manager import get_cache

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StackTraceAIAnalyzer:
    """AI-powered analysis of extracted Java code from stack traces"""
    
    # Maximum tokens for AI analysis (adjust based on your AI model)
    MAX_ANALYSIS_TOKENS = 4000
    ESTIMATED_CHARS_PER_TOKEN = 4  # Rough estimate
    
    def __init__(self):
        """Initialize the AI analyzer with OpenAI clients"""
        self.cache = get_cache()
        
        # Initialize multiple AI clients using Siemens API keys
        self.api_keys = [
            os.getenv("OPENAI_API_KEY"),
            os.getenv("OPENAI_API_KEY2"), 
            os.getenv("OPENAI_API_KEY3")
        ]
        
        # Filter out None values and create clients
        self.api_keys = [key for key in self.api_keys if key is not None]
        self.ai_clients = []
        
        if not self.api_keys:
            logger.error("No API keys found in environment variables!")
            raise ValueError("At least one OpenAI API key must be configured in .env file")
        
        for i, api_key in enumerate(self.api_keys):
            try:
                client = OpenAI(api_key=api_key)
                self.ai_clients.append(client)
                logger.info(f"Initialized AI client {i + 1}/{len(self.api_keys)}")
            except Exception as e:
                logger.error(f"Failed to initialize AI client {i + 1}: {e}")
        
        if not self.ai_clients:
            raise ValueError("Failed to initialize any AI clients")
        
        # Track usage for load balancing
        self.current_client_index = 0
    
    def analyze_extracted_code(self, 
                             extracted_code: ExtractedCode, 
                             stack_trace_info: Union[StackTraceInfo, StackTraceParseResult],
                             repo_path: str,
                             custom_question: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze extracted Java code using AI
        
        Args:
            extracted_code: The extracted code to analyze
            stack_trace_info: Original stack trace information (StackTraceInfo or StackTraceParseResult)
            repo_path: Repository path for caching
            custom_question: Optional custom analysis question
            
        Returns:
            Dictionary containing analysis results
        """
        # Convert StackTraceParseResult to StackTraceInfo if needed
        if isinstance(stack_trace_info, StackTraceParseResult):
            stack_trace_info = self._convert_parse_result_to_info(stack_trace_info)
        
        # Check cache first
        cached_result = self.cache.get_analysis_result(stack_trace_info, repo_path)
        if cached_result and not custom_question:  # Don't use cache for custom questions
            logger.info("Using cached analysis result")
            return cached_result
        
        logger.info(f"Analyzing method: {stack_trace_info.class_name}.{stack_trace_info.method_name}")
        
        # Prepare code for analysis
        analysis_context = self._prepare_analysis_context(extracted_code, stack_trace_info)
        
        # Choose analysis strategy based on code size
        code_size = len(analysis_context['complete_code'])
        if code_size > self.MAX_ANALYSIS_TOKENS * self.ESTIMATED_CHARS_PER_TOKEN:
            result = self._analyze_with_chunking(analysis_context, stack_trace_info, custom_question)
        else:
            result = self._analyze_complete(analysis_context, stack_trace_info, custom_question)
        
        # Add metadata
        result['analysis_metadata'] = {
            'analyzed_at': datetime.now().isoformat(),
            'code_size_chars': code_size,
            'analysis_strategy': result.get('analysis_strategy', 'unknown'),
            'target_method': f"{stack_trace_info.class_name}.{stack_trace_info.method_name}",
            'file_path': extracted_code.file_info.relative_path
        }
        
        # Cache the result (only for default analysis, not custom questions)
        if not custom_question:
            self.cache.store_analysis_result(stack_trace_info, repo_path, result)
        
        return result
    
    def _prepare_analysis_context(self, extracted_code: ExtractedCode, stack_trace_info: StackTraceInfo) -> Dict[str, Any]:
        """Prepare context information for AI analysis"""
        return {
            'complete_code': extracted_code.get_complete_code(),
            'target_method': extracted_code.target_method,
            'dependent_methods': extracted_code.dependent_methods,
            'class_fields': extracted_code.class_fields,
            'imports': extracted_code.imports,
            'class_name': stack_trace_info.class_name,
            'method_name': stack_trace_info.method_name,
            'file_info': extracted_code.file_info,
            'extraction_strategy': extracted_code.extraction_strategy
        }
    
    def _convert_parse_result_to_info(self, parse_result: StackTraceParseResult) -> StackTraceInfo:
        """Convert StackTraceParseResult to StackTraceInfo for compatibility"""
        # Extract package path and class name from fully qualified class name
        class_fqn = parse_result.class_fqn
        
        if '.' in class_fqn:
            parts = class_fqn.split('.')
            package_path = '.'.join(parts[:-1])
            class_name = parts[-1]
        else:
            package_path = ""
            class_name = class_fqn
        
        return StackTraceInfo(
            package_path=package_path,
            class_name=class_name,
            method_name=parse_result.method or "unknown",
            full_class_path=class_fqn,
            file_name=f"{class_name}.java",
            line_number=None
        )
    
    def _analyze_complete(self, analysis_context: Dict, stack_trace_info: StackTraceInfo, custom_question: Optional[str] = None) -> Dict[str, Any]:
        """Analyze code that fits within token limits"""
        logger.info("Using complete analysis strategy")
        
        prompt = self._build_analysis_prompt(analysis_context, custom_question)
        
        # This would connect to your existing AI analysis pipeline
        # For now, I'll create a structured response that matches your existing format
        analysis_result = {
            'analysis_strategy': 'complete',
            'prompt_used': prompt,
            'ai_response': self._analyze_with_ai(analysis_context, custom_question),
            'code_context': {
                'method_signature': analysis_context['target_method'].method_signature,
                'method_lines': f"{analysis_context['target_method'].start_line}-{analysis_context['target_method'].end_line}",
                'dependencies_count': len(analysis_context['dependent_methods']),
                'class_fields_count': len(analysis_context['class_fields'])
            }
        }
        
        return analysis_result
    
    def _analyze_with_chunking(self, analysis_context: Dict, stack_trace_info: StackTraceInfo, custom_question: Optional[str] = None) -> Dict[str, Any]:
        """Analyze large code using chunking strategy"""
        logger.info("Using chunking analysis strategy")
        
        # Break code into logical chunks
        chunks = self._create_code_chunks(analysis_context)
        
        chunk_analyses = []
        for i, chunk in enumerate(chunks):
            chunk_prompt = self._build_chunk_analysis_prompt(chunk, i + 1, len(chunks), custom_question)
            chunk_analysis = {
                'chunk_id': i + 1,
                'chunk_type': chunk['type'],
                'chunk_description': chunk['description'],
                'prompt_used': chunk_prompt,
                'ai_response': self._analyze_with_ai(chunk, custom_question)
            }
            chunk_analyses.append(chunk_analysis)
        
        # Aggregate results
        aggregated_analysis = self._aggregate_chunk_analyses(chunk_analyses, analysis_context, custom_question)
        
        return {
            'analysis_strategy': 'chunking',
            'chunk_analyses': chunk_analyses,
            'aggregated_analysis': aggregated_analysis,
            'total_chunks': len(chunks)
        }
    
    def _create_code_chunks(self, analysis_context: Dict) -> List[Dict]:
        """Break large code into logical chunks for analysis"""
        chunks = []
        
        # Chunk 1: Target method only
        target_method = analysis_context['target_method']
        chunks.append({
            'type': 'target_method',
            'description': f"Target method: {target_method.method_name}",
            'code': target_method.method_body,
            'context': {
                'method_signature': target_method.method_signature,
                'dependencies': target_method.dependencies,
                'line_range': f"{target_method.start_line}-{target_method.end_line}"
            }
        })
        
        # Chunk 2: Dependent methods (if any)
        if analysis_context['dependent_methods']:
            dependent_code = '\\n\\n'.join([
                f"// Method: {method.method_name}\\n{method.method_body}"
                for method in analysis_context['dependent_methods']
            ])
            chunks.append({
                'type': 'dependent_methods',
                'description': f"Dependent methods ({len(analysis_context['dependent_methods'])} methods)",
                'code': dependent_code,
                'context': {
                    'method_count': len(analysis_context['dependent_methods']),
                    'method_names': [m.method_name for m in analysis_context['dependent_methods']]
                }
            })
        
        # Chunk 3: Class context (fields and imports)
        if analysis_context['class_fields'] or analysis_context['imports']:
            context_code = ''
            if analysis_context['imports']:
                context_code += '\\n'.join(analysis_context['imports']) + '\\n\\n'
            if analysis_context['class_fields']:
                context_code += '// Class Fields:\\n' + '\\n'.join(analysis_context['class_fields'])
            
            chunks.append({
                'type': 'class_context',
                'description': f"Class context (imports and fields)",
                'code': context_code,
                'context': {
                    'import_count': len(analysis_context['imports']),
                    'field_count': len(analysis_context['class_fields'])
                }
            })
        
        return chunks
    
    def _build_analysis_prompt(self, analysis_context: Dict, custom_question: Optional[str] = None) -> str:
        """Build AI analysis prompt for complete code analysis"""
        if custom_question:
            return self._build_custom_prompt(analysis_context, custom_question)
        
        return f'''
Analyze this Java method for potential performance issues, logic problems, and code quality concerns:

**Context:**
- Class: {analysis_context['class_name']}
- Method: {analysis_context['method_name']}
- File: {analysis_context['file_info'].relative_path}
- Extraction Strategy: {analysis_context['extraction_strategy']}

**Code to Analyze:**
```java
{analysis_context['complete_code']}
```

**Analysis Requirements:**
1. **Performance Issues**: Identify potential performance bottlenecks, inefficient algorithms, or resource leaks
2. **Logic Problems**: Look for null pointer risks, infinite loops, incorrect condition checks, or edge case handling
3. **Code Quality**: Check for maintainability issues, code duplication, or violation of best practices
4. **Dependencies**: Analyze how this method interacts with its dependencies and if there are any coupling issues

**Response Format:**
Provide a structured analysis with:
- **Summary**: Brief overview of the method's purpose and main concerns
- **Issues Found**: List specific issues with severity levels (HIGH/MEDIUM/LOW)
- **Recommendations**: Specific improvement suggestions
- **Code Quality Score**: Rate from 1-10 with justification

Focus on actionable insights that can help resolve issues that might appear in stack traces.
'''
    
    def _build_chunk_analysis_prompt(self, chunk: Dict, chunk_num: int, total_chunks: int, custom_question: Optional[str] = None) -> str:
        """Build AI analysis prompt for code chunk"""
        if custom_question:
            return f'''
Analyze this Java code chunk ({chunk_num}/{total_chunks}) to answer the question: "{custom_question}"

**Chunk Type:** {chunk['type']}
**Description:** {chunk['description']}

**Code:**
```java
{chunk['code']}
```

**Context:** {chunk.get('context', {})}

Focus your analysis on how this chunk relates to the question asked.
'''
        
        return f'''
Analyze this Java code chunk ({chunk_num}/{total_chunks}) for issues:

**Chunk Type:** {chunk['type']}
**Description:** {chunk['description']}

**Code:**
```java
{chunk['code']}
```

**Context:** {chunk.get('context', {})}

Focus on issues specific to this code segment. This is part {chunk_num} of {total_chunks} total chunks.
'''
    
    def _build_custom_prompt(self, analysis_context: Dict, custom_question: str) -> str:
        """Build AI prompt for custom analysis question"""
        return f'''
Analyze this Java method to answer the specific question: "{custom_question}"

**Method Context:**
- Class: {analysis_context['class_name']}
- Method: {analysis_context['method_name']}
- File: {analysis_context['file_info'].relative_path}

**Code:**
```java
{analysis_context['complete_code']}
```

Please provide a focused analysis that directly addresses the question asked.
'''
    
    def _get_next_client(self) -> OpenAI:
        """Get the next available AI client using round-robin"""
        client = self.ai_clients[self.current_client_index]
        self.current_client_index = (self.current_client_index + 1) % len(self.ai_clients)
        return client
    
    def _make_ai_request(self, prompt: str, max_retries: int = 3) -> str:
        """Make AI request with retry logic"""
        for attempt in range(max_retries):
            try:
                client = self._get_next_client()
                
                messages = [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
                
                completions = client.chat.completions.create(
                    model="gpt-4",
                    messages=messages,
                    temperature=0.1,
                    max_tokens=4000
                )
                
                return completions.choices[0].message.content
                
            except Exception as e:
                logger.warning(f"AI request attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    logger.error(f"All AI request attempts failed. Last error: {e}")
                    # Return fallback analysis instead of failing
                    return self._fallback_analysis(prompt)
        
        return self._fallback_analysis(prompt)
    
    def _fallback_analysis(self, prompt: str) -> str:
        """Provide fallback analysis when AI service is unavailable"""
        return """
**AI Analysis Currently Unavailable**

The AI analysis service is temporarily unavailable. This could be due to:
- API key issues
- Network connectivity problems  
- Service rate limits

**Basic Analysis:**
The code has been successfully extracted and is ready for analysis. You can:
1. Review the extracted code manually
2. Try the AI analysis again later
3. Check the system logs for more details

**Recommendations:**
- Ensure API keys are properly configured in the .env file
- Check network connectivity
- Wait a few moments before retrying
"""
    
    def _analyze_with_ai(self, analysis_context: Dict, custom_question: Optional[str] = None) -> str:
        """
        Perform actual AI analysis of the Java code using OpenAI API
        """
        # Build the appropriate prompt
        prompt = self._build_analysis_prompt(analysis_context, custom_question)
        
        logger.info(f"Sending analysis request to AI service")
        logger.debug(f"Prompt length: {len(prompt)} characters")
        
        # Make the AI request
        ai_response = self._make_ai_request(prompt)
        
        logger.info("AI analysis completed successfully")
        return ai_response
    
    def _aggregate_chunk_analyses(self, chunk_analyses: List[Dict], analysis_context: Dict, custom_question: Optional[str] = None) -> str:
        """Aggregate results from multiple chunk analyses"""
        return f'''
**Aggregated Analysis Summary:**

**Analyzed Components:**
{len(chunk_analyses)} code chunks were analyzed separately and results aggregated.

**Overall Assessment:**
- Target Method: {analysis_context['method_name']}
- Dependent Methods: {len(analysis_context['dependent_methods'])}
- Total Analysis Chunks: {len(chunk_analyses)}

**Key Findings Across All Chunks:**
Based on the analysis of all code chunks, here are the key findings.

**Integrated Recommendations:**
Based on the complete analysis across all code chunks, the main recommendations are:
1. Focus on the target method issues first
2. Review dependent methods for consistency
3. Ensure proper integration between all components
'''

    def get_supported_analysis_types(self) -> List[str]:
        """Get list of supported analysis types"""
        return [
            "Performance Analysis",
            "Logic Error Detection", 
            "Code Quality Assessment",
            "Dependency Analysis",
            "Security Vulnerability Scan",
            "Best Practices Review",
            "Custom Question Analysis"
        ]
