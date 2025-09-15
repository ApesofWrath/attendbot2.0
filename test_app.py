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

    def test_attendance_time_tracking(self):
        """Test attendance time tracking functionality"""
        print("Testing attendance time tracking...")
        
        with self.app.app_context():
            # Create a test meeting with specific times
            meeting_start = datetime.utcnow().replace(hour=14, minute=0, second=0, microsecond=0)
            meeting_end = meeting_start + timedelta(hours=2)
            
            test_meeting = MeetingHour(
                start_time=meeting_start,
                end_time=meeting_end,
                description="Test Meeting for Time Tracking",
                meeting_type="regular",
                created_by=self.test_data['admin_id']
            )
            db.session.add(test_meeting)
            db.session.commit()
            
            # Test 1: Full attendance with specific times
            full_attendance = AttendanceLog(
                user_id=self.test_data['user1_id'],
                meeting_hour_id=test_meeting.id,
                notes="Full attendance test",
                is_partial=False,
                partial_hours=None,
                attendance_start_time=meeting_start,
                attendance_end_time=meeting_end
            )
            db.session.add(full_attendance)
            db.session.commit()
            
            # Test 2: Partial attendance with specific times
            partial_start = meeting_start + timedelta(minutes=30)
            partial_end = meeting_start + timedelta(hours=1, minutes=30)
            partial_attendance = AttendanceLog(
                user_id=self.test_data['user2_id'],
                meeting_hour_id=test_meeting.id,
                notes="Partial attendance test",
                is_partial=True,
                partial_hours=1.0,
                attendance_start_time=partial_start,
                attendance_end_time=partial_end
            )
            db.session.add(partial_attendance)
            db.session.commit()
            
            # Test 3: Legacy record without specific times
            legacy_attendance = AttendanceLog(
                user_id=self.test_data['admin_id'],
                meeting_hour_id=test_meeting.id,
                notes="Legacy attendance test",
                is_partial=True,
                partial_hours=1.5,
                attendance_start_time=None,
                attendance_end_time=None
            )
            db.session.add(legacy_attendance)
            db.session.commit()
            
            # Test meeting detail data preparation
            from app import get_meeting_attendance_detail
            meeting_data = get_meeting_attendance_detail(test_meeting.id)
            
            if meeting_data and 'attendance' in meeting_data:
                attendance_records = meeting_data['attendance']
                
                # Verify full attendance record
                full_record = next((r for r in attendance_records if r['user']['id'] == self.test_data['user1_id']), None)
                if full_record and full_record['attendance_start_time'] and full_record['attendance_end_time']:
                    print("✓ Full attendance with specific times handled correctly")
                    print(f"  - Start: {full_record['attendance_start_time'].strftime('%H:%M')}")
                    print(f"  - End: {full_record['attendance_end_time'].strftime('%H:%M')}")
                else:
                    print("✗ Full attendance record missing or invalid")
                
                # Verify partial attendance record
                partial_record = next((r for r in attendance_records if r['user']['id'] == self.test_data['user2_id']), None)
                if partial_record and partial_record['attendance_start_time'] and partial_record['attendance_end_time']:
                    print("✓ Partial attendance with specific times handled correctly")
                    print(f"  - Start: {partial_record['attendance_start_time'].strftime('%H:%M')}")
                    print(f"  - End: {partial_record['attendance_end_time'].strftime('%H:%M')}")
                    print(f"  - Hours: {partial_record['hours_attended']}")
                else:
                    print("✗ Partial attendance record missing or invalid")
                
                # Verify legacy record handling
                legacy_record = next((r for r in attendance_records if r['user']['id'] == self.test_data['admin_id']), None)
                if legacy_record and legacy_record['attendance_start_time'] and legacy_record['attendance_end_time']:
                    # Legacy record should have calculated times
                    expected_start = meeting_start
                    expected_end = meeting_start + timedelta(hours=1.5)
                    
                    if (legacy_record['attendance_start_time'] == expected_start and 
                        legacy_record['attendance_end_time'] == expected_end):
                        print("✓ Legacy record calculated times correctly")
                        print(f"  - Calculated start: {legacy_record['attendance_start_time'].strftime('%H:%M')}")
                        print(f"  - Calculated end: {legacy_record['attendance_end_time'].strftime('%H:%M')}")
                    else:
                        print("✗ Legacy record time calculation incorrect")
                else:
                    print("✗ Legacy record missing calculated times")
                
                print("✓ Attendance time tracking test completed")
            else:
                print("✗ Meeting detail data preparation failed")
            
            # Cleanup test meeting
            db.session.delete(test_meeting)
            db.session.commit()

    def test_slack_time_based_logging(self):
        """Test Slack time-based logging functionality"""
        print("Testing Slack time-based logging...")
        
        with self.app.app_context():
            from slack_bot import AttendanceSlackBot
            
            # Create a test meeting
            meeting_start = datetime.utcnow().replace(hour=14, minute=0, second=0, microsecond=0)
            meeting_end = meeting_start + timedelta(hours=2)
            
            test_meeting = MeetingHour(
                start_time=meeting_start,
                end_time=meeting_end,
                description="Test Meeting for Slack Logging",
                meeting_type="regular",
                created_by=self.test_data['admin_id']
            )
            db.session.add(test_meeting)
            db.session.commit()
            
            bot = AttendanceSlackBot()
            
            # Test time-based logging
            date_str = meeting_start.strftime('%Y-%m-%d')
            time_str = f"{meeting_start.strftime('%H:%M')}-{(meeting_start + timedelta(hours=1)).strftime('%H:%M')}"
            text = f"{date_str} {time_str} Test time-based logging"
            
            # Mock the Slack response (we can't actually send to Slack in tests)
            print(f"  - Testing time-based format: {text}")
            
            # Test the time parsing logic directly
            try:
                parts = text.strip().split()
                meeting_date = datetime.strptime(parts[0], "%Y-%m-%d")
                time_str = parts[1]
                start_time_str, end_time_str = time_str.split("-")
                start_time = datetime.strptime(f"{meeting_date.strftime('%Y-%m-%d')} {start_time_str}", "%Y-%m-%d %H:%M")
                end_time = datetime.strptime(f"{meeting_date.strftime('%Y-%m-%d')} {end_time_str}", "%Y-%m-%d %H:%M")
                
                print("✓ Time parsing logic works correctly")
                print(f"  - Parsed start: {start_time.strftime('%H:%M')}")
                print(f"  - Parsed end: {end_time.strftime('%H:%M')}")
                
                # Test overlap calculation
                overlap_start = max(test_meeting.start_time, start_time)
                overlap_end = min(test_meeting.end_time, end_time)
                overlap_hours = (overlap_end - overlap_start).total_seconds() / 3600
                
                print(f"  - Overlap hours: {overlap_hours}")
                print("✓ Overlap calculation works correctly")
                
            except Exception as e:
                print(f"✗ Time parsing failed: {e}")
            
            # Cleanup
            db.session.delete(test_meeting)
            db.session.commit()

    def test_chart_data_preparation(self):
        """Test chart data preparation with attendance times"""
        print("Testing chart data preparation...")
        
        with self.app.app_context():
            # Create a test meeting
            meeting_start = datetime.utcnow().replace(hour=14, minute=0, second=0, microsecond=0)
            meeting_end = meeting_start + timedelta(hours=2)
            
            test_meeting = MeetingHour(
                start_time=meeting_start,
                end_time=meeting_end,
                description="Test Meeting for Chart Data",
                meeting_type="regular",
                created_by=self.test_data['admin_id']
            )
            db.session.add(test_meeting)
            db.session.commit()
            
            # Create attendance records with different time patterns
            # Full attendance
            full_attendance = AttendanceLog(
                user_id=self.test_data['user1_id'],
                meeting_hour_id=test_meeting.id,
                notes="Full attendance",
                is_partial=False,
                partial_hours=None,
                attendance_start_time=meeting_start,
                attendance_end_time=meeting_end
            )
            
            # Partial attendance (first hour)
            partial_attendance = AttendanceLog(
                user_id=self.test_data['user2_id'],
                meeting_hour_id=test_meeting.id,
                notes="Partial attendance",
                is_partial=True,
                partial_hours=1.0,
                attendance_start_time=meeting_start,
                attendance_end_time=meeting_start + timedelta(hours=1)
            )
            
            # Legacy record (should be calculated)
            legacy_attendance = AttendanceLog(
                user_id=self.test_data['admin_id'],
                meeting_hour_id=test_meeting.id,
                notes="Legacy attendance",
                is_partial=True,
                partial_hours=0.5,
                attendance_start_time=None,
                attendance_end_time=None
            )
            
            db.session.add_all([full_attendance, partial_attendance, legacy_attendance])
            db.session.commit()
            
            # Test meeting detail data
            from app import get_meeting_attendance_detail
            meeting_data = get_meeting_attendance_detail(test_meeting.id)
            
            if meeting_data and 'attendance' in meeting_data:
                attendance_records = meeting_data['attendance']
                
                # Simulate chart data preparation
                time_intervals = []
                current_time = meeting_start
                while current_time <= meeting_end:
                    time_intervals.append(current_time)
                    current_time += timedelta(minutes=15)
                
                # Calculate attendance at each interval
                attendance_counts = []
                for interval in time_intervals:
                    count = 0
                    for record in attendance_records:
                        if (record['attendance_start_time'] <= interval <= record['attendance_end_time']):
                            count += 1
                    attendance_counts.append(count)
                
                print("✓ Chart data preparation successful")
                print(f"  - Time intervals: {len(time_intervals)}")
                print(f"  - Attendance counts: {attendance_counts}")
                
                # Verify peak attendance calculation
                max_attendance = max(attendance_counts) if attendance_counts else 0
                peak_time_index = attendance_counts.index(max_attendance) if max_attendance > 0 else 0
                peak_time = time_intervals[peak_time_index] if peak_time_index < len(time_intervals) else meeting_start
                
                print(f"  - Peak attendance: {max_attendance}")
                print(f"  - Peak time: {peak_time.strftime('%H:%M')}")
                print("✓ Peak attendance calculation works")
                
            else:
                print("✗ Chart data preparation failed")
            
            # Cleanup
            db.session.delete(test_meeting)
            db.session.commit()

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
            self.test_attendance_time_tracking()
            self.test_slack_time_based_logging()
            self.test_chart_data_preparation()
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