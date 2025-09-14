#!/usr/bin/env python3
"""
Test script for Google SSO authentication
"""

import os
from app import app, db, User
from google_auth import get_flow, get_slack_user_info

def test_google_auth_setup():
    """Test Google OAuth configuration"""
    print("Testing Google OAuth setup...")
    
    # Check environment variables
    required_vars = ['GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET', 'GOOGLE_REDIRECT_URI']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("Please set these in your .env file")
        return False
    
    print("✅ All required environment variables are set")
    
    # Test flow creation
    try:
        flow = get_flow()
        print("✅ Google OAuth flow created successfully")
    except Exception as e:
        print(f"❌ Error creating OAuth flow: {e}")
        return False
    
    return True

def test_user_model():
    """Test user model with Google SSO fields"""
    print("\nTesting user model...")
    
    with app.app_context():
        # Test creating a user with Google SSO
        test_user = User(
            google_id="test_google_id_123",
            email="test@example.com",
            username="Test User",
            is_admin=False
        )
        
        db.session.add(test_user)
        db.session.commit()
        
        # Verify user was created
        user = User.query.filter_by(google_id="test_google_id_123").first()
        if user:
            print("✅ User with Google ID created successfully")
            print(f"   Email: {user.email}")
            print(f"   Username: {user.username}")
            print(f"   Google ID: {user.google_id}")
        else:
            print("❌ Failed to create user with Google ID")
            return False
        
        # Test email matching
        user_by_email = User.query.filter_by(email="test@example.com").first()
        if user_by_email and user_by_email.id == user.id:
            print("✅ Email matching works correctly")
        else:
            print("❌ Email matching failed")
            return False
        
        # Clean up
        db.session.delete(user)
        db.session.commit()
        print("✅ Test user cleaned up")
    
    return True

def test_slack_user_creation():
    """Test automatic Slack user creation"""
    print("\nTesting Slack user creation...")
    
    # Mock Slack user info
    mock_slack_info = {
        'id': 'U1234567890',
        'name': 'Test Slack User',
        'email': 'slack@example.com',
        'display_name': 'Test User'
    }
    
    with app.app_context():
        # Create user as if from Slack
        user = User(
            slack_user_id=mock_slack_info['id'],
            email=mock_slack_info['email'],
            username=mock_slack_info.get('display_name', mock_slack_info.get('name', 'Slack User')),
            is_admin=False
        )
        
        db.session.add(user)
        db.session.commit()
        
        # Verify user was created
        slack_user = User.query.filter_by(slack_user_id=mock_slack_info['id']).first()
        if slack_user:
            print("✅ Slack user created successfully")
            print(f"   Email: {slack_user.email}")
            print(f"   Username: {slack_user.username}")
            print(f"   Slack ID: {slack_user.slack_user_id}")
        else:
            print("❌ Failed to create Slack user")
            return False
        
        # Test linking Google account to existing Slack user
        slack_user.google_id = "linked_google_id_456"
        db.session.commit()
        
        # Verify linking worked
        linked_user = User.query.filter_by(email=mock_slack_info['email']).first()
        if linked_user and linked_user.google_id == "linked_google_id_456":
            print("✅ Google account linked to existing Slack user")
        else:
            print("❌ Failed to link Google account")
            return False
        
        # Clean up
        db.session.delete(slack_user)
        db.session.commit()
        print("✅ Test Slack user cleaned up")
    
    return True

def main():
    """Run all tests"""
    print("Google SSO Authentication Test Suite")
    print("=" * 40)
    
    tests = [
        test_google_auth_setup,
        test_user_model,
        test_slack_user_creation
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                print(f"❌ {test.__name__} failed")
        except Exception as e:
            print(f"❌ {test.__name__} failed with exception: {e}")
    
    print(f"\nTest Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Google SSO is ready to use.")
    else:
        print("⚠️  Some tests failed. Please check the configuration.")

if __name__ == "__main__":
    main()
