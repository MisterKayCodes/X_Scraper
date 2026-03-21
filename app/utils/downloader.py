import requests
from pathlib import Path
from tqdm import tqdm
import sys

def log(msg, level="INFO", quiet=False):
    if not quiet:
        print(f"[{level}] {msg}")
        sys.stdout.flush()

def download_file(url: str, dest_path: Path, headers: dict, quiet=False):
    """
    Download a file with progress bar and atomic writing (128KB buffer).
    """
    if dest_path.exists():
        log(f"Skipping: {dest_path.name} (already exists)", quiet=quiet)
        return True

    temp_path = dest_path.with_suffix(dest_path.suffix + ".part")
    
    # Rule 12: Handle errors explicitly
    try:
        # Rule 14: Security - Verify is TRUE, 15s timeout
        with requests.get(url, headers=headers, stream=True, timeout=15, verify=True) as response:
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            desc = dest_path.name[:25]
            pbar = tqdm(
                total=total_size, 
                unit='B', 
                unit_scale=True, 
                desc=f"Downloading {desc}", 
                disable=quiet,
                leave=False
            )
            
            # Rule 4 & 8: 128KB is the "Senior" sweet spot for speed/stability
            with open(temp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=131072):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))
            
            pbar.close()
            temp_path.rename(dest_path)
            return True

    except Exception as e:
        if temp_path.exists():
            temp_path.unlink()
        print(f"[🚨] Critical Download Failure: {e}")
        log(f"Download failed for {url}: {e}", "ERROR", quiet=quiet)
        return False
