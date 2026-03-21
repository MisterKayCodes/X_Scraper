import os
import re
from typing import List
from typing import List

TREE_FILE = "tree_structure.txt"
INDENT_SPACES = 4  # Number of spaces per level

def sanitize_name(name: str) -> str:
    """Sanitize folder/file names for Windows/Linux."""
    invalid_chars = '<>:"/\\|?*'
    for ch in invalid_chars:
        name = name.replace(ch, '_')
    return name.rstrip(" .")

def parse_tree(tree_text: str):
    """
    Parse the tree text and return a list of tuples:
    (full_path, is_dir, comment)
    """
    parsed_items = []
    path_stack: List[str] = []

    lines = tree_text.splitlines()

    for idx, line in enumerate(lines):
        # Skip empty lines
        if not line.strip():
            continue

        # Remove tree symbols
        line_clean = line.replace('│', ' ').replace('├', ' ').replace('└', ' ').replace('─', ' ')

        # Count indentation based on leading spaces
        stripped = line_clean.lstrip(' ')
        depth = (len(line_clean) - len(stripped)) // INDENT_SPACES

        # Skip completely empty lines
        if not stripped:
            continue

        # Extract comment if exists
        if '#' in stripped:
            parts = stripped.split('#', 1)
            clean_name = parts[0].strip()
            comment = parts[1].strip()
        else:
            clean_name, comment = stripped, ''

        # Sanitize folder/file name
        name = sanitize_name(clean_name.rstrip('/'))
        if not name:
            continue

        # Determine if it is a folder
        is_dir = False
        if clean_name.endswith('/'):
            is_dir = True
        elif idx + 1 < len(lines):
            # Check next line indentation to see if this is a folder
            next_line = lines[idx + 1].replace('│', ' ').replace('├', ' ').replace('└', ' ').replace('─', ' ')
            next_stripped = next_line.lstrip(' ')
            if next_stripped and ((len(next_line) - len(next_stripped)) // INDENT_SPACES) > depth:
                is_dir = True
        else:
            # Last line without dot? Treat as folder
            if '.' not in name:
                is_dir = True

        # Adjust stack to current depth
        while len(path_stack) > depth:
            path_stack.pop()

        # Full path
        full_path = os.path.join(*path_stack, name) if path_stack else name
        parsed_items.append((full_path, is_dir, comment))

        # Push folder to stack
        if is_dir:
            path_stack.append(name)

    return parsed_items

def print_tree_preview(parsed_items):
    """Print tree preview."""
    for path, is_dir, comment in parsed_items:
        prefix = "[DIR ]" if is_dir else "[FILE]"
        print(f"{prefix} {path} {'# ' + comment if comment else ''}")

def create_tree(parsed_items, base_path='.'):
    """Create folders and files on disk."""
    for path, is_dir, comment in parsed_items:
        full_path = os.path.join(base_path, path)
        if is_dir:
            os.makedirs(full_path, exist_ok=True)
            print(f"[DIR ] Created: {full_path}/")
        else:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w', encoding='utf-8') as f:
                if comment:
                    f.write(f"# {comment}\n")
            print(f"[FILE] Created: {full_path} {'# ' + comment if comment else ''}")

if __name__ == "__main__":
    if not os.path.exists(TREE_FILE):
        print(f"❌ Tree file '{TREE_FILE}' not found.")
        exit()

    with open(TREE_FILE, 'r', encoding='utf-8') as f:
        tree_text = f.read()

    parsed_items = parse_tree(tree_text)

    print("📂 Tree Preview:")
    print_tree_preview(parsed_items)

    proceed = input("\nDo you want to create this tree on disk? (y/n): ").strip().lower()
    if proceed == 'y':
        create_tree(parsed_items)
        print("\n✅ Tree creation complete!")
    else:
        print("\n⚠️ Tree creation aborted by user.")
