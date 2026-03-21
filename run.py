import subprocess, sys, os

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

def kill_ghosts():
    print("[...] Searching for and terminating ghost processes...")
    try:
        current_dir = os.getcwd()
        if os.name == 'nt':
            # Safely target only python processes running main.py in THIS specific directory
            cmd = f"powershell -Command \"Get-WmiObject Win32_Process -Filter \\\"Name='python.exe'\\\" | Where-Object {{ $_.CommandLine -ne $null -and $_.CommandLine -match 'main.py' -and $_.CommandLine -match '{current_dir.replace('\\', '\\\\')}' }} | ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }}\""
            subprocess.run(cmd, shell=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        else:
            # Use absolute path to ensure we ONLY kill this specific bot's ghosts
            # We escape the current_dir to be safe in pkill regex
            safe_dir = current_dir.replace("/", "\\/").replace(".", "\\.")
            cmd = f'pkill -f "python.*{safe_dir}.*main.py"' 
            subprocess.run(cmd, shell=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        print("[OK] Ghost processes cleared.")
    except Exception as e:
        print(f"[!] Failed to kill ghosts: {e}")


if __name__ == "__main__":
    if run_inspector():
        kill_ghosts()
        try:
            from watchfiles import run_process, DefaultFilter
            
            class IgnoreDataFilter(DefaultFilter):
                def __call__(self, change, path):
                    p = str(path).lower()
                    # Rule: Strictly ignore database files, data folder, and downloads folder
                    patterns = ["app/data", "app\\data", "downloads", "downloads\\", ".db", ".db-wal", ".db-shm", ".part"]
                    if any(pattern in p for pattern in patterns):
                        return False
                    return super().__call__(change, path)

            print("[...] Starting bot with hot-reload (Ignoring DB/Data)...")
            run_process("./", target=f"{sys.executable} main.py", watch_filter=IgnoreDataFilter())
        except ImportError:
            print("[...] Installing 'watchfiles' dependency...")
            subprocess.run([sys.executable, "-m", "pip", "install", "watchfiles"])
            from watchfiles import run_process, DefaultFilter
            
            class IgnoreDataFilter(DefaultFilter):
                def __call__(self, change, path):
                    path_str = str(path).replace("\\", "/").lower()
                    if any(pattern in path_str for pattern in ["app/data", "scraped_media.db", "downloads", ".part"]):
                        return False
                    return super().__call__(change, path)

            print("[...] Starting bot with hot-reload (Ignoring DB updates)...")
            run_process("./", target=f"{sys.executable} main.py", watch_filter=IgnoreDataFilter())
    else:
        print("[!] Fix architectural issues before running.")
        sys.exit(1)
