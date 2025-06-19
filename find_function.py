#!/usr/bin/env python3
import re

def find_function_in_file(file_path, function_name):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Search for the function
    pattern = rf'function\s+{function_name}\s*\('
    match = re.search(pattern, content)
    
    if match:
        start_pos = match.start()
        line_num = content[:start_pos].count('\n') + 1
        
        # Find the end of the function (rough approximation)
        brace_count = 0
        pos = content.find('{', start_pos)
        if pos == -1:
            return None
            
        brace_count = 1
        end_pos = pos + 1
        
        while brace_count > 0 and end_pos < len(content):
            if content[end_pos] == '{':
                brace_count += 1
            elif content[end_pos] == '}':
                brace_count -= 1
            end_pos += 1
        
        # Extract function
        function_text = content[start_pos:end_pos]
        
        return {
            'line_number': line_num,
            'function': function_text,
            'start_line': line_num,
            'end_line': line_num + function_text.count('\n')
        }
    
    # Try to find any occurrence
    pos = content.find(function_name)
    if pos != -1:
        line_num = content[:pos].count('\n') + 1
        # Get context
        lines = content.split('\n')
        start_line = max(0, line_num - 10)
        end_line = min(len(lines), line_num + 50)
        context = '\n'.join(lines[start_line:end_line])
        
        return {
            'line_number': line_num,
            'context': context,
            'found_as': 'reference'
        }
    
    return None

# Search for the function
result = find_function_in_file('templates/index.html', 'askInteractiveQuestion')

if result:
    if 'function' in result:
        print(f"Found function definition at line {result['line_number']}")
        print(f"Function spans lines {result['start_line']} to {result['end_line']}")
        print("\nFunction content:")
        print(result['function'][:2000])  # Print first 2000 chars
    else:
        print(f"Found reference at line {result['line_number']}")
        print("\nContext:")
        print(result['context'])
else:
    print("Function not found")