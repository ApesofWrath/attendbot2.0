#!/usr/bin/env python3
"""
Setup script for Attendance Tracker
"""

import os
import sys
from app import app, db, User

def create_admin_user():
    """Create an admin user for initial setup"""
    with app.app_context():
        # Check if any admin users exist
        admin_exists = User.query.filter_by(is_admin=True).first()
        
        if admin_exists:
            print("Admin user already exists.")
            return
        
        print("Creating initial admin user...")
        slack_user_id = input("Enter Slack User ID for admin: ").strip()
        username = input("Enter username for admin: ").strip()
        email = input("Enter email for admin (optional): ").strip() or None
        
        admin_user = User(
            slack_user_id=slack_user_id,
            username=username,
            email=email,
            is_admin=True
        )
        
        db.session.add(admin_user)
        db.session.commit()
        
        print(f"Admin user created: {username} ({slack_user_id})")

def setup_database():
    """Initialize the database"""
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("Database initialized successfully!")

def main():
    """Main setup function"""
    print("Attendance Tracker Setup")
    print("=" * 30)
    
    # Check environment variables
    required_vars = ['SECRET_KEY', 'SLACK_BOT_TOKEN']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"Warning: Missing environment variables: {', '.join(missing_vars)}")
        print("Please set these in your .env file or environment")
        print()
    
    # Setup database
    setup_database()
    
    # Create admin user
    create_admin_user()
    
    print("\nSetup complete!")
    print("You can now run the application with: python app.py")

if __name__ == "__main__":
    main()
