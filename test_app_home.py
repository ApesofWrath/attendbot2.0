#!/usr/bin/env python3
"""
Test script for Slack App Home functionality
"""

import os
import sys
from datetime import datetime, timedelta

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User, MeetingHour, AttendanceLog
from slack_bot import AttendanceSlackBot

def test_app_home_functionality():
    """Test the App Home functionality"""
    
    print("🧪 Testing Slack App Home Functionality\n")
    
    with app.app_context():
        # Initialize the bot
        bot = AttendanceSlackBot()
        
        # Test 1: Create test data
        print("1. Creating test data...")
        
        # Create a test user
        test_user = User.query.filter_by(email='test@example.com').first()
        if not test_user:
            test_user = User(
                slack_user_id='U12345TEST',
                email='test@example.com',
                username='TestUser',
                is_admin=False
            )
            db.session.add(test_user)
        
        # Create an admin user
        admin_user = User.query.filter_by(email='admin@example.com').first()
        if not admin_user:
            admin_user = User(
                slack_user_id='U12345ADMIN',
                email='admin@example.com',
                username='AdminUser',
                is_admin=True
            )
            db.session.add(admin_user)
        
        # Create some test meetings
        now = datetime.now()
        
        # Regular meeting with no attendance
        regular_meeting = MeetingHour(
            start_time=now - timedelta(days=1, hours=2),
            end_time=now - timedelta(days=1),
            description='Test Regular Meeting - No Attendance',
            meeting_type='regular',
            created_by=admin_user.id if admin_user.id else 1
        )
        db.session.add(regular_meeting)
        
        # Regular meeting with attendance
        regular_meeting_with_attendance = MeetingHour(
            start_time=now - timedelta(days=2, hours=2),
            end_time=now - timedelta(days=2),
            description='Test Regular Meeting - With Attendance',
            meeting_type='regular',
            created_by=admin_user.id if admin_user.id else 1
        )
        db.session.add(regular_meeting_with_attendance)
        
        # Outreach meeting
        outreach_meeting = MeetingHour(
            start_time=now - timedelta(days=3, hours=2),
            end_time=now - timedelta(days=3),
            description='Test Outreach Meeting',
            meeting_type='outreach',
            created_by=admin_user.id if admin_user.id else 1
        )
        db.session.add(outreach_meeting)
        
        db.session.commit()
        
        # Create attendance log for one meeting
        attendance_log = AttendanceLog(
            user_id=test_user.id,
            meeting_hour_id=regular_meeting_with_attendance.id,
            notes='Test attendance from App Home',
            is_partial=False,
            attendance_start_time=regular_meeting_with_attendance.start_time,
            attendance_end_time=regular_meeting_with_attendance.end_time
        )
        db.session.add(attendance_log)
        db.session.commit()
        
        print("✅ Test data created successfully")
        
        # Test 2: Test App Home Block creation for regular user
        print("\n2. Testing App Home blocks for regular user...")
        try:
            blocks = bot._create_app_home_blocks(test_user)
            assert isinstance(blocks, list), "Blocks should be a list"
            assert len(blocks) > 0, "Should have at least one block"
            
            # Check for header
            header_found = any(block.get('type') == 'header' for block in blocks)
            assert header_found, "Should have a header block"
            
            # Check for regular meetings section
            regular_section_found = any(
                block.get('type') == 'header' and 
                'Regular Meetings' in block.get('text', {}).get('text', '')
                for block in blocks
            )
            assert regular_section_found, "Should have Regular Meetings section"
            
            # Check for outreach section
            outreach_section_found = any(
                block.get('type') == 'header' and 
                'Outreach Meetings' in block.get('text', {}).get('text', '')
                for block in blocks
            )
            assert outreach_section_found, "Should have Outreach Meetings section"
            
            print("✅ App Home blocks created successfully for regular user")
            
        except Exception as e:
            print(f"❌ Error creating App Home blocks for regular user: {e}")
            return False
        
        # Test 3: Test App Home blocks for admin user
        print("\n3. Testing App Home blocks for admin user...")
        try:
            admin_blocks = bot._create_app_home_blocks(admin_user)
            assert isinstance(admin_blocks, list), "Admin blocks should be a list"
            
            # Check for admin controls
            admin_section_found = any(
                block.get('type') == 'header' and 
                'Admin Controls' in block.get('text', {}).get('text', '')
                for block in admin_blocks
            )
            assert admin_section_found, "Admin should have Admin Controls section"
            
            # Check for admin buttons
            admin_buttons_found = any(
                block.get('type') == 'actions' and
                any(element.get('action_id') == 'add_regular_meeting' 
                    for element in block.get('elements', []))
                for block in admin_blocks
            )
            assert admin_buttons_found, "Admin should have meeting creation buttons"
            
            print("✅ App Home blocks created successfully for admin user")
            
        except Exception as e:
            print(f"❌ Error creating App Home blocks for admin user: {e}")
            return False
        
        # Test 4: Test recent meetings retrieval
        print("\n4. Testing recent meetings retrieval...")
        try:
            regular_meetings = bot._get_recent_meetings('regular', test_user.id)
            outreach_meetings = bot._get_recent_meetings('outreach', test_user.id)
            
            assert isinstance(regular_meetings, list), "Regular meetings should be a list"
            assert isinstance(outreach_meetings, list), "Outreach meetings should be a list"
            assert len(regular_meetings) >= 2, "Should have at least 2 regular meetings"
            assert len(outreach_meetings) >= 1, "Should have at least 1 outreach meeting"
            
            # Check meeting data structure
            for meeting_data in regular_meetings:
                assert 'meeting' in meeting_data, "Should have meeting object"
                assert 'attendance_log' in meeting_data, "Should have attendance_log (can be None)"
            
            print(f"✅ Retrieved {len(regular_meetings)} regular meetings and {len(outreach_meetings)} outreach meetings")
            
        except Exception as e:
            print(f"❌ Error retrieving recent meetings: {e}")
            return False
        
        # Test 5: Test meeting blocks creation
        print("\n5. Testing meeting blocks creation...")
        try:
            # Test with meeting that has no attendance
            no_attendance_blocks = bot._create_meeting_blocks(regular_meeting, None, test_user.id)
            assert isinstance(no_attendance_blocks, list), "Meeting blocks should be a list"
            assert len(no_attendance_blocks) > 0, "Should have at least one meeting block"
            
            # Should have "Log Attendance" button
            log_button_found = any(
                'accessory' in block and 
                block['accessory'].get('action_id', '').startswith('log_attendance_')
                for block in no_attendance_blocks
            )
            assert log_button_found, "Meeting without attendance should have Log Attendance button"
            
            # Test with meeting that has attendance
            with_attendance_blocks = bot._create_meeting_blocks(regular_meeting_with_attendance, attendance_log, test_user.id)
            
            # Should have "Edit Attendance" button
            edit_button_found = any(
                'accessory' in block and 
                block['accessory'].get('action_id', '').startswith('edit_attendance_')
                for block in with_attendance_blocks
            )
            assert edit_button_found, "Meeting with attendance should have Edit Attendance button"
            
            print("✅ Meeting blocks created successfully")
            
        except Exception as e:
            print(f"❌ Error creating meeting blocks: {e}")
            return False
        
        # Test 6: Test error blocks
        print("\n6. Testing error blocks creation...")
        try:
            error_blocks = bot._create_error_blocks("Test error message")
            assert isinstance(error_blocks, list), "Error blocks should be a list"
            assert len(error_blocks) > 0, "Should have at least one error block"
            
            error_header_found = any(
                block.get('type') == 'header' and 
                'Error' in block.get('text', {}).get('text', '')
                for block in error_blocks
            )
            assert error_header_found, "Error blocks should have error header"
            
            print("✅ Error blocks created successfully")
            
        except Exception as e:
            print(f"❌ Error creating error blocks: {e}")
            return False
        
        print("\n🎉 All App Home functionality tests passed!")
        
        # Cleanup test data
        print("\n7. Cleaning up test data...")
        try:
            # Delete test attendance log
            AttendanceLog.query.filter_by(user_id=test_user.id).delete()
            
            # Delete test meetings
            MeetingHour.query.filter(MeetingHour.description.like('Test %')).delete()
            
            # Delete test users (optional - comment out if you want to keep them)
            # User.query.filter(User.email.in_(['test@example.com', 'admin@example.com'])).delete()
            
            db.session.commit()
            print("✅ Test data cleaned up")
            
        except Exception as e:
            print(f"⚠️  Warning: Could not clean up all test data: {e}")
        
        return True

def main():
    """Main test function"""
    print("Starting Slack App Home functionality tests...\n")
    
    try:
        success = test_app_home_functionality()
        
        if success:
            print("\n✅ All tests completed successfully!")
            print("\nNext steps:")
            print("1. Configure your Slack app with the required permissions")
            print("2. Enable App Home and subscribe to app_home_opened events")
            print("3. Update your Slack app's event subscription URL")
            print("4. Test the App Home functionality in your Slack workspace")
            return 0
        else:
            print("\n❌ Some tests failed. Please check the output above.")
            return 1
            
    except Exception as e:
        print(f"\n💥 Unexpected error during testing: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    exit(main())
