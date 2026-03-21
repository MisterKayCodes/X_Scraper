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
        if os.name == 'nt':
            cmd = "powershell -Command \"Get-WmiObject Win32_Process -Filter \\\"Name='python.exe'\\\" | Where-Object { $_.CommandLine -ne $null -and $_.CommandLine -match 'main.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }\""
            subprocess.run(cmd, shell=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        else:
            cmd = 'pkill -f "python.*main.py"' 
            subprocess.run(cmd, shell=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        print("[OK] Ghost processes cleared.")
    except Exception as e:
        print(f"[!] Failed to kill ghosts: {e}")

if __name__ == "__main__":
    if run_inspector():
        kill_ghosts()
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
