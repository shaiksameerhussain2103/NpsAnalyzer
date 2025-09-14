import re
import sys
sys.path.append('src')

file_path = r'C:\Users\Z0055DXU\mgnoscan\repo\iesd-25\datamodel_src\tests\src\chs\common\attr\AttributeValidatorFactoryDescriptionTest.java'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')
method_name = 'testIsVersionShortDescriptionUniqueNoRevisionsUniqueDesc'

# Find the method line
method_line_num = None
method_line = None
for i, line in enumerate(lines):
    if method_name in line:
        method_line_num = i
        method_line = line
        print(f'Method found at line {i+1}: {line}')
        break

if method_line_num is not None:
    # The exact pattern from JavaMethodExtractor
    method_pattern = re.compile(
        r'^(\s*(?:public|private|protected|static|final|abstract|synchronized|\s)*)\s+'
        r'(?:[\w<>[\],\s]+\s+)?'  # Return type
        r'(\w+)\s*\('               # Method name
        r'([^)]*)\)\s*'             # Parameters
        r'(?:throws\s+[\w\s,]+)?\s*'# Throws clause
        r'[{;]',                    # Opening brace or semicolon
        re.MULTILINE
    )
    
    print(f'\nMethod line: "{method_line}"')
    print(f'Next line: "{lines[method_line_num + 1]}"')
    
    # Test single line
    match = method_pattern.search(method_line)
    if match:
        print('✅ Single line matches')
        print(f'  Method name captured: "{match.group(2)}"')
        print(f'  Expected method name: "{method_name}"')
    else:
        print('❌ Single line does not match')
        
        # The method signature might span multiple lines
        # Try with next line included
        combined = method_line + '\n' + lines[method_line_num + 1]
        match2 = method_pattern.search(combined)
        if match2:
            print('✅ Multi-line matches')
            print(f'  Method name captured: "{match2.group(2)}"')
        else:
            print('❌ Multi-line also fails')
            print(f'Combined: "{combined}"')