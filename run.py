import subprocess, sys

def run_inspector():
    print("[...] Running Architecture Inspector...")
    try:
        result = subprocess.run([sys.executable, "scripts/architecture_inspector.py"], capture_output=True, text=True)
        if result.returncode == 0:
            print("[OK] Architecture inspection passed.")
            return True
        else:
            print("[!] Architecture inspection failed:")
            print(result.stdout)
            print(result.stderr)
            return False
    except Exception as e:
        print(f"[!] Error running inspector: {e}")
        return False

if __name__ == "__main__":
    if run_inspector():
        try:
            from watchfiles import run_process
            print("[...] Starting bot with hot-reload...")
            run_process("./", target=f"{sys.executable} main.py")
        except ImportError:
            print("[...] Installing 'watchfiles' dependency...")
            subprocess.run([sys.executable, "-m", "pip", "install", "watchfiles"])
            from watchfiles import run_process
            print("[...] Starting bot with hot-reload...")
            run_process("./", target=f"{sys.executable} main.py")
    else:
        print("[!] Fix architectural issues before running.")
        sys.exit(1)
