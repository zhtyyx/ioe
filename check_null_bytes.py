import os

def check_file(file_path):
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
            if b'\x00' in content:
                print(f"File {file_path} contains null bytes")
                return True
    except Exception as e:
        print(f"Error checking {file_path}: {e}")
    return False

def check_directory(directory):
    found_nulls = False
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.html') or file.endswith('.py'):
                file_path = os.path.join(root, file)
                if check_file(file_path):
                    found_nulls = True
    return found_nulls

if __name__ == "__main__":
    print("Checking for null bytes in template files...")
    check_directory('inventory') 