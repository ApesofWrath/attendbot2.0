#!/usr/bin/env python3
"""
Startup script for Attendance Tracker with proper imports
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the app first
from app import app, db

# Then import and register Slack routes
from slack_routes import *

if __name__ == '__main__':
    with app.app_context():
        # Create tables if they don't exist
        db.create_all()
        print("Database initialized")
    
    print("Starting Attendance Tracker...")
    print("Web interface: http://localhost:5001")
    print("Press Ctrl+C to stop")
    
    app.run(debug=True, host='0.0.0.0', port=5001)
