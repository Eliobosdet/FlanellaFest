import os
import re

directory = r"c:\Lavoro\FlanellaFest-main\FlanellaFest-main\templates\festival"
for root, _, files in os.walk(directory):
    for f in files:
        if f.endswith('.html'):
            path = os.path.join(root, f)
            with open(path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # We want to remove specific inline CSS that is forcing the old green theme and fonts
            # but preserve other inline styles if possible
            content = re.sub(r'color:\s*#[a-fA-F0-9]{6};?\s*', '', content) 
            content = re.sub(r'background-color:\s*#[a-fA-F0-9]{6}\s*!important;?\s*', '', content)
            content = re.sub(r'background-color:\s*#[a-fA-F0-9]{6};?\s*', '', content)
            content = re.sub(r'border:\s*[^;]*#[a-fA-F0-9]{6};?\s*', '', content)
            content = re.sub(r'border-color:\s*#[a-fA-F0-9]{6};?\s*', '', content)
            content = re.sub(r"font-family:\s*'Courier New',\s*monospace;?\s*", '', content)
            content = re.sub(r"font-family:\s*[^;]*monospace;?\s*", '', content)
            
            # Clean up empty style="" or style=" " attributes
            content = re.sub(r'style="\s+"', '', content)
            content = re.sub(r'style=""', '', content)

            with open(path, 'w', encoding='utf-8') as file:
                file.write(content)
print("Inline styles cleaned!")
