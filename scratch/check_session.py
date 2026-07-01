import sqlite3
import os
import base64
import struct
import ipaddress

def get_session_string(file_path):
    try:
        conn = sqlite3.connect(file_path)
        cursor = conn.cursor()
        cursor.execute("SELECT dc_id, server_address, port, auth_key FROM sessions")
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return "No session data found in database."
            
        dc_id, ip, port, auth_key = row
        
        # Telethon StringSession format:
        # 1 byte for version (currently '1')
        # Packed Data:
        # dc_id (1 byte), ip (4/16 bytes), port (2 bytes), auth_key (256 bytes)
        
        version = '1'
        ip_obj = ipaddress.ip_address(ip)
        ip_bytes = ip_obj.packed
        
        # IP length is 4 for IPv4, 16 for IPv6
        # Telethon uses '>B4sH256s' for IPv4 or '>B16sH256s' for IPv6
        if ip_obj.version == 4:
            data = struct.pack('>B4sH256s', dc_id, ip_bytes, port, auth_key)
        else:
            data = struct.pack('>B16sH256s', dc_id, ip_bytes, port, auth_key)
            
        # IMPORTANT: Use standard b64encode, NOT urlsafe_b64encode
        # This is likely why it failed before.
        encoded = version + base64.b64encode(data).decode('ascii')
        return encoded
        
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == '__main__':
    session_path = r'c:\Users\USER\OneDrive\Desktop\5561982750162\5561982750162.session'
    result = get_session_string(session_path)
    print("\n--- FIXED Telethon Session String ---")
    print(result)
    print("-------------------------------------\n")
