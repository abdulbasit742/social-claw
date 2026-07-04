import re, sys

with open('skills/viral_optimize.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add UTF-8 stdout fix right after the function docstring
old_marker = '    """Standalone CLI: print today\'s trending keywords + 10 viral ideas + hashtags."""\n    print("\\n" + "="*70)'
new_marker = '    """Standalone CLI: print today\'s trending keywords + 10 viral ideas + hashtags."""\n    import io\n    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")\n    print("\\n" + "="*70)'
content = content.replace(old_marker, new_marker, 1)

# Remove all emoji using regex
emoji_pattern = re.compile(
    '[\U0001F600-\U0001F64F'
    '\U0001F300-\U0001F5FF'
    '\U0001F680-\U0001F6FF'
    '\U0001F1E0-\U0001F1FF'
    '\U00002702-\U000027B0'
    '\U000024C2-\U0001F251'
    '\U0001f926-\U0001f937'
    '\u2640-\u2642'
    '\u2600-\u2B55'
    '\u200d\u23cf\u23e9\u231a\ufe0f\u3030'
    ']+', flags=re.UNICODE
)
content = emoji_pattern.sub('', content)

# Also replace bullet dots and checkmarks which cause issues
content = content.replace('\u2022', '*')
content = content.replace('\u2014', '--')
content = content.replace('\u2713', 'OK')
content = content.replace('\u2705', '[OK]')
content = content.replace('\u274c', '[X]')

with open('skills/viral_optimize.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done - emoji removed and UTF-8 stdout added successfully')
