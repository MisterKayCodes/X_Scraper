import os, re, subprocess, sys

def sync():
    tracking_path = "docs/tracking.md"
    if not os.path.exists(tracking_path):
        print(f"[!] {tracking_path} not found. Git sync aborted.")
        return

    with open(tracking_path, "r") as f:
        lines = f.readlines()
        if not lines:
            return
            
        for line in reversed(lines):
            # Look for commit messages in the tracking table (e.g., | Date | Task | `commit message` |)
            m = re.search(r'\|\s*`([^`]+)`\s*\|', line)
            if m:
                msg = m.group(1)
                print(f"[...] Syncing changes with commit: {msg}")
                subprocess.run("git add .", shell=True)
                subprocess.run(f'git commit -m "{msg}"', shell=True)
                subprocess.run("git push origin main", shell=True)
                return

if __name__ == "__main__":
    sync()
