#!/usr/bin/env python3
"""
Update ZEMmacOS desktop app to use new API endpoint
Run: python update_desktop_app.py

This updates the desktop app's API configuration from Google Sheets to your FastAPI backend.
"""

import os
import re
import json

# Paths to update
DESKTOP_APP_PATHS = [
    "zem_license/api_client.py",
    "zem_license/api_config.py",
    "zem_license/license_manager.py",
    "zem_license/license_service.py",
]

NEW_API_URL = "https://zem-license-api.onrender.com"  # Change to your Render URL

def update_file(filepath):
    """Update API endpoints in a file"""
    full_path = os.path.join(os.path.dirname(__file__), filepath)
    if not os.path.exists(full_path):
        print(f"⚠️ Not found: {filepath}")
        return False
    
    with open(full_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    changes = []
    
    # Replace Google Sheets URLs
    patterns = [
        (r'https?://sheets\.googleapis\.com[^\s"\']*', f'"{NEW_API_URL}"'),
        (r'GOOGLE_SHEET[^\s]*', 'LICENSE_API_URL'),
        (r'spreadsheets\.google\.com[^\s"\']*', NEW_API_URL),
    ]
    
    for pattern, replacement in patterns:
        if re.search(pattern, content, re.IGNORECASE):
            content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
            changes.append(f"  - Replaced {pattern[:30]}...")
    
    # Replace API endpoint paths
    endpoint_mappings = {
        r'/api/license/validate': '/license/validate',
        r'/api/license/activate': '/license/activate',
        r'/api/license/reset': '/license/reset',
        r'/api/trial/start': '/trial/start',
        r'/api/trial/status': '/trial/status',
    }
    
    for old, new in endpoint_mappings.items():
        if old in content:
            content = content.replace(old, new)
            changes.append(f"  - Changed endpoint: {old} → {new}")
    
    if content != original:
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Updated: {filepath}")
        for change in changes:
            print(change)
        return True
    else:
        print(f"ℹ️ No changes needed: {filepath}")
        return False

def create_new_config():
    """Create a new API config file if needed"""
    config_path = os.path.join(os.path.dirname(__file__), "zem_license", "api_config_new.py")
    
    config_content = f'''"""
ZEM License API Configuration
Updated to use FastAPI backend on Render
"""

import os

# API Configuration
API_BASE_URL = os.getenv("ZEM_API_URL", "{NEW_API_URL}")

# Endpoints
ENDPOINTS = {{
    "validate": f"{{API_BASE_URL}}/license/validate",
    "activate": f"{{API_BASE_URL}}/license/activate",
    "reset": f"{{API_BASE_URL}}/license/reset",
    "info": f"{{API_BASE_URL}}/license/info",
    "trial_start": f"{{API_BASE_URL}}/trial/start",
    "trial_status": f"{{API_BASE_URL}}/trial/status",
}}

# Request timeout (seconds)
REQUEST_TIMEOUT = 30

# Retry settings
MAX_RETRIES = 3
RETRY_DELAY = 1
'''
    
    with open(config_path, 'w', encoding='utf-8') as f:
        f.write(config_content)
    print(f"\n✅ Created new config: {config_path}")
    print("   Review and rename to api_config.py if needed")

def main():
    print("="*50)
    print("🔄 Updating ZEMmacOS Desktop App")
    print("="*50)
    print(f"\n📡 New API URL: {NEW_API_URL}")
    print("\n⚠️ Make sure you have backed up your desktop app!\n")
    
    response = input("Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Cancelled.")
        return
    
    print("\n📁 Updating files...")
    updated_count = 0
    
    for filepath in DESKTOP_APP_PATHS:
        if update_file(filepath):
            updated_count += 1
    
    create_new_config()
    
    print("\n" + "="*50)
    print(f"✅ Updated {updated_count} files")
    print("="*50)
    print("\n📌 Next steps:")
    print(f"1. Update your .env file in desktop app with:")
    print(f"   ZEM_API_URL={NEW_API_URL}")
    print("2. Test the desktop app with new API")
    print("3. Remove old Google Sheets code after testing")

if __name__ == "__main__":
    main()