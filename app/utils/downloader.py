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
    Download a file with progress bar and atomic writing.
    """
    if dest_path.exists():
        log(f"Skipping: {dest_path.name} (already exists)", quiet=quiet)
        return True

    temp_path = dest_path.with_suffix(dest_path.suffix + ".part")
    
    try:
        response = requests.get(url, headers=headers, stream=True, timeout=30, verify=False)
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
        
        with open(temp_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    pbar.update(len(chunk))
        
        pbar.close()
        temp_path.rename(dest_path)
        return True

    except Exception as e:
        if temp_path.exists():
            temp_path.unlink()
        log(f"Download failed for {url}: {e}", "ERROR", quiet=quiet)
        return False
