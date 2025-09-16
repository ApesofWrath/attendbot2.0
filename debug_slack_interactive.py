#!/usr/bin/env python3
"""
Debug script for Slack interactive components
"""

import os
import sys
import json
from datetime import datetime, timedelta

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User, MeetingHour, AttendanceLog
from slack_bot import AttendanceSlackBot

def test_slack_interactive():
    """Test the Slack interactive functionality"""
    
    print("🔍 Testing Slack Interactive Components\n")
    
    with app.app_context():
        # Initialize the bot
        bot = AttendanceSlackBot()
        
        # Create a test user
        test_user = User.query.filter_by(slack_user_id='U12345TEST').first()
        if not test_user:
            test_user = User(
                slack_user_id='U12345TEST',
                email='test@example.com',
                username='TestUser',
                is_admin=False
            )
            db.session.add(test_user)
            db.session.commit()
        
        # Create a test meeting
        now = datetime.now()
        test_meeting = MeetingHour(
            start_time=now - timedelta(days=1, hours=2),
            end_time=now - timedelta(days=1),
            description='Test Meeting for Interactive Debug',
            meeting_type='regular',
            created_by=test_user.id
        )
        db.session.add(test_meeting)
        db.session.commit()
        
        print(f"✅ Created test user: {test_user.username} (ID: {test_user.id})")
        print(f"✅ Created test meeting: {test_meeting.description} (ID: {test_meeting.id})")
        
        # Test 1: Test App Home creation
        print("\n1. Testing App Home creation...")
        try:
            blocks = bot._create_app_home_blocks(test_user)
            print(f"✅ App Home blocks created: {len(blocks)} blocks")
            
            # Check if we have the right buttons
            log_buttons = 0
            edit_buttons = 0
            for block in blocks:
                if block.get('type') == 'section' and 'accessory' in block:
                    action_id = block['accessory'].get('action_id', '')
                    if action_id.startswith('log_attendance_'):
                        log_buttons += 1
                    elif action_id.startswith('edit_attendance_'):
                        edit_buttons += 1
            
            print(f"   - Log attendance buttons: {log_buttons}")
            print(f"   - Edit attendance buttons: {edit_buttons}")
            
        except Exception as e:
            print(f"❌ Error creating App Home: {e}")
            return False
        
        # Test 2: Test modal opening (without actually opening)
        print("\n2. Testing modal creation...")
        try:
            # Test log attendance modal
            modal = bot.open_log_attendance_modal(test_user.slack_user_id, test_meeting.id, "test_trigger_123")
            if modal:
                print("✅ Log attendance modal created successfully")
            else:
                print("❌ Log attendance modal creation failed")
            
        except Exception as e:
            print(f"❌ Error creating modal: {e}")
            import traceback
            traceback.print_exc()
        
        # Test 3: Test block actions payload parsing
        print("\n3. Testing block actions payload...")
        try:
            # Create a mock payload
            mock_payload = {
                'type': 'block_actions',
                'user': {'id': test_user.slack_user_id},
                'trigger_id': 'test_trigger_123',
                'actions': [
                    {
                        'action_id': f'log_attendance_{test_meeting.id}',
                        'value': None
                    }
                ]
            }
            
            print(f"Mock payload: {json.dumps(mock_payload, indent=2)}")
            
            # Test the handler (without actually calling Slack API)
            from slack_routes import handle_block_actions
            print("✅ Block actions handler imported successfully")
            
        except Exception as e:
            print(f"❌ Error testing block actions: {e}")
            import traceback
            traceback.print_exc()
        
        # Test 4: Check Slack client configuration
        print("\n4. Testing Slack client configuration...")
        try:
            print(f"Slack client token configured: {'Yes' if bot.client.token else 'No'}")
            print(f"Token starts with: {bot.client.token[:10] if bot.client.token else 'None'}...")
            
        except Exception as e:
            print(f"❌ Error checking Slack client: {e}")
        
        print("\n🔧 Debugging Tips:")
        print("1. Check that your Slack app has interactivity enabled")
        print("2. Verify the Request URL is set to: https://your-domain.com/slack/interactive")
        print("3. Make sure the bot has the required OAuth scopes")
        print("4. Check the application logs when clicking buttons")
        print("5. Verify the trigger_id is being passed correctly")
        
        # Cleanup
        print("\n5. Cleaning up test data...")
        try:
            MeetingHour.query.filter_by(description='Test Meeting for Interactive Debug').delete()
            db.session.commit()
            print("✅ Test data cleaned up")
        except Exception as e:
            print(f"⚠️  Warning: Could not clean up test data: {e}")
        
        return True

def main():
    """Main debug function"""
    print("Starting Slack interactive components debug...\n")
    
    try:
        success = test_slack_interactive()
        
        if success:
            print("\n✅ Debug test completed!")
            print("\nIf buttons still show exclamation marks:")
            print("1. Check your Slack app's interactivity settings")
            print("2. Verify the Request URL is correct")
            print("3. Check the application logs for errors")
            print("4. Make sure the bot token has the right permissions")
        else:
            print("\n❌ Debug test failed. Check the errors above.")
            return 1
            
    except Exception as e:
        print(f"\n💥 Unexpected error during debugging: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    exit(main())
