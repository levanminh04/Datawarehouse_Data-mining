import glob
import re

search_pattern = r"os\.path\.dirname\(__file__\)"
replace_string = "os.getcwd()"

for file in glob.glob('0*.py') + glob.glob('0*.ipynb'):
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    new_content = re.sub(search_pattern, replace_string, content)
    
    with open(file, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f'Fixed {file}')
