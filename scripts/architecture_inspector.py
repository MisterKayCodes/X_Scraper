import os, sys, ast, argparse

DEFAULT_FORBIDDEN_IMPORTS = {
    "core": ["aiogram", "sqlalchemy", "bot", "data", "services"],
    "bot": ["sqlalchemy", "data.models"], 
    "data": ["aiogram", "services", "bot"],
    "services": ["aiogram", "bot", "sqlalchemy"]
}

def check_file_integrity(file_path, folder_name, rules, max_lines=200):
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        if len(lines) > max_lines: return [f"File too long ({len(lines)} > {max_lines})"]
        try: tree = ast.parse("".join(lines))
        except Exception as e: return [f"Syntax Error: {e}"]
    
    errors = []
    forbidden = rules.get(folder_name, [])
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = []
            if isinstance(node, ast.ImportFrom):
                if node.module:
                    names.append(node.module)
            else:
                names.extend([n.name for n in node.names])
            
            for name in names:
                if name and any(name.startswith(f) for f in forbidden):
                    errors.append(f"Illegal import: {name}")
    return errors

def scan_organism(base_dir=".", max_lines=200):
    has_issues = False
    app_path = os.path.join(base_dir, "app")
    if not os.path.exists(app_path):
        print(f"[!] 'app/' directory not found in {base_dir}")
        return False

    for layer in DEFAULT_FORBIDDEN_IMPORTS.keys():
        path = os.path.join(app_path, layer)
        if not os.path.exists(path): continue
        for root, _, files in os.walk(path):
            for file in files:
                if file.endswith(".py") and file != "__init__.py":
                    errs = check_file_integrity(os.path.join(root, file), layer, DEFAULT_FORBIDDEN_IMPORTS, max_lines)
                    # Also check for 'app.' prefixed versions of forbidden imports
                    with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                        file_content = f.read()
                        for forbidden in DEFAULT_FORBIDDEN_IMPORTS[layer]:
                            if f"from app.{forbidden}" in file_content or f"import app.{forbidden}" in file_content:
                                errs.append(f"Illegal import: app.{forbidden}")
                    
                    for e in errs: 
                        print(f"[!] {os.path.join(root, file)}: {e}")
                        has_issues = True
    return not has_issues

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", default=".", help="Base directory to scan")
    args = parser.parse_args()
    
    if not scan_organism(args.dir):
        sys.exit(1)
    else:
        print("[OK] Architecture inspection passed.")
