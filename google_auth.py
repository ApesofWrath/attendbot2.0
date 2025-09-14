"""
Google OAuth configuration and utilities
"""

import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import json
import urllib3

# OAuth 2.0 scopes
SCOPES = [
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'openid'
]

def get_flow():
    """Create and return a Google OAuth flow"""
    # Disable SSL warnings for local development
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    client_config = {
        "web": {
            "client_id": os.environ.get('GOOGLE_CLIENT_ID'),
            "client_secret": os.environ.get('GOOGLE_CLIENT_SECRET'),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [os.environ.get('GOOGLE_REDIRECT_URI', 'http://localhost:5001/auth/google/callback')]
        }
    }
    
    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=os.environ.get('GOOGLE_REDIRECT_URI', 'http://localhost:5001/auth/google/callback')
    )
    
    # Allow HTTP for local development by disabling HTTPS requirement
    if os.environ.get('FLASK_ENV') == 'development':
        # This is the key fix - disable HTTPS requirement for local development
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
        
        # Also set the redirect URI explicitly
        flow.redirect_uri = os.environ.get('GOOGLE_REDIRECT_URI', 'http://localhost:5001/auth/google/callback')
    
    return flow

def get_user_info(credentials):
    """Get user information from Google using credentials"""
    try:
        # Use People API instead of deprecated OAuth2 API
        service = build('people', 'v1', credentials=credentials)
        profile = service.people().get(
            resourceName='people/me',
            personFields='names,emailAddresses'
        ).execute()
        
        # Extract user info from the response
        names = profile.get('names', [])
        emails = profile.get('emailAddresses', [])
        
        user_info = {
            'id': profile.get('resourceName', '').split('/')[-1],
            'name': names[0]['displayName'] if names else '',
            'email': emails[0]['value'] if emails else ''
        }
        
        return user_info
    except Exception as e:
        print(f"Error getting user info: {e}")
        # Fallback to OAuth2 API if People API fails
        try:
            service = build('oauth2', 'v2', credentials=credentials)
            user_info = service.userinfo().get().execute()
            return user_info
        except Exception as e2:
            print(f"Fallback also failed: {e2}")
            return None

def get_slack_user_info(slack_user_id):
    """Get Slack user information including email"""
    try:
        from slack_sdk import WebClient
        client = WebClient(token=os.environ.get('SLACK_BOT_TOKEN'))
        
        response = client.users_info(user=slack_user_id)
        if response['ok']:
            user = response['user']
            profile = user.get('profile', {})
            return {
                'id': user['id'],
                'name': user.get('real_name', user.get('name', '')),
                'email': profile.get('email', ''),
                'display_name': profile.get('display_name', user.get('real_name', ''))
            }
    except Exception as e:
        print(f"Error getting Slack user info: {e}")
    
    return None
