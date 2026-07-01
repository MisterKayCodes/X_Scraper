import instaloader
import sys
import os

def generate_session_from_id(username: str):
    print(f"\n--- Foolproof Session Generator for: {username} ---")
    print("1. Open Chrome/Edge and go to Instagram.com")
    print("2. Press F12 to open Developer Tools")
    print("3. Go to the 'Application' tab (or 'Storage' tab)")
    print("4. On the left sidebar, expand 'Cookies' and click 'https://www.instagram.com'")
    print("5. Find the cookie named 'sessionid', double-click its Value, and copy it.\n")
    
    session_id = input("Paste your sessionid here: ").strip()
    
    if not session_id:
        print("[FAIL] No session ID provided.")
        sys.exit(1)

    # Build Instaloader and inject the session ID cookie directly
    L = instaloader.Instaloader()
    L.context._session.cookies.set("sessionid", session_id, domain=".instagram.com")
    L.context.username = username

    # Save to root folder (one level above /scripts/)
    root_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), f"ig_session_{username}")
    
    try:
        L.save_session_to_file(root_path)
        print(f"\n[SUCCESS] Session file saved to:\n  {root_path}")
        print("\nUpload that file to your VPS root folder and restart the bot!")
    except Exception as e:
        print(f"[FAIL] Could not save the file: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/generate_ig_session.py <your_instagram_username>")
        sys.exit(1)
        
    username = sys.argv[1]
    generate_session_from_id(username)
