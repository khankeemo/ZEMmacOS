#!/usr/bin/env python3
"""
Migrate SQLite data to Vercel Postgres
Run: python migrate_to_vercel_postgres.py

This script copies ALL data from zemmacos_dev.db to Vercel Postgres
"""

import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Source: SQLite (your existing data)
SQLITE_PATH = os.path.join(os.path.dirname(__file__), "zemmacos_dev.db")
SOURCE_URL = f"sqlite:///{SQLITE_PATH}"

# Target: Vercel Postgres (from environment)
TARGET_URL = os.getenv("DATABASE_URL")
if not TARGET_URL:
    print("❌ DATABASE_URL not found in .env")
    print("Please set DATABASE_URL to your Vercel Postgres connection string")
    sys.exit(1)

print(f"📦 Source: {SQLITE_PATH}")
print(f"🎯 Target: {TARGET_URL[:50]}...")

# Create connections
source_engine = create_engine(SOURCE_URL)
target_engine = create_engine(TARGET_URL)

SourceSession = sessionmaker(bind=source_engine)
TargetSession = sessionmaker(bind=target_engine)

source_db = SourceSession()
target_db = TargetSession()


def migrate_table(table_name: str, columns: list):
    """Generic table migration function"""
    print(f"  📋 Migrating {table_name}...")
    
    # Get data from source
    result = source_db.execute(text(f"SELECT * FROM {table_name}"))
    rows = result.fetchall()
    
    if not rows:
        print(f"     ⚠️ No data in {table_name}")
        return 0
    
    # Clear target table first
    target_db.execute(text(f"DELETE FROM {table_name}"))
    
    # Insert each row
    for row in rows:
        placeholders = ", ".join([f":{col}" for col in columns])
        insert_sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
        
        row_dict = {}
        for i, col in enumerate(columns):
            value = row[i]
            # Handle datetime conversion
            if isinstance(value, datetime):
                value = value.isoformat()
            row_dict[col] = value
        
        target_db.execute(text(insert_sql), row_dict)
    
    target_db.commit()
    print(f"     ✅ Migrated {len(rows)} rows")
    return len(rows)


def main():
    print("\n" + "="*50)
    print("🔄 ZEM License Database Migration")
    print("="*50)
    
    # Check if source exists
    if not os.path.exists(SQLITE_PATH):
        print(f"❌ Source database not found: {SQLITE_PATH}")
        sys.exit(1)
    
    # Tables to migrate (in correct order for foreign keys)
    tables = [
        ("admins", ["id", "username", "password_hash", "is_active", "created_at", "last_login"]),
        ("licenses", ["id", "customer_name", "customer_email", "license_key", "plan", 
                      "status", "expiry_date", "max_devices", "notes", "created_at", "updated_at"]),
        ("activations", ["id", "license_id", "hardware_id", "activated_at", "last_seen", 
                         "device_name", "ip_address"]),
        ("trials", ["id", "hardware_id", "started_at", "expiry_date", "status"]),
        ("audit_logs", ["id", "event_type", "message", "timestamp", "ip_address", 
                        "license_key", "hardware_id"]),
    ]
    
    total = 0
    for table_name, columns in tables:
        try:
            count = migrate_table(table_name, columns)
            total += count
        except Exception as e:
            print(f"     ❌ Error: {e}")
    
    print("\n" + "="*50)
    print(f"✅ Migration Complete! Total rows migrated: {total}")
    print("="*50)
    print("\n📌 Next steps:")
    print("1. Update your .env file with DATABASE_URL")
    print("2. Set USE_SQLITE_DEV=0")
    print("3. Restart your API")
    
    source_db.close()
    target_db.close()


if __name__ == "__main__":
    main()