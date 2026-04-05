import os
import re

def remove_emojis(text):
    # Regex for emojis and other non-ASCII symbols that cause issues on Windows CP1256
    emoji_pattern = re.compile(r'[\U00010000-\U0010FFFF\u2600-\u27BF\u274c\u2714\u2705\u26a0]')
    return emoji_pattern.sub('', text)

def process_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        new_content = remove_emojis(content)
        
        if content != new_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Cleaned: {filepath}")
    except Exception as e:
        print(f"Error processing {filepath}: {e}")

def main():
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.py') or file.endswith('.json'):
                filepath = os.path.join(root, file)
                process_file(filepath)

if __name__ == "__main__":
    main()
