#!/usr/bin/env python3
"""
Demo script for Attendance Tracker
Creates sample data and demonstrates the application features
"""

import os
import sys
from datetime import datetime, timedelta
from app import app, db, User, MeetingHour, ReportingPeriod, AttendanceLog, Excuse, ExcuseRequest

def create_demo_data():
    """Create demo data for testing"""
    with app.app_context():
        print("Creating demo data...")
        
        # Clear existing data
        db.drop_all()
        db.create_all()
        
        # Create admin user
        admin = User(
            slack_user_id="U1234567890",
            google_id="admin_google_id_123",
            username="Admin User",
            email="admin@example.com",
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()
        print("✓ Admin user created")
        
        # Create regular users
        users = []
        for i in range(5):
            user = User(
                slack_user_id=f"U{i+1:010d}",
                google_id=f"google_id_{i+1}",
                username=f"User {i+1}",
                email=f"user{i+1}@example.com",
                is_admin=False
            )
            users.append(user)
            db.session.add(user)
        db.session.commit()
        print("✓ Regular users created")
        
        # Create reporting period
        period = ReportingPeriod(
            name="Demo Season 2024",
            start_date=datetime.utcnow() - timedelta(days=30),
            end_date=datetime.utcnow() + timedelta(days=30),
            created_by=admin.id
        )
        db.session.add(period)
        db.session.commit()
        print("✓ Reporting period created")
        
        # Create regular meetings
        meetings = []
        for i in range(10):
            meeting = MeetingHour(
                start_time=datetime.utcnow() - timedelta(days=25-i*2, hours=14),
                end_time=datetime.utcnow() - timedelta(days=25-i*2, hours=16),
                description=f"Team Meeting {i+1}",
                meeting_type='regular',
                created_by=admin.id
            )
            meetings.append(meeting)
            db.session.add(meeting)
        
        # Create outreach events
        outreach_events = []
        for i in range(5):
            outreach = MeetingHour(
                start_time=datetime.utcnow() - timedelta(days=20-i*3, hours=10),
                end_time=datetime.utcnow() - timedelta(days=20-i*3, hours=8),
                description=f"Outreach Event {i+1}",
                meeting_type='outreach',
                created_by=admin.id
            )
            outreach_events.append(outreach)
            db.session.add(outreach)
        
        db.session.commit()
        print("✓ Regular meetings created")
        print("✓ Outreach events created")
        
        # Create attendance logs for regular meetings (some users attend more than others)
        for i, user in enumerate(users):
            # User 1 attends all meetings (100%)
            # User 2 attends 8/10 meetings (80%)
            # User 3 attends 6/10 meetings (60%)
            # User 4 attends 4/10 meetings (40%)
            # User 5 attends 2/10 meetings (20%)
            meetings_to_attend = min(10, 10 - i*2)
            
            for j in range(meetings_to_attend):
                # Add some partial attendance for variety
                is_partial = (i == 1 and j == 0) or (i == 2 and j == 1)  # User 2 and 3 have some partial attendance
                partial_hours = 1.5 if is_partial else None
                
                attendance = AttendanceLog(
                    user_id=user.id,
                    meeting_hour_id=meetings[j].id,
                    notes=f"Attended meeting {j+1}" + (" (partial)" if is_partial else ""),
                    is_partial=is_partial,
                    partial_hours=partial_hours
                )
                db.session.add(attendance)
        
        # Create attendance logs for outreach events
        for i, user in enumerate(users):
            # User 1 attends all outreach events (10h)
            # User 2 attends 4/5 outreach events (8h)
            # User 3 attends 3/5 outreach events (6h)
            # User 4 attends 2/5 outreach events (4h)
            # User 5 attends 1/5 outreach events (2h)
            outreach_to_attend = min(5, 5 - i)
            
            for j in range(outreach_to_attend):
                attendance = AttendanceLog(
                    user_id=user.id,
                    meeting_hour_id=outreach_events[j].id,
                    notes=f"Attended outreach {j+1}"
                )
                db.session.add(attendance)
        
        db.session.commit()
        print("✓ Regular meeting attendance logs created")
        print("✓ Outreach attendance logs created")
        
        # Create excuse requests (some pending, some approved)
        excuse_request1 = ExcuseRequest(
            user_id=users[1].id,
            meeting_hour_id=meetings[0].id,
            reason="Family emergency - need to attend funeral",
            status='pending'
        )
        excuse_request2 = ExcuseRequest(
            user_id=users[2].id,
            meeting_hour_id=meetings[1].id,
            reason="Medical appointment - annual checkup",
            status='approved',
            reviewed_by=admin.id,
            reviewed_at=datetime.utcnow(),
            admin_notes="Approved - medical appointments are valid excuses"
        )
        excuse_request3 = ExcuseRequest(
            user_id=users[3].id,
            meeting_hour_id=meetings[2].id,
            reason="Want to skip this meeting",
            status='denied',
            reviewed_by=admin.id,
            reviewed_at=datetime.utcnow(),
            admin_notes="Not a valid reason for missing a mandatory meeting"
        )
        db.session.add_all([excuse_request1, excuse_request2, excuse_request3])
        
        # Create some excuses
        excuse1 = Excuse(
            user_id=users[1].id,
            meeting_hour_id=meetings[0].id,
            reporting_period_id=period.id,
            reason="Family emergency",
            created_by=admin.id
        )
        excuse2 = Excuse(
            user_id=users[2].id,
            meeting_hour_id=meetings[1].id,
            reporting_period_id=period.id,
            reason="Medical appointment",
            created_by=admin.id,
            excuse_request_id=excuse_request2.id
        )
        db.session.add(excuse1)
        db.session.add(excuse2)
        db.session.commit()
        print("✓ Excuses created")
        
        print("\nDemo data created successfully!")
        print(f"Admin user ID: {admin.slack_user_id}")
        print(f"Regular user IDs: {[user.slack_user_id for user in users]}")
        print(f"Reporting period: {period.name}")
        print(f"Meetings created: {len(meetings)}")
        print(f"Attendance logs: {len(AttendanceLog.query.all())}")
        print(f"Excuses: {len(Excuse.query.all())}")

def show_attendance_summary():
    """Show attendance summary for all users"""
    with app.app_context():
        from app import get_user_attendance_data, get_attendance_report_data
        
        period = ReportingPeriod.query.first()
        if not period:
            print("No reporting period found")
            return
        
        print(f"\nAttendance Summary for {period.name}")
        print("=" * 50)
        
        report_data = get_attendance_report_data(period.id)
        
        for user_data in report_data:
            user = user_data['user']
            print(f"\n{user.username}:")
            
            # Regular meetings
            regular = user_data['regular_meetings']
            print(f"  Regular Meetings:")
            print(f"    Attendance: {regular['attendance_percentage']}%")
            print(f"    Attended: {regular['attended']}/{regular['total']}")
            print(f"    Excused: {regular['excused']}")
            print(f"    Team Requirement (60%): {'✓' if regular['meets_team_requirement'] else '✗'}")
            print(f"    Travel Requirement (75%): {'✓' if regular['meets_travel_requirement'] else '✗'}")
            
            # Outreach hours
            outreach = user_data['outreach_hours']
            print(f"  Outreach Hours:")
            print(f"    Attended: {outreach['attended_hours']}h/{outreach['total_hours']}h")
            print(f"    Excused: {outreach['excused_hours']}h")
            print(f"    Team Requirement (12h): {'✓' if outreach['meets_team_requirement'] else '✗'}")
            print(f"    Travel Requirement (18h): {'✓' if outreach['meets_travel_requirement'] else '✗'}")

def main():
    """Run the demo"""
    print("Attendance Tracker Demo")
    print("=" * 30)
    
    # Create demo data
    create_demo_data()
    
    # Show attendance summary
    show_attendance_summary()
    
    print("\nDemo completed!")
    print("You can now run the application with: ./venv/bin/python start.py")
    print("Login with Slack User ID: U1234567890 (Admin)")

if __name__ == "__main__":
    main()
