#!/usr/bin/env python3
"""
Comprehensive test suite for Attendance Tracker
Tests all major functionality including user management, meeting operations, and reporting
"""

import os
import sys
import json
from datetime import datetime, timedelta
from app import app, db, User, MeetingHour, ReportingPeriod, AttendanceLog, Excuse, ExcuseRequest

class TestAttendanceTracker:
    def __init__(self):
        self.app = app
        self.client = app.test_client()
        self.test_data = {}
        
    def setup_test_data(self):
        """Create test data for all tests"""
        with self.app.app_context():
            # Use unique identifiers to avoid conflicts
            timestamp = str(int(datetime.utcnow().timestamp()))
            
            # Create test admin user
            admin = User(
                slack_user_id=f"U{timestamp}001",
                username=f"Test Admin {timestamp}",
                email=f"admin{timestamp}@test.com",
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()
            self.test_data['admin'] = admin
            self.test_data['admin_id'] = admin.id
            
            # Create test regular users
            user1 = User(
                slack_user_id=f"U{timestamp}002",
                username=f"Test User 1 {timestamp}",
                email=f"user1{timestamp}@test.com",
                is_admin=False
            )
            user2 = User(
                slack_user_id=f"U{timestamp}003",
                username=f"Test User 2 {timestamp}", 
                email=f"user2{timestamp}@test.com",
                is_admin=False
            )
            db.session.add_all([user1, user2])
            db.session.commit()
            self.test_data['user1'] = user1
            self.test_data['user1_id'] = user1.id
            self.test_data['user2'] = user2
            self.test_data['user2_id'] = user2.id
            
            # Create test reporting period
            period = ReportingPeriod(
                name=f"Test Period {timestamp}",
                start_date=datetime.utcnow() - timedelta(days=30),
                end_date=datetime.utcnow() + timedelta(days=30),
                created_by=admin.id
            )
            db.session.add(period)
            db.session.commit()
            self.test_data['period'] = period
            self.test_data['period_id'] = period.id
            
            # Create test meetings
            meeting1 = MeetingHour(
                start_time=datetime.utcnow() - timedelta(hours=2),
                end_time=datetime.utcnow() - timedelta(hours=1),
                description=f"Test Regular Meeting {timestamp}",
                meeting_type="regular",
                created_by=admin.id
            )
            meeting2 = MeetingHour(
                start_time=datetime.utcnow() - timedelta(hours=4),
                end_time=datetime.utcnow() - timedelta(hours=3),
                description=f"Test Outreach Event {timestamp}",
                meeting_type="outreach",
                created_by=admin.id
            )
            db.session.add_all([meeting1, meeting2])
            db.session.commit()
            self.test_data['meeting1'] = meeting1
            self.test_data['meeting1_id'] = meeting1.id
            self.test_data['meeting2'] = meeting2
            self.test_data['meeting2_id'] = meeting2.id
            
            # Create test attendance logs
            attendance1 = AttendanceLog(
                user_id=user1.id,
                meeting_hour_id=meeting1.id,
                notes="Test attendance 1"
            )
            attendance2 = AttendanceLog(
                user_id=user2.id,
                meeting_hour_id=meeting1.id,
                notes="Test attendance 2"
            )
            attendance3 = AttendanceLog(
                user_id=user1.id,
                meeting_hour_id=meeting2.id,
                notes="Test outreach attendance"
            )
            db.session.add_all([attendance1, attendance2, attendance3])
            db.session.commit()
            self.test_data['attendance1'] = attendance1
            self.test_data['attendance2'] = attendance2
            self.test_data['attendance3'] = attendance3
            
            # Create test excuse
            excuse = Excuse(
                user_id=user2.id,
                meeting_hour_id=meeting2.id,
                reporting_period_id=period.id,
                reason="Test excuse",
                created_by=admin.id
            )
            db.session.add(excuse)
            db.session.commit()
            self.test_data['excuse'] = excuse

    def cleanup_test_data(self):
        """Clean up all test data"""
        with self.app.app_context():
            # Delete in reverse order to avoid foreign key constraints
            for key in ['excuse', 'attendance1', 'attendance2', 'attendance3', 'meeting1', 'meeting2', 'period', 'user1', 'user2', 'admin']:
                if key in self.test_data:
                    try:
                        db.session.delete(self.test_data[key])
                    except:
                        pass
            db.session.commit()

    def test_user_combination(self):
        """Test user combination functionality"""
        print("Testing user combination...")
        
        with self.app.app_context():
            from app import combine_user_data
            
            # Refresh objects from database to avoid detached instance errors
            primary_user = User.query.get(self.test_data['user1_id'])
            secondary_user = User.query.get(self.test_data['user2_id'])
            
            # Add some data to secondary user
            original_slack_id = secondary_user.slack_user_id
            secondary_user.slack_user_id = f"U{int(datetime.utcnow().timestamp())}999"
            secondary_user.google_id = "google123"
            db.session.commit()
            
            # Test combination
            result = combine_user_data(primary_user, secondary_user)
            
            if result['error'] is None:
                print("✓ User combination successful")
                print(f"  - Details: {', '.join(result['details'])}")
                
                # Verify data was transferred
                updated_primary = User.query.get(primary_user.id)
                if updated_primary.slack_user_id == secondary_user.slack_user_id and updated_primary.google_id == "google123":
                    print("✓ User data transferred correctly")
                else:
                    print("✗ User data transfer failed")
                    
                # Verify secondary user was deleted
                if User.query.get(secondary_user.id) is None:
                    print("✓ Secondary user deleted")
                else:
                    print("✗ Secondary user not deleted")
            else:
                print(f"✗ User combination failed: {result['error']}")
                # Restore original data if combination failed
                secondary_user.slack_user_id = original_slack_id
                secondary_user.google_id = None
                db.session.commit()

    def test_user_editing(self):
        """Test user editing functionality"""
        print("Testing user editing...")
        
        with self.app.app_context():
            # Test editing user profile
            user = User.query.get(self.test_data['user1_id'])
            new_username = f"Updated Username {int(datetime.utcnow().timestamp())}"
            new_email = f"updated{int(datetime.utcnow().timestamp())}@test.com"
            
            user.username = new_username
            user.email = new_email
            db.session.commit()
            
            # Verify changes
            updated_user = User.query.get(user.id)
            if updated_user.username == new_username and updated_user.email == new_email:
                print("✓ User editing successful")
            else:
                print("✗ User editing failed")

    def test_individual_attendance_report(self):
        """Test individual user attendance report functionality"""
        print("Testing individual attendance report...")
        
        with self.app.app_context():
            from app import get_user_attendance_data
            
            user_id = self.test_data['user1_id']
            period_id = self.test_data['period_id']
            
            # Test getting attendance data
            attendance_data = get_user_attendance_data(user_id, period_id)
            
            if attendance_data:
                print("✓ Individual attendance report generated")
                print(f"  - Regular attendance: {attendance_data.get('regular_attendance_percentage', 0)}%")
                print(f"  - Outreach attendance: {attendance_data.get('outreach_attendance_percentage', 0)}%")
            else:
                print("✗ Individual attendance report failed")

    def test_meeting_detail_view(self):
        """Test meeting detail view functionality"""
        print("Testing meeting detail view...")
        
        with self.app.app_context():
            from app import get_meeting_attendance_detail
            
            meeting_id = self.test_data['meeting1_id']
            
            # Test getting meeting detail data
            meeting_data = get_meeting_attendance_detail(meeting_id)
            
            if meeting_data:
                print("✓ Meeting detail view generated")
                print(f"  - Attendance count: {meeting_data.get('attendance_count', 0)}")
                print(f"  - Total attended hours: {meeting_data.get('total_attended_hours', 0)}")
                
                # Test JSON serialization (this was a previous bug)
                try:
                    json.dumps(meeting_data)
                    print("✓ Meeting data is JSON serializable")
                except TypeError as e:
                    print(f"✗ Meeting data JSON serialization failed: {e}")
            else:
                print("✗ Meeting detail view failed")

    def test_meeting_deletion(self):
        """Test meeting deletion functionality"""
        print("Testing meeting deletion...")
        
        with self.app.app_context():
            from app import delete_meeting
            
            # Create a test meeting for deletion
            test_meeting = MeetingHour(
                start_time=datetime.utcnow() - timedelta(hours=1),
                end_time=datetime.utcnow(),
                description=f"Test Meeting for Deletion {int(datetime.utcnow().timestamp())}",
                created_by=self.test_data['admin_id']
            )
            db.session.add(test_meeting)
            db.session.commit()
            
            # Test deletion
            result = delete_meeting(self.test_data['period_id'], test_meeting.id)
            
            if result['success']:
                print("✓ Meeting deletion successful")
                
                # Verify meeting was deleted
                if MeetingHour.query.get(test_meeting.id) is None:
                    print("✓ Meeting removed from database")
                else:
                    print("✗ Meeting still exists in database")
            else:
                print(f"✗ Meeting deletion failed: {result['message']}")

    def test_separated_meetings_data(self):
        """Test separated meetings data functionality"""
        print("Testing separated meetings data...")
        
        with self.app.app_context():
            from app import get_separated_meetings_data_for_period
            
            period_id = self.test_data['period_id']
            
            # Test getting separated meetings data
            regular_meetings, outreach_meetings = get_separated_meetings_data_for_period(period_id)
            
            if regular_meetings is not None and outreach_meetings is not None:
                print("✓ Separated meetings data generated")
                print(f"  - Regular meetings: {len(regular_meetings)}")
                print(f"  - Outreach meetings: {len(outreach_meetings)}")
                
                # Test attendance percentage calculation
                for meeting_data in regular_meetings + outreach_meetings:
                    if 'attendance_percentage' in meeting_data and 'total_members_in_period' in meeting_data:
                        print(f"  - Meeting attendance: {meeting_data['attendance_percentage']}% of {meeting_data['total_members_in_period']} members")
                        break
            else:
                print("✗ Separated meetings data failed")

    def test_attendance_percentage_calculation(self):
        """Test the new attendance percentage calculation"""
        print("Testing attendance percentage calculation...")
        
        with self.app.app_context():
            from app import get_separated_meetings_data_for_period
            
            period_id = self.test_data['period_id']
            regular_meetings, outreach_meetings = get_separated_meetings_data_for_period(period_id)
            
            if regular_meetings:
                meeting_data = regular_meetings[0]
                attendance_count = meeting_data['attendance_count']
                total_members = meeting_data['total_members_in_period']
                attendance_percentage = meeting_data['attendance_percentage']
                
                # Verify calculation
                expected_percentage = round((attendance_count / total_members * 100) if total_members > 0 else 0, 1)
                
                if attendance_percentage == expected_percentage:
                    print("✓ Attendance percentage calculation correct")
                    print(f"  - {attendance_count} members attended out of {total_members} total members = {attendance_percentage}%")
                else:
                    print(f"✗ Attendance percentage calculation incorrect: expected {expected_percentage}%, got {attendance_percentage}%")
            else:
                print("✗ No meetings found for percentage calculation test")

    def test_api_endpoints(self):
        """Test key API endpoints"""
        print("Testing API endpoints...")
        
        with self.app.test_client() as client:
            # Test login (would need proper authentication in real test)
            print("✓ API client initialized")
            
            # Test that routes exist (without authentication)
            try:
                response = client.get('/admin/users')
                # Should redirect to login, not 404
                if response.status_code in [302, 401]:
                    print("✓ Admin users route exists")
                else:
                    print(f"✗ Admin users route unexpected status: {response.status_code}")
            except Exception as e:
                print(f"✗ Admin users route test failed: {e}")

    def run_all_tests(self):
        """Run all tests"""
        print("Attendance Tracker Comprehensive Test Suite")
        print("=" * 50)
        
        try:
            self.setup_test_data()
            print("✓ Test data setup complete")
            
            self.test_user_combination()
            self.test_user_editing()
            self.test_individual_attendance_report()
            self.test_meeting_detail_view()
            self.test_meeting_deletion()
            self.test_separated_meetings_data()
            self.test_attendance_percentage_calculation()
            self.test_api_endpoints()
            
        except Exception as e:
            print(f"✗ Test suite error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.cleanup_test_data()
            print("✓ Test cleanup complete")
        
        print("\nTest suite completed!")

def main():
    """Run the test suite"""
    tester = TestAttendanceTracker()
    tester.run_all_tests()

if __name__ == "__main__":
    main()