#!/usr/bin/env python3
"""
Remove Google Sheets related files from ZEM_API project
Run: python remove_google_sheets.py

This safely deletes files that are no longer needed.
"""

import os
import shutil

# Files to delete (Google Sheets related)
FILES_TO_DELETE = [
    "services/google_sheets_service.py",
    "services/legacy_google_sheets.py",
]

# Directories to check for any other Google Sheets references
DIRECTORIES_TO_CHECK = [
    "services/",
    "routes/",
]

def delete_file(filepath):
    """Delete a file safely"""
    full_path = os.path.join(os.path.dirname(__file__), filepath)
    if os.path.exists(full_path):
        os.remove(full_path)
        print(f"✅ Deleted: {filepath}")
        return True
    else:
        print(f"⚠️ Not found: {filepath}")
        return False

def search_for_google_references():
    """Search for any remaining Google Sheets references in code"""
    print("\n🔍 Searching for Google Sheets references in code...")
    
    found = []
    extensions = ['.py', '.env', '.example', '.txt']
    
    for directory in DIRECTORIES_TO_CHECK:
        dir_path = os.path.join(os.path.dirname(__file__), directory)
        if not os.path.exists(dir_path):
            continue
            
        for root, dirs, files in os.walk(dir_path):
            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if 'google' in content.lower() or 'sheets' in content.lower():
                                rel_path = os.path.relpath(file_path, os.path.dirname(__file__))
                                found.append(rel_path)
                                print(f"  📄 Found in: {rel_path}")
                    except:
                        pass
    
    return found

def main():
    print("="*50)
    print("🗑️ Google Sheets Cleanup for ZEM_API")
    print("="*50)
    print("\n⚠️ This will delete Google Sheets related files.")
    print("Make sure you have backed up your data!\n")
    
    response = input("Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Cancelled.")
        return
    
    # Delete specified files
    print("\n📁 Deleting files...")
    for filepath in FILES_TO_DELETE:
        delete_file(filepath)
    
    # Search for references
    references = search_for_google_references()
    
    if references:
        print("\n⚠️ Found Google Sheets references in these files:")
        for ref in references:
            print(f"   - {ref}")
        print("\n📌 You may need to manually remove these references.")
    else:
        print("\n✅ No Google Sheets references found in code.")
    
    print("\n" + "="*50)
    print("✅ Cleanup complete!")
    print("="*50)
    print("\n📌 Next steps:")
    print("1. Update your .env file (remove GOOGLE_* variables)")
    print("2. Test your API to ensure everything works")

if __name__ == "__main__":
    main()