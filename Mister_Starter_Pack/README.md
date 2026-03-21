# 🤖 Mister Assistant Starter Kit

Welcome to the **Mister Starter Kit**! This package is designed to help you build robust, modular, and automated Python projects (Bots, Scrapers, or APIs) following a strict and scalable architecture.

---

## Getting Started

### 1. Build Your Organism
Open `tree_structure.txt` and customize your project layout (or use the default Mister Assistant template). Then run:
```bash
python tree_generator.py
```
This will create your entire project directory structure and basic files instantly.

### 2. Initialize Environment
Run `setup.bat`. This will:
- Create a virtual environment (`venv`).
- Install all necessary dependencies from `requirements.txt`.

### 3. Launch & Develop
Double-click `run.bat`. This will:
- Start your project entry point (`main.py`).
- Enable **Hot Reload** (the bot restarts automatically when you save changes).
- Automatically run the **Architecture Inspector** to ensure your code stays clean.

---

## The Architecture (The "Mister Assistant" Way)

Your project is organized into layers to prevent "spaghetti code":

- **`app/bot/` (The Mouth)**: Handles the UI (Telegram, CLI). Strictly for interaction.
- **`app/core/` (The Brain)**: Pure logic only. No internet or DB imports allowed here.
- **`app/services/` (The Wires)**: The *only* place allowed to talk to the Internet/APIs.
- **`app/data/` (The Memory)**: Handles long-term storage and database access.
- **`app/utils/`**: Reusable helpers and loggers.

---

## Automated Enforcement

### The 200-Line Rule
Files over 200 lines are considered "debt". The inspector will yell at you to refactor into smaller components.

### No "Mutants"
The architecture protects your Brain (`core`) from getting "dirty" with UI or DB logic. The `architecture_inspector.py` automatically blocks illegal imports between layers.

### Auto Git-Sync
Whenever you update your session tracker in `docs/tracking.md`, the `git_sync.py` tool automatically performs a git push with your tracking message as the commit.

---

## AI Agent Rules (The Librarian Rule)

If an AI agent is working on this project, it **MUST** strictly adhere to these documentation and tracking rules:

### 1. The Librarian Rule (`docs/tracking.md`)
Every feature or refactor **MUST** be logged in `docs/tracking.md`. A new entry in the tracking table with a concise commit message is required to trigger the `git_sync.py` automation.

### 2. Continuous Learning (`personal/learning.md`)
After every major implementation or tricky fix, the agent **MUST** update `personal/learning.md` with the "Why" and technical details. This is the project's memory.

### 3. Task Roadmap (`docs/task.md`)
The `docs/task.md` must be updated to reflect the current roadmap and completed features.

### 4. Documentation Sync
Update this `README.md` immediately if any architectural changes or new core features are introduced.

---

## Requirements
- Python 3.10+
- `watchfiles` (installed automatically via `setup.bat`)
- `aiogram` (if building a Telegram bot)

Happy coding, Boss!
