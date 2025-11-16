"""
One-off script to fix attendance logs where equal start/end times
were incorrectly stored as a 24h duration.

Usage (from project root, ideally in venv):

    python fix_equal_time_entries.py

This will:
- Find AttendanceLog rows where both attendance_start_time and
  attendance_end_time are set, and the duration is ~24h
- Set attendance_end_time == attendance_start_time
- Set partial_hours to 0
- Set is_partial to False

Always back up your database before running.
"""

from datetime import timedelta

from app import app, db, AttendanceLog


def fix_equal_time_entries(dry_run: bool = True) -> None:
    with app.app_context():
        logs = AttendanceLog.query.filter(
            AttendanceLog.attendance_start_time.isnot(None),
            AttendanceLog.attendance_end_time.isnot(None),
        ).all()

        fixed = 0
        candidates = 0

        for log in logs:
            duration = log.attendance_end_time - log.attendance_start_time
            hours = duration.total_seconds() / 3600.0

            # Consider anything very close to exactly 24h as a bugged record
            if abs(hours - 24.0) < 0.01:
                candidates += 1

                # What we'll change:
                new_end = log.attendance_start_time

                print(
                    f"[CANDIDATE] log_id={log.id}, "
                    f"user_id={log.user_id}, meeting_hour_id={log.meeting_hour_id}, "
                    f"old_hours={hours:.2f} -> new_hours=0.00"
                )

                if not dry_run:
                    log.attendance_end_time = new_end
                    log.partial_hours = 0.0
                    log.is_partial = False
                    fixed += 1

        if not dry_run and fixed:
            db.session.commit()

        print(f"Found {candidates} candidate 24h records.")
        if dry_run:
            print("Dry run only. Re-run with dry_run=False in main() to apply changes.")
        else:
            print(f"Updated {fixed} records.")


def main():
    # First run will be a dry run; edit to dry_run=False once you're happy.
    fix_equal_time_entries(dry_run=True)


if __name__ == "__main__":
    main()


