#!/usr/bin/env python3
"""
Simple test script for Attendance Tracker
"""

import os
import sys
from datetime import datetime, timedelta
from app import app, db, User, MeetingHour, ReportingPeriod, AttendanceLog, Excuse

def test_database_operations():
    """Test basic database operations"""
    with app.app_context():
        print("Testing database operations...")
        
        # Create test admin user
        admin = User(
            slack_user_id="U1234567890",
            username="Test Admin",
            email="admin@test.com",
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()
        print("✓ Admin user created")
        
        # Create test regular user
        user = User(
            slack_user_id="U0987654321",
            username="Test User",
            email="user@test.com",
            is_admin=False
        )
        db.session.add(user)
        db.session.commit()
        print("✓ Regular user created")
        
        # Create test reporting period
        period = ReportingPeriod(
            name="Test Period",
            start_date=datetime.utcnow() - timedelta(days=30),
            end_date=datetime.utcnow() + timedelta(days=30),
            created_by=admin.id
        )
        db.session.add(period)
        db.session.commit()
        print("✓ Reporting period created")
        
        # Create test meeting
        meeting = MeetingHour(
            start_time=datetime.utcnow() - timedelta(hours=2),
            end_time=datetime.utcnow() - timedelta(hours=1),
            description="Test Meeting",
            created_by=admin.id
        )
        db.session.add(meeting)
        db.session.commit()
        print("✓ Meeting created")
        
        # Create test attendance log
        attendance = AttendanceLog(
            user_id=user.id,
            meeting_hour_id=meeting.id,
            notes="Test attendance"
        )
        db.session.add(attendance)
        db.session.commit()
        print("✓ Attendance log created")
        
        # Test attendance calculation
        from app import get_user_attendance_data
        attendance_data = get_user_attendance_data(user.id, period.id)
        
        if attendance_data:
            print(f"✓ Attendance calculation works: {attendance_data['attendance_percentage']}%")
        else:
            print("✗ Attendance calculation failed")
        
        # Clean up test data
        db.session.delete(attendance)
        db.session.delete(meeting)
        db.session.delete(period)
        db.session.delete(user)
        db.session.delete(admin)
        db.session.commit()
        print("✓ Test data cleaned up")

def test_slack_bot():
    """Test Slack bot functionality"""
    print("\nTesting Slack bot...")
    
    try:
        from slack_bot import AttendanceSlackBot
        bot = AttendanceSlackBot()
        print("✓ Slack bot initialized")
    except Exception as e:
        print(f"✗ Slack bot initialization failed: {e}")

def main():
    """Run all tests"""
    print("Attendance Tracker Test Suite")
    print("=" * 40)
    
    # Test database operations
    test_database_operations()
    
    # Test Slack bot
    test_slack_bot()
    
    print("\nTest suite completed!")

if __name__ == "__main__":
    main()
