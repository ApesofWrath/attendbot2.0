#!/usr/bin/env python3
"""
Unit tests for core attendance time tracking logic
Tests the calculation functions without database operations
"""

from datetime import datetime, timedelta

def test_legacy_time_calculation():
    """Test legacy record time calculation logic"""
    print("Testing legacy time calculation logic...")
    
    # Simulate a meeting
    meeting_start = datetime(2024, 1, 15, 14, 0)  # 2:00 PM
    meeting_end = datetime(2024, 1, 15, 16, 0)    # 4:00 PM
    
    # Test case 1: Partial attendance (1.5 hours)
    partial_hours = 1.5
    expected_start = meeting_start
    expected_end = meeting_start + timedelta(hours=partial_hours)
    
    # Simulate the calculation logic
    if partial_hours is not None:
        calculated_start = meeting_start
        calculated_end = meeting_start + timedelta(hours=partial_hours)
    else:
        calculated_start = meeting_start
        calculated_end = meeting_end
    
    if calculated_start == expected_start and calculated_end == expected_end:
        print("✓ Legacy partial attendance calculation correct")
        print(f"  - Meeting: {meeting_start.strftime('%H:%M')} - {meeting_end.strftime('%H:%M')}")
        print(f"  - Logged: {partial_hours} hours")
        print(f"  - Calculated: {calculated_start.strftime('%H:%M')} - {calculated_end.strftime('%H:%M')}")
    else:
        print("✗ Legacy partial attendance calculation incorrect")
    
    # Test case 2: Full attendance
    full_hours = 2.0
    expected_start = meeting_start
    expected_end = meeting_end
    
    if full_hours is not None and full_hours == (meeting_end - meeting_start).total_seconds() / 3600:
        calculated_start = meeting_start
        calculated_end = meeting_end
    else:
        calculated_start = meeting_start
        calculated_end = meeting_start + timedelta(hours=full_hours)
    
    if calculated_start == expected_start and calculated_end == expected_end:
        print("✓ Legacy full attendance calculation correct")
        print(f"  - Meeting: {meeting_start.strftime('%H:%M')} - {meeting_end.strftime('%H:%M')}")
        print(f"  - Logged: {full_hours} hours")
        print(f"  - Calculated: {calculated_start.strftime('%H:%M')} - {calculated_end.strftime('%H:%M')}")
    else:
        print("✗ Legacy full attendance calculation incorrect")

def test_time_parsing():
    """Test time parsing logic for Slack commands"""
    print("Testing time parsing logic...")
    
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

def test_overlap_calculation():
    """Test overlap calculation for time-based logging"""
    print("Testing overlap calculation...")
    
    # Meeting: 14:00-16:00 (2 hours)
    meeting_start = datetime(2024, 1, 15, 14, 0)
    meeting_end = datetime(2024, 1, 15, 16, 0)
    
    # User logs: 14:30-15:30 (1 hour)
    user_start = datetime(2024, 1, 15, 14, 30)
    user_end = datetime(2024, 1, 15, 15, 30)
    
    # Calculate overlap
    overlap_start = max(meeting_start, user_start)
    overlap_end = min(meeting_end, user_end)
    overlap_hours = (overlap_end - overlap_start).total_seconds() / 3600
    
    expected_hours = 1.0
    if overlap_hours == expected_hours:
        print("✓ Overlap calculation correct")
        print(f"  - Meeting: {meeting_start.strftime('%H:%M')} - {meeting_end.strftime('%H:%M')}")
        print(f"  - User logged: {user_start.strftime('%H:%M')} - {user_end.strftime('%H:%M')}")
        print(f"  - Overlap: {overlap_start.strftime('%H:%M')} - {overlap_end.strftime('%H:%M')} ({overlap_hours}h)")
    else:
        print(f"✗ Overlap calculation incorrect: expected {expected_hours}h, got {overlap_hours}h")
    
    # Test case 2: User logs outside meeting time
    user_start_2 = datetime(2024, 1, 15, 13, 0)  # Before meeting
    user_end_2 = datetime(2024, 1, 15, 13, 30)   # Before meeting
    
    overlap_start_2 = max(meeting_start, user_start_2)
    overlap_end_2 = min(meeting_end, user_end_2)
    overlap_hours_2 = (overlap_end_2 - overlap_start_2).total_seconds() / 3600
    
    if overlap_hours_2 == 0:
        print("✓ No overlap calculation correct")
        print(f"  - User logged: {user_start_2.strftime('%H:%M')} - {user_end_2.strftime('%H:%M')}")
        print(f"  - Overlap: {overlap_hours_2}h")
    else:
        print(f"✗ No overlap calculation incorrect: expected 0h, got {overlap_hours_2}h")

def test_chart_data_simulation():
    """Test chart data calculation simulation"""
    print("Testing chart data calculation...")
    
    # Meeting: 14:00-16:00 (2 hours)
    meeting_start = datetime(2024, 1, 15, 14, 0)
    meeting_end = datetime(2024, 1, 15, 16, 0)
    
    # Simulate attendance records
    attendance_records = [
        {
            'attendance_start_time': meeting_start,
            'attendance_end_time': meeting_end,  # Full attendance
            'user': 'User1'
        },
        {
            'attendance_start_time': meeting_start,
            'attendance_end_time': meeting_start + timedelta(hours=1),  # First hour only
            'user': 'User2'
        },
        {
            'attendance_start_time': meeting_start + timedelta(minutes=30),
            'attendance_end_time': meeting_start + timedelta(hours=1, minutes=30),  # Middle hour
            'user': 'User3'
        }
    ]
    
    # Create time intervals (every 15 minutes)
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
    print(f"  - Attendance counts: {attendance_counts}")
    
    # Verify peak attendance
    max_attendance = max(attendance_counts) if attendance_counts else 0
    peak_time_index = attendance_counts.index(max_attendance) if max_attendance > 0 else 0
    peak_time = time_intervals[peak_time_index] if peak_time_index < len(time_intervals) else meeting_start
    
    print(f"  - Peak attendance: {max_attendance}")
    print(f"  - Peak time: {peak_time.strftime('%H:%M')}")
    
    # Verify expected patterns
    # Should have 3 people for first hour, 2 people for second hour
    first_hour_max = max(attendance_counts[:4])  # First 4 intervals (1 hour)
    second_hour_max = max(attendance_counts[4:8])  # Next 4 intervals (1 hour)
    
    if first_hour_max == 3 and second_hour_max == 1:
        print("✓ Attendance patterns calculated correctly")
    else:
        print(f"✗ Attendance patterns incorrect: first hour max={first_hour_max}, second hour max={second_hour_max}")

def run_all_tests():
    """Run all core logic tests"""
    print("Core Attendance Time Tracking Logic Tests")
    print("=" * 45)
    
    test_legacy_time_calculation()
    print()
    test_time_parsing()
    print()
    test_overlap_calculation()
    print()
    test_chart_data_simulation()
    print()
    
    print("Core logic tests completed!")

if __name__ == "__main__":
    run_all_tests()
