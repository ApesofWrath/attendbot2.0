#!/usr/bin/env python3
"""
Run script for Attendance Tracker
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Check required environment variables
required_vars = ['SECRET_KEY']
missing_vars = [var for var in required_vars if not os.environ.get(var)]

if missing_vars:
    print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
    print("Please create a .env file with the required variables.")
    print("See env.example for reference.")
    sys.exit(1)

# Import and run the app
from app import app, db

if __name__ == '__main__':
    with app.app_context():
        # Create tables if they don't exist
        db.create_all()
        print("Database initialized")
    
    print("Starting Attendance Tracker...")
    print("Web interface: http://localhost:5001")
    print("Press Ctrl+C to stop")
    
    app.run(debug=True, host='0.0.0.0', port=5001)
