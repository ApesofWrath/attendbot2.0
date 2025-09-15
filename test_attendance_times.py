#!/usr/bin/env python3
"""
Focused test suite for attendance time tracking functionality
Tests the new attendance start/end time features
"""

import os
import sys
import json
from datetime import datetime, timedelta
from app import app, db, User, MeetingHour, AttendanceLog, ReportingPeriod

class TestAttendanceTimeTracking:
    def __init__(self):
        self.app = app
        self.test_data = {}
        
    def setup_test_data(self):
        """Create minimal test data for attendance time tests"""
        with self.app.app_context():
            # Create test admin user
            timestamp = str(int(datetime.utcnow().timestamp()))
            
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
            
            # Create test regular user
            user = User(
                slack_user_id=f"U{timestamp}002",
                username=f"Test User {timestamp}",
                email=f"user{timestamp}@test.com",
                is_admin=False
            )
            db.session.add(user)
            db.session.commit()
            self.test_data['user'] = user
            self.test_data['user_id'] = user.id
            
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

    def cleanup_test_data(self):
        """Clean up test data"""
        with self.app.app_context():
            try:
                # Delete users and period
                for key in ['user', 'admin', 'period']:
                    if key in self.test_data:
                        db.session.delete(self.test_data[key])
                db.session.commit()
            except Exception as e:
                print(f"Cleanup warning: {e}")

    def test_attendance_time_calculation(self):
        """Test attendance time calculation for legacy records"""
        print("Testing attendance time calculation...")
        
        with self.app.app_context():
            # Create a test meeting
            meeting_start = datetime.utcnow().replace(hour=14, minute=0, second=0, microsecond=0)
            meeting_end = meeting_start + timedelta(hours=2)
            
            test_meeting = MeetingHour(
                start_time=meeting_start,
                end_time=meeting_end,
                description="Test Meeting for Time Calculation",
                meeting_type="regular",
                created_by=self.test_data['admin_id']
            )
            db.session.add(test_meeting)
            db.session.commit()
            
            # Test 1: Legacy record with partial hours
            legacy_attendance = AttendanceLog(
                user_id=self.test_data['user_id'],
                meeting_hour_id=test_meeting.id,
                notes="Legacy partial attendance",
                is_partial=True,
                partial_hours=1.5,
                attendance_start_time=None,
                attendance_end_time=None
            )
            db.session.add(legacy_attendance)
            db.session.commit()
            
            # Test the calculation logic
            from app import get_meeting_attendance_detail
            meeting_data = get_meeting_attendance_detail(test_meeting.id)
            
            if meeting_data and 'attendance' in meeting_data:
                attendance_records = meeting_data['attendance']
                legacy_record = attendance_records[0]
                
                # Verify calculated times
                expected_start = meeting_start
                expected_end = meeting_start + timedelta(hours=1.5)
                
                if (legacy_record['attendance_start_time'] == expected_start and 
                    legacy_record['attendance_end_time'] == expected_end):
                    print("✓ Legacy record time calculation correct")
                    print(f"  - Expected: {expected_start.strftime('%H:%M')} - {expected_end.strftime('%H:%M')}")
                    print(f"  - Calculated: {legacy_record['attendance_start_time'].strftime('%H:%M')} - {legacy_record['attendance_end_time'].strftime('%H:%M')}")
                else:
                    print("✗ Legacy record time calculation incorrect")
                    print(f"  - Expected: {expected_start.strftime('%H:%M')} - {expected_end.strftime('%H:%M')}")
                    print(f"  - Got: {legacy_record['attendance_start_time'].strftime('%H:%M')} - {legacy_record['attendance_end_time'].strftime('%H:%M')}")
                
                # Test JSON serialization
                try:
                    json.dumps(meeting_data)
                    print("✓ Meeting data is JSON serializable")
                except TypeError as e:
                    print(f"✗ JSON serialization failed: {e}")
                
            else:
                print("✗ Meeting detail data preparation failed")
            
            # Cleanup
            db.session.delete(test_meeting)
            db.session.commit()

    def test_specific_attendance_times(self):
        """Test attendance records with specific start/end times"""
        print("Testing specific attendance times...")
        
        with self.app.app_context():
            # Create a test meeting
            meeting_start = datetime.utcnow().replace(hour=14, minute=0, second=0, microsecond=0)
            meeting_end = meeting_start + timedelta(hours=2)
            
            test_meeting = MeetingHour(
                start_time=meeting_start,
                end_time=meeting_end,
                description="Test Meeting for Specific Times",
                meeting_type="regular",
                created_by=self.test_data['admin_id']
            )
            db.session.add(test_meeting)
            db.session.commit()
            
            # Test specific attendance times
            specific_start = meeting_start + timedelta(minutes=30)
            specific_end = meeting_start + timedelta(hours=1, minutes=30)
            
            specific_attendance = AttendanceLog(
                user_id=self.test_data['user_id'],
                meeting_hour_id=test_meeting.id,
                notes="Specific time attendance",
                is_partial=True,
                partial_hours=1.0,
                attendance_start_time=specific_start,
                attendance_end_time=specific_end
            )
            db.session.add(specific_attendance)
            db.session.commit()
            
            # Test the data preparation
            from app import get_meeting_attendance_detail
            meeting_data = get_meeting_attendance_detail(test_meeting.id)
            
            if meeting_data and 'attendance' in meeting_data:
                attendance_records = meeting_data['attendance']
                specific_record = attendance_records[0]
                
                if (specific_record['attendance_start_time'] == specific_start and 
                    specific_record['attendance_end_time'] == specific_end):
                    print("✓ Specific attendance times preserved correctly")
                    print(f"  - Start: {specific_record['attendance_start_time'].strftime('%H:%M')}")
                    print(f"  - End: {specific_record['attendance_end_time'].strftime('%H:%M')}")
                else:
                    print("✗ Specific attendance times not preserved")
                
            else:
                print("✗ Meeting detail data preparation failed")
            
            # Cleanup
            db.session.delete(test_meeting)
            db.session.commit()

    def test_chart_data_calculation(self):
        """Test chart data calculation with attendance times"""
        print("Testing chart data calculation...")
        
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
            
            # Create multiple attendance records with different patterns
            # Full attendance
            full_attendance = AttendanceLog(
                user_id=self.test_data['user_id'],
                meeting_hour_id=test_meeting.id,
                notes="Full attendance",
                is_partial=False,
                partial_hours=None,
                attendance_start_time=meeting_start,
                attendance_end_time=meeting_end
            )
            
            # Partial attendance (first hour only)
            partial_attendance = AttendanceLog(
                user_id=self.test_data['admin_id'],
                meeting_hour_id=test_meeting.id,
                notes="Partial attendance",
                is_partial=True,
                partial_hours=1.0,
                attendance_start_time=meeting_start,
                attendance_end_time=meeting_start + timedelta(hours=1)
            )
            
            db.session.add_all([full_attendance, partial_attendance])
            db.session.commit()
            
            # Test chart data calculation
            from app import get_meeting_attendance_detail
            meeting_data = get_meeting_attendance_detail(test_meeting.id)
            
            if meeting_data and 'attendance' in meeting_data:
                attendance_records = meeting_data['attendance']
                
                # Simulate chart calculation
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
                
                print("✓ Chart data calculation successful")
                print(f"  - Time intervals: {len(time_intervals)}")
                print(f"  - Sample counts: {attendance_counts[:5]}...")  # First 5 intervals
                
                # Verify peak attendance
                max_attendance = max(attendance_counts) if attendance_counts else 0
                print(f"  - Peak attendance: {max_attendance}")
                
                # Verify attendance patterns
                # Should have 2 people for first hour, 1 person for second hour
                first_hour_max = max(attendance_counts[:4])  # First 4 intervals (1 hour)
                second_hour_max = max(attendance_counts[4:8])  # Next 4 intervals (1 hour)
                
                if first_hour_max == 2 and second_hour_max == 1:
                    print("✓ Attendance patterns calculated correctly")
                else:
                    print(f"✗ Attendance patterns incorrect: first hour max={first_hour_max}, second hour max={second_hour_max}")
                
            else:
                print("✗ Chart data calculation failed")
            
            # Cleanup
            db.session.delete(test_meeting)
            db.session.commit()

    def test_slack_time_parsing(self):
        """Test Slack time parsing logic"""
        print("Testing Slack time parsing...")
        
        # Test time parsing logic (without actual Slack integration)
        test_cases = [
            ("2024-01-15 14:00-15:30", "14:00", "15:30"),
            ("2024-01-15 09:30-11:00", "09:30", "11:00"),
            ("2024-01-15 13:45-14:15", "13:45", "14:15"),
        ]
        
        for test_input, expected_start, expected_end in test_cases:
            try:
                parts = test_input.strip().split()
                date_str = parts[0]
                time_str = parts[1]
                
                # Parse date
                meeting_date = datetime.strptime(date_str, "%Y-%m-%d")
                
                # Parse time range
                start_time_str, end_time_str = time_str.split("-")
                start_time = datetime.strptime(f"{meeting_date.strftime('%Y-%m-%d')} {start_time_str}", "%Y-%m-%d %H:%M")
                end_time = datetime.strptime(f"{meeting_date.strftime('%Y-%m-%d')} {end_time_str}", "%Y-%m-%d %H:%M")
                
                if (start_time.strftime('%H:%M') == expected_start and 
                    end_time.strftime('%H:%M') == expected_end):
                    print(f"✓ Time parsing correct: {test_input} -> {start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')}")
                else:
                    print(f"✗ Time parsing incorrect: {test_input} -> {start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')} (expected {expected_start}-{expected_end})")
                    
            except Exception as e:
                print(f"✗ Time parsing failed for {test_input}: {e}")

    def run_all_tests(self):
        """Run all attendance time tracking tests"""
        print("Attendance Time Tracking Test Suite")
        print("=" * 40)
        
        try:
            self.setup_test_data()
            print("✓ Test data setup complete")
            
            self.test_attendance_time_calculation()
            self.test_specific_attendance_times()
            self.test_chart_data_calculation()
            self.test_slack_time_parsing()
            
        except Exception as e:
            print(f"✗ Test suite error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.cleanup_test_data()
            print("✓ Test cleanup complete")
        
        print("\nAttendance time tracking tests completed!")

def main():
    """Run the test suite"""
    tester = TestAttendanceTimeTracking()
    tester.run_all_tests()

if __name__ == "__main__":
    main()
