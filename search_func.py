with open('templates/index.html', 'r') as f:
    content = f.read()
    
# Find askInteractiveQuestion
index = content.find('askInteractiveQuestion')
if index != -1:
    # Get line number
    line_num = content[:index].count('\n') + 1
    print(f'Found askInteractiveQuestion at line {line_num}')
    
    # Extract function (rough)
    func_start = content.rfind('function', 0, index)
    if func_start != -1:
        # Find the closing brace
        brace_count = 0
        pos = content.find('{', func_start)
        if pos != -1:
            brace_count = 1
            end_pos = pos + 1
            
            while brace_count > 0 and end_pos < len(content):
                if content[end_pos] == '{':
                    brace_count += 1
                elif content[end_pos] == '}':
                    brace_count -= 1
                end_pos += 1
            
            # Extract and print function
            function_code = content[func_start:end_pos]
            print(f'\nFunction code (first 2000 chars):')
            print(function_code[:2000])
            
            # Look for chat history update logic
            if 'updateChatHistory' in function_code or 'chat-history' in function_code:
                print('\n\nFound chat history update logic in the function!')
                
    # Also search for chat history separately
    chat_index = content.find('updateChatHistory')
    if chat_index != -1:
        chat_line = content[:chat_index].count('\n') + 1
        print(f'\n\nFound updateChatHistory at line {chat_line}')
else:
    print('askInteractiveQuestion not found')