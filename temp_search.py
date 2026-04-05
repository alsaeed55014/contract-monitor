import sys

def search_file(filepath, query):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f, 1):
                if query.lower() in line.lower():
                    print(f"{i}: {line.strip()}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    search_file(sys.argv[1], sys.argv[2])
