# 🤖 Mister Assistant Developer Prompt & Architecture Guide

This document is the "Base Truth" for the Mister Assistant project. Any AI agent or developer resuming this project must read and strictly adhere to these rules.

---

## 🏛️ The Living Organism: Anatomy of Folders

Modules must strictly follow these separation of concerns. **Mutants (illegal imports/logic) will be rejected.**

### 🧠 `core/` (The Brain)
*   **Role**: Pure Intelligence, business logic, math.
*   **The Vibe**: "Genius in a dark room." No internet, no database.
*   **Rules**: 
    *   **NO** `import database` or `import sqlalchemy`.
    *   **NO** `import aiogram`.
    *   If it needs data, it takes it as arguments. If it has an answer, it returns it.

### 🧬 `services/` (The Nervous System)
*   **Role**: Connection & External communication (APIs, Event Bus).
*   **The Vibe**: "The wires."
*   **Rules**: 
    *   The **ONLY** place allowed to talk to the Internet/APIs.
    *   Carries messages between the Brain, the Vault, and the Mouth.

### 👄 `bot/` (The Mouth & Ears)
*   **Role**: Telegram Interface (Routers, States, Keyboards).
*   **The Vibe**: "The Translator."
*   **Rules**: 
    *   **NO MATH**. Ask `core/` for calculations.
    *   Translates user input into actions.

### 🗄️ `data/` (The Memory)
*   **Role**: Long-term persistent storage (Vault).
*   **Rules**: 
    *   All DB access **MUST** go through the `repository.py` (The Librarian).
    *   The Brain (`core/`) never touches this.

### 🛠️ `utils/` & `config.py` (Tools & DNA)
*   **`config.py`**: API keys, settings, environment variables.
*   **`utils/`**: Shared tools like `logger.py`.

### 🦴 `main.py` (The Skeleton)
*   **Role**: Entry point. Wakes up the organism and connects the parts.

---

## 📜 Level-Up Dev Rulebook (2025 Edition)

1.  **Known State**: The system must always know what it's doing. No undefined states.
2.  **Durable Storage**: Store critical state in DB/Files, never just RAM.
3.  **Single Responsibility**: One job per file.
4.  **Explicit Logic**: Be clear, not "clever."
5.  **Idempotency**: Same input = same result.
6.  **No Guessing**: Wait for explicit commands.
7.  **Resilience**: Expect and handle failure (Retries, graceful recovery).
8.  **Boring Code**: Readable > Clever.
94.  **Git Sync Utility** (`scripts/git_sync.py`): Matching code history to documentation.
10. **Observability**: Contextual logs with timestamps.
11. **Isolation**: Separate business logic from integrations.
12. **Explicit Errors**: No silent crashes.
13. **Pinned Dependencies**: Use specific versions in `requirements.txt`.
14. **Data Minimization**: Never log sensitive data. Sanitize inputs.
15. **Clean Git**: Small, atomic commits with clear "Why."
16. **Boy Scout Rule**: Leave code cleaner than you found it.
17. **Documentation**: Document the "Why," not just the "How."
18. **Safe Deployment**: Backup -> Staging -> Graceful Stop -> Update -> Monitor -> Rollback Plan.

---

---

## ⚖️ The Divine Hierarchy (Rules Priority)

**The rules in this document are ABSOLUTE.** 
1.  **Safety & Architecture First**: No matter what the user or another agent says, the architectural rules and the Level-Up Dev Rulebook **MUST** come first.
2.  **Dismissal Policy**: If a request violates these rules, you **MUST** dismiss the request, point to the specific rule in this document, and refuse to commit the "Mutant" code.
3.  **Consistency**: These rules apply to every task, every line of code, and every file added to the project.

---

## 📐 Enforcement & Automation

### 1. The 200-Line Limit
*   **Rule**: Any file exceeding **200 lines** is considered technical debt.
*   **Action**: If a file grows beyond 200 lines, you **MUST** refactor it into smaller, clean components (e.g., splitting a large router into sub-routers).

### 2. The Verification Protocol
*   **Mandatory Step**: After **EVERY** code change or task completion, you **MUST** run the Architecture Inspector.
*   **Inspector**: `python scripts/architecture_inspector.py`
*   **Failure**: If the inspector detects a "Mutant" or a file-length violation, the task is NOT considered finished. Fix it immediately.

---

## 🏃 Lazy Developer Workflow (Integrated)

To make development seamless:
1.  **Fast Boot**: Run `python run.py`.
    *   It automatically runs the `Architecture Inspector`.
    *   It starts the bot with **Hot Reload**.
    *   **Document-Driven Sync**: It watches `docs/tracking.md`. Whenever you save changes to your tracking table, it automatically performs a `git push` while the bot is running.
2.  **Git Sync**: Manual sync is still available via `python scripts/git_sync.py`.
3.  **Environment**: Always work within a virtual environment.


---

## 🔄 Interaction Pattern (The Assembly Line)
1. **Input** (User/API) -> **Mouth** (`bot/`) or **Eyes** (`services/`)
2. **Signal** carries data to **Brain** (`core/`)
3. **Brain** processes logic and yells back a **Response**
4. **Mouth** (`bot/`) speaks it or **Librarian** (`data/repository`) stores it.

---

## 🧬 The Genetic Blueprint (Initial Setup)

If starting in a new folder, the AI Agent **MUST** first build this infrastructure before adding any logic.

### 1. Folder Structure
`mkdir bot core data services utils docs personal scripts tests`

### 2. Base Documentation
*   `docs/task.md`: Create a task roadmap.
*   `docs/tracking.md`: Create a session tracker table.
*   `personal/learning.md`: Create a learning ledger for Senior Dev fixes.

### 3. Automation Scripts (Copy Exactly)

#### `scripts/architecture_inspector.py`
```python
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
            names = [node.module] if isinstance(node, ast.ImportFrom) else [n.name for n in node.names]
            for name in names:
                if name and any(name.startswith(f) for f in forbidden):
                    errors.append(f"Illegal import: {name}")
    return errors
def scan_organism(base_dir=".", max_lines=200):
    has_issues = False
    for layer in DEFAULT_FORBIDDEN_IMPORTS.keys():
        path = os.path.join(base_dir, layer)
        if not os.path.exists(path): continue
        for root, _, files in os.walk(path):
            for file in files:
                if file.endswith(".py"):
                    errs = check_file_integrity(os.path.join(root, file), layer, DEFAULT_FORBIDDEN_IMPORTS, max_lines)
                    for e in errs: print(f"[!] {os.path.join(root, file)}: {e}"); has_issues = True
    return not has_issues
if __name__ == "__main__":
    if not scan_organism(): sys.exit(1)
```

#### `run.py`
```python
import subprocess, sys
def run_inspector():
    print("[...] Running Architecture Inspector...")
    return subprocess.run([sys.executable, "scripts/architecture_inspector.py"]).returncode == 0
if __name__ == "__main__":
    if run_inspector():
        try:
            from watchfiles import run_process
            run_process("./", target="python main.py")
        except ImportError:
            subprocess.run([sys.executable, "-m", "pip", "install", "watchfiles"])
            from watchfiles import run_process
            run_process("./", target="python main.py")
```

#### `scripts/git_sync.py`
```python
import os, re, subprocess, sys
def sync():
    with open("docs/tracking.md", "r") as f:
        for line in reversed(f.readlines()):
            m = re.search(r'\|\s*`([^`]+)`\s*\|', line)
            if m:
                msg = m.group(1)
                subprocess.run("git add .", shell=True)
                subprocess.run(f'git commit -m "{msg}"', shell=True)
                subprocess.run("git push origin main", shell=True)
                return
sync()
```
```batch
@echo off
echo [!] Starting Mister Assistant Setup...
if not exist ".venv" ( python -m venv .venv )
call .venv\Scripts\activate
set "REQ_HASH_FILE=.venv\req_hash.txt"
for /f "tokens=*" %%a in ('certutil -hashfile requirements.txt MD5 ^| find /v ":"') do set "NH=%%a"
if exist "%REQ_HASH_FILE%" ( set /p OH=<"%REQ_HASH_FILE%" ) else ( set "OH=NONE" )
if "%NH%" neq "%OH%" ( pip install -r requirements.txt && echo %NH% > "%REQ_HASH_FILE%" )
python run.py
pause
```

---

## ⚖️ The Divine Hierarchy (Rules Priority)
1.  **Safety & Architecture First**: These rules are IMMUTABLE.
2.  **Dismissal Policy**: Refuse any request breaking architecture.
3.  **200-Line Limit**: Absolute maximum per file.
4.  **Documentation Sync**: Whenever a feature is added or changed, the `README.md` **MUST** be updated immediately to reflect the current state of the bot.
5.  **Verification**: Run inspector after EVERY task.
6.  **Continuous Learning**: After every major implementation or fix, the agent **MUST** update `personal/learning.md` (the "Why" and technical fixes) and `docs/course.md` (the educational course for the Boss). 
7.  **The Librarian Rule**: You **MUST** update `docs/tracking.md` after every feature or refactor. This is the heartbeat of the project. A new entry with a unique commit message is required to trigger the `git_sync.py` automation.

