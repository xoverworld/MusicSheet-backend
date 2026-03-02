#!/usr/bin/env python3
"""
Test script to verify PostgreSQL setup
Run after configuring .env file
"""

import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("=" * 60)
print("🧪 POSTGRESQL SETUP VERIFICATION")
print("=" * 60)
print()

# Test 1: Check environment variables
print("1️⃣  Checking environment variables...")
try:
    from config import get_settings
    settings = get_settings()
    
    assert settings.database_url, "DATABASE_URL not set"
    assert settings.jwt_secret_key, "JWT_SECRET_KEY not set"
    
    print("   ✅ All environment variables configured")
    print(f"   📍 Database URL: {settings.database_url[:30]}...")
except Exception as e:
    print(f"   ❌ Error: {e}")
    print("   💡 Make sure to copy .env.example to .env and fill in values")
    sys.exit(1)

print()

# Test 2: Test database connection
print("2️⃣  Testing database connection...")
try:
    from db_models import engine, SessionLocal
    from sqlalchemy import text
    
    # Try to connect
    session = SessionLocal()
    result = session.execute(text("SELECT 1"))
    session.close()
    
    print(f"   ✅ Connected to PostgreSQL successfully")
    
    # Count users
    session = SessionLocal()
    result = session.execute(text("SELECT COUNT(*) FROM users"))
    count = result.scalar()
    session.close()
    
    print(f"   👥 Users in database: {count}")
except Exception as e:
    print(f"   ❌ Connection failed: {e}")
    print("   💡 Check that:")
    print("      - PostgreSQL is running")
    print("      - Database 'piano_transcription' exists")
    print("      - DATABASE_URL in .env is correct")
    print("      - Tables are created (run: python db_models.py)")
    sys.exit(1)

print()

# Test 3: Test password hashing
print("3️⃣  Testing password hashing...")
try:
    from auth import hash_password, verify_password
    
    test_password = "test_password_123"
    hashed = hash_password(test_password)
    
    assert verify_password(test_password, hashed), "Password verification failed"
    assert not verify_password("wrong_password", hashed), "Should reject wrong password"
    
    print("   ✅ Password hashing working correctly")
except Exception as e:
    print(f"   ❌ Error: {e}")
    sys.exit(1)

print()

# Test 4: Test JWT token creation
print("4️⃣  Testing JWT token creation...")
try:
    from auth import create_access_token, decode_token
    
    test_data = {"sub": "test-user-id"}
    token = create_access_token(test_data)
    decoded = decode_token(token)
    
    assert decoded["sub"] == "test-user-id", "Token data mismatch"
    print("   ✅ JWT token creation and verification working")
except Exception as e:
    print(f"   ❌ Error: {e}")
    sys.exit(1)

print()

# Test 5: Test database operations
print("5️⃣  Testing database operations...")
try:
    from database import database
    from db_models import SessionLocal
    import uuid
    
    session = SessionLocal()
    
    # Create test user
    test_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    test_password_hash = hash_password("test123456")
    
    print(f"   📧 Creating test user: {test_email}")
    user = database.create_user(session, test_email, test_password_hash)
    
    assert user is not None, "Failed to create user"
    print(f"   ✅ User created with ID: {user.id[:8]}...")
    
    # Verify user exists
    found_user = database.get_user_by_email(session, test_email)
    assert found_user is not None, "Failed to find user"
    print(f"   ✅ User found in database")
    
    # Clean up - delete test user
    session.delete(user)
    session.commit()
    session.close()
    print(f"   🗑️  Test user cleaned up")
    
except Exception as e:
    print(f"   ❌ Error: {e}")
    print("   💡 Make sure database tables are created (run: python db_models.py)")
    sys.exit(1)

print()

# Test 6: Test file storage
print("6️⃣  Testing file storage...")
try:
    import os
    from config import get_settings
    
    settings = get_settings()
    
    # Check if upload directory exists
    if os.path.exists(settings.upload_dir):
        print(f"   ✅ Upload directory exists: {settings.upload_dir}")
    else:
        os.makedirs(settings.upload_dir, exist_ok=True)
        print(f"   ✅ Upload directory created: {settings.upload_dir}")
    
    # Check subdirectories
    audio_dir = os.path.join(settings.upload_dir, "audio")
    sheets_dir = os.path.join(settings.upload_dir, "sheets")
    
    os.makedirs(audio_dir, exist_ok=True)
    os.makedirs(sheets_dir, exist_ok=True)
    
    print(f"   ✅ Audio directory: {audio_dir}")
    print(f"   ✅ Sheets directory: {sheets_dir}")
        
except Exception as e:
    print(f"   ⚠️  File storage setup issue: {e}")
    print("   💡 This is optional but needed for file uploads")

print()
print("=" * 60)
print("✅ SETUP VERIFICATION COMPLETE")
print("=" * 60)
print()
print("🎉 Your backend is ready to use!")
print()
print("Next steps:")
print("  1. Start the server: python main.py")
print("  2. Visit http://localhost:3001/docs for API documentation")
print("  3. Test registration: POST /auth/register")
print("  4. Test login: POST /auth/login")
print()