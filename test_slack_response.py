#!/usr/bin/env python3
"""
Test script to verify Slack interactive response handling
"""

import requests
import json

def test_interactive_endpoint():
    """Test the interactive endpoint with a mock payload"""
    
    # Mock payload for testing
    mock_payload = {
        'type': 'block_actions',
        'user': {'id': 'U12345TEST'},
        'trigger_id': 'test_trigger_123',
        'actions': [
            {
                'action_id': 'refresh_app_home',
                'value': None
            }
        ]
    }
    
    # Test data
    test_data = {
        'payload': json.dumps(mock_payload)
    }
    
    # Test the endpoint
    try:
        response = requests.post(
            'http://localhost:5001/slack/interactive',
            data=test_data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Body: {response.text}")
        
        if response.status_code == 200:
            print("✅ Interactive endpoint is working correctly")
        else:
            print("❌ Interactive endpoint returned an error")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the server. Make sure the app is running on localhost:5001")
    except Exception as e:
        print(f"❌ Error testing endpoint: {e}")

if __name__ == '__main__':
    print("Testing Slack interactive endpoint...")
    test_interactive_endpoint()
