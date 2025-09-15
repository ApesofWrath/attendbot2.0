import os
import json
import logging
from datetime import datetime, timedelta
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from app import app, db, User, MeetingHour, AttendanceLog, ReportingPeriod, Excuse, ExcuseRequest
from google_auth import get_slack_user_info
import pytz

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AttendanceSlackBot:
    def __init__(self):
        self.client = WebClient(token=os.environ.get('SLACK_BOT_TOKEN'))
        self.app = app
    
    def handle_command(self, command, user_id, channel_id, text=""):
        """Handle Slack slash commands"""
        with self.app.app_context():
            user = User.query.filter_by(slack_user_id=user_id).first()
            
            if not user:
                # Try to get user info from Slack and create user automatically
                logger.info(f"User not found in database for slack_user_id: {user_id}")
                slack_user_info = get_slack_user_info(user_id)
                logger.info(f"Slack user info retrieved: {slack_user_info}")
                
                if slack_user_info:
                    # Try to match by email first (if available)
                    if slack_user_info.get('email'):
                        existing_user = User.query.filter_by(email=slack_user_info['email']).first()
                        if existing_user:
                            logger.info(f"Found existing user with email {slack_user_info['email']}, updating slack_user_id")
                            existing_user.slack_user_id = user_id
                            db.session.commit()
                            user = existing_user
                            self._send_ephemeral_message(channel_id, user_id, f"✅ Your Slack account has been linked! You can now use commands.")
                        else:
                            # Create user automatically with email
                            logger.info(f"Creating new user with email {slack_user_info['email']}")
                            user = User(
                                slack_user_id=user_id,
                                email=slack_user_info['email'],
                                username=slack_user_info.get('display_name', slack_user_info.get('name', 'Slack User')),
                                is_admin=False
                            )
                            db.session.add(user)
                            db.session.commit()
                            self._send_ephemeral_message(channel_id, user_id, f"✅ Welcome! Your account has been created. You can now log attendance.")
                    else:
                        # No email from Slack - try to match by display name or real name
                        logger.info(f"No email from Slack, trying to match by name: {slack_user_info.get('display_name')} or {slack_user_info.get('name')}")
                        
                        # Try to find user by username (case-insensitive)
                        display_name = slack_user_info.get('display_name', '').lower().strip()
                        real_name = slack_user_info.get('name', '').lower().strip()
                        
                        existing_user = None
                        if display_name:
                            existing_user = User.query.filter(User.username.ilike(f"%{display_name}%")).first()
                        if not existing_user and real_name:
                            existing_user = User.query.filter(User.username.ilike(f"%{real_name}%")).first()
                        
                        if existing_user:
                            logger.info(f"Found existing user by name match: {existing_user.username}, linking Slack account")
                            existing_user.slack_user_id = user_id
                            db.session.commit()
                            user = existing_user
                            self._send_ephemeral_message(channel_id, user_id, f"✅ Your Slack account has been linked to {existing_user.username}! You can now use commands.")
                        else:
                            # No match found - need manual linking
                            logger.error(f"No existing user found for Slack user {slack_user_info.get('display_name')} ({slack_user_info.get('name')})")
                            return self._send_ephemeral_message(channel_id, user_id, "❌ No matching account found. Please log in to the web app first to create your account, or contact an admin to link your Slack account.")
                else:
                    logger.error(f"Failed to get slack user info")
                    return self._send_ephemeral_message(channel_id, user_id, "❌ Unable to retrieve Slack user information. Please contact an admin.")
            
            if command == "/add_meeting":
                return self._handle_add_meeting(user, channel_id, user_id, text)
            elif command == "/add_outreach":
                return self._handle_add_outreach(user, channel_id, user_id, text)
            elif command == "/log_attendance":
                return self._handle_log_attendance(user, channel_id, user_id, text)
            elif command == "/log_outreach":
                return self._handle_log_outreach(user, channel_id, user_id, text)
            elif command == "/create_period":
                return self._handle_create_period(user, channel_id, user_id, text)
            elif command == "/excuse":
                return self._handle_excuse(user, channel_id, user_id, text)
            elif command == "/my_attendance":
                return self._handle_my_attendance(user, channel_id, user_id)
            elif command == "/request_excuse":
                return self._handle_request_excuse(user, channel_id, user_id, text)
            elif command == "/help":
                return self._handle_help(user, channel_id, user_id)
            else:
                return self._send_ephemeral_message(channel_id, user_id, "❌ Unknown command. Use `/help` to see available commands.")
    
    def _handle_add_meeting(self, user, channel_id, user_id, text):
        """Handle adding a new meeting hour"""
        if not user.is_admin:
            return self._send_ephemeral_message(channel_id, user_id, "❌ Admin privileges required.")
        
        try:
            # Parse text: "YYYY-MM-DD HH:MM-HH:MM Description with spaces"
            parts = text.strip().split()
            if len(parts) < 3:
                return self._send_ephemeral_message(channel_id, user_id, "❌ Format: `/add_meeting YYYY-MM-DD HH:MM-HH:MM Description`")
            
            date_str = parts[0]
            time_str = parts[1]
            description = " ".join(parts[2:])  # Join remaining parts to handle spaces in description
            
            # Parse date and time
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            start_time_str, end_time_str = time_str.split("-")
            start_time = datetime.strptime(f"{date_str} {start_time_str}", "%Y-%m-%d %H:%M")
            end_time = datetime.strptime(f"{date_str} {end_time_str}", "%Y-%m-%d %H:%M")
            
            # Create meeting hour
            meeting_hour = MeetingHour(
                start_time=start_time,
                end_time=end_time,
                description=description,
                meeting_type='regular',
                created_by=user.id
            )
            
            db.session.add(meeting_hour)
            db.session.commit()
            
            return self._send_ephemeral_message(channel_id, user_id, f"✅ Meeting added: {description} on {date_str} from {start_time_str} to {end_time_str}")
            
        except Exception as e:
            return self._send_ephemeral_message(channel_id, user_id, f"❌ Error adding meeting: {str(e)}")
    
    def _handle_add_outreach(self, user, channel_id, user_id, text):
        """Handle adding a new outreach event"""
        if not user.is_admin:
            return self._send_ephemeral_message(channel_id, user_id, "❌ Admin privileges required.")
        
        try:
            # Parse text: "YYYY-MM-DD HH:MM-HH:MM Description"
            parts = text.strip().split()
            if len(parts) < 3:
                return self._send_ephemeral_message(channel_id, user_id, "❌ Format: `/add_outreach YYYY-MM-DD HH:MM-HH:MM Description`")
            
            date_str = parts[0]
            time_str = parts[1]
            description = " ".join(parts[2:])
            
            # Parse date and time
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            start_time_str, end_time_str = time_str.split("-")
            start_time = datetime.strptime(f"{date_str} {start_time_str}", "%Y-%m-%d %H:%M")
            end_time = datetime.strptime(f"{date_str} {end_time_str}", "%Y-%m-%d %H:%M")
            
            # Create outreach event
            outreach_event = MeetingHour(
                start_time=start_time,
                end_time=end_time,
                description=description,
                meeting_type='outreach',
                created_by=user.id
            )
            
            db.session.add(outreach_event)
            db.session.commit()
            
            # Calculate duration
            duration_hours = (end_time - start_time).total_seconds() / 3600
            
            return self._send_ephemeral_message(channel_id, user_id, f"✅ Outreach event added: {description} on {date_str} from {start_time_str} to {end_time_str} ({duration_hours:.1f} hours)")
            
        except Exception as e:
            return self._send_ephemeral_message(channel_id, user_id, f"❌ Error adding outreach event: {str(e)}")
    
    def _handle_log_attendance(self, user, channel_id, user_id, text):
        """Handle logging attendance (supports both meeting_id and time-based logging)"""
        try:
            parts = text.strip().split()
            if not parts:
                return self._send_ephemeral_message(channel_id, user_id, "❌ Format: `/log_attendance meeting_id [notes]` or `/log_attendance YYYY-MM-DD HH:MM-HH:MM [notes]`")
            
            # Check if first part is a date (YYYY-MM-DD format) or meeting ID
            first_part = parts[0]
            
            # Try to parse as date first
            try:
                meeting_date = datetime.strptime(first_part, "%Y-%m-%d")
                # This is date-based logging with time range
                return self._handle_time_based_logging(user, channel_id, user_id, parts, meeting_date)
            except ValueError:
                # This is meeting ID based logging
                return self._handle_meeting_id_logging(user, channel_id, user_id, parts)
                
        except Exception as e:
            return self._send_ephemeral_message(channel_id, user_id, f"❌ Error logging attendance: {str(e)}")
    
    def _handle_meeting_id_logging(self, user, channel_id, user_id, parts):
        """Handle meeting ID based logging (full attendance)"""
        try:
            if len(parts) < 1:
                return self._send_ephemeral_message(channel_id, user_id, "❌ Format: `/log_attendance meeting_id [notes]`")
            
            meeting_id = int(parts[0])
            notes = " ".join(parts[1:]) if len(parts) > 1 else ""
            
            # Check if meeting exists
            meeting_hour = MeetingHour.query.get(meeting_id)
            if not meeting_hour:
                return self._send_ephemeral_message(channel_id, user_id, "❌ Meeting not found.")
            
            # Check if already logged
            existing_log = AttendanceLog.query.filter_by(
                user_id=user.id,
                meeting_hour_id=meeting_id
            ).first()
            
            if existing_log:
                return self._send_ephemeral_message(channel_id, user_id, "❌ Attendance already logged for this meeting.")
            
            # Calculate meeting duration
            meeting_duration = (meeting_hour.end_time - meeting_hour.start_time).total_seconds() / 3600
            
            # Create attendance log (full attendance)
            attendance_log = AttendanceLog(
                user_id=user.id,
                meeting_hour_id=meeting_id,
                notes=notes,
                is_partial=False,
                partial_hours=None,
                attendance_start_time=meeting_hour.start_time,
                attendance_end_time=meeting_hour.end_time
            )
            
            db.session.add(attendance_log)
            db.session.commit()
            
            return self._send_ephemeral_message(channel_id, user_id, f"✅ Full attendance logged: {meeting_duration:.1f}h for {meeting_hour.description}")
            
        except ValueError:
            return self._send_ephemeral_message(channel_id, user_id, "❌ Invalid meeting ID. Must be a number.")
    
    def _handle_time_based_logging(self, user, channel_id, user_id, parts, meeting_date):
        """Handle time-based logging with start and end times"""
        try:
            if len(parts) < 3:
                return self._send_ephemeral_message(channel_id, user_id, "❌ Format: `/log_attendance YYYY-MM-DD HH:MM-HH:MM [notes]`")
            
            # Parse time range
            time_str = parts[1]
            notes = " ".join(parts[2:]) if len(parts) > 2 else ""
            
            # Parse time range
            try:
                start_time_str, end_time_str = time_str.split("-")
                start_time = datetime.strptime(f"{meeting_date.strftime('%Y-%m-%d')} {start_time_str}", "%Y-%m-%d %H:%M")
                end_time = datetime.strptime(f"{meeting_date.strftime('%Y-%m-%d')} {end_time_str}", "%Y-%m-%d %H:%M")
                
                if end_time <= start_time:
                    return self._send_ephemeral_message(channel_id, user_id, "❌ End time must be after start time.")
                    
            except ValueError:
                return self._send_ephemeral_message(channel_id, user_id, "❌ Invalid time format. Use HH:MM-HH:MM (e.g., 14:00-15:30).")
            
            # Find meetings that overlap with the specified time range
            meetings = MeetingHour.query.filter(
                db.func.date(MeetingHour.start_time) == meeting_date.date(),
                MeetingHour.meeting_type == 'regular',
                MeetingHour.start_time <= end_time,
                MeetingHour.end_time >= start_time
            ).all()
            
            if not meetings:
                return self._send_ephemeral_message(channel_id, user_id, f"❌ No regular meetings found on {meeting_date.strftime('%Y-%m-%d')} that overlap with {start_time_str}-{end_time_str}. Please check the time or contact an admin.")
            
            # If multiple meetings overlap, find the best match (most overlap)
            best_meeting = None
            max_overlap = 0
            
            for meeting in meetings:
                # Calculate overlap duration
                overlap_start = max(meeting.start_time, start_time)
                overlap_end = min(meeting.end_time, end_time)
                overlap_duration = (overlap_end - overlap_start).total_seconds() / 3600
                
                if overlap_duration > max_overlap:
                    max_overlap = overlap_duration
                    best_meeting = meeting
            
            if not best_meeting:
                return self._send_ephemeral_message(channel_id, user_id, f"❌ No suitable meeting found for the time range {start_time_str}-{end_time_str}.")
            
            # Check if already logged
            existing_log = AttendanceLog.query.filter_by(
                user_id=user.id,
                meeting_hour_id=best_meeting.id
            ).first()
            
            if existing_log:
                return self._send_ephemeral_message(channel_id, user_id, f"❌ Attendance already logged for {best_meeting.description} on {meeting_date.strftime('%Y-%m-%d')}.")
            
            # Calculate actual hours attended (overlap with meeting)
            actual_start = max(best_meeting.start_time, start_time)
            actual_end = min(best_meeting.end_time, end_time)
            hours_attended = (actual_end - actual_start).total_seconds() / 3600
            meeting_duration = (best_meeting.end_time - best_meeting.start_time).total_seconds() / 3600
            
            # Determine if this is partial attendance
            is_partial = hours_attended < meeting_duration
            
            # Create attendance log
            attendance_log = AttendanceLog(
                user_id=user.id,
                meeting_hour_id=best_meeting.id,
                notes=notes,
                is_partial=is_partial,
                partial_hours=hours_attended if is_partial else None,
                attendance_start_time=actual_start,
                attendance_end_time=actual_end
            )
            
            db.session.add(attendance_log)
            db.session.commit()
            
            if is_partial:
                return self._send_ephemeral_message(channel_id, user_id, f"✅ Partial attendance logged: {hours_attended:.1f}h of {meeting_duration:.1f}h for {best_meeting.description} on {meeting_date.strftime('%Y-%m-%d')}")
            else:
                return self._send_ephemeral_message(channel_id, user_id, f"✅ Full attendance logged: {hours_attended:.1f}h for {best_meeting.description} on {meeting_date.strftime('%Y-%m-%d')}")
            
        except Exception as e:
            return self._send_ephemeral_message(channel_id, user_id, f"❌ Error logging attendance: {str(e)}")
    
    def _handle_log_outreach(self, user, channel_id, user_id, text):
        """Handle logging outreach attendance (supports both outreach_id and time-based logging)"""
        try:
            parts = text.strip().split()
            if not parts:
                return self._send_ephemeral_message(channel_id, user_id, "❌ Format: `/log_outreach outreach_id [notes]` or `/log_outreach YYYY-MM-DD HH:MM-HH:MM [notes]`")
            
            # Check if first part is a date (YYYY-MM-DD format) or outreach ID
            first_part = parts[0]
            
            # Try to parse as date first
            try:
                outreach_date = datetime.strptime(first_part, "%Y-%m-%d")
                # This is date-based logging with time range
                return self._handle_outreach_time_based_logging(user, channel_id, user_id, parts, outreach_date)
            except ValueError:
                # This is outreach ID based logging
                return self._handle_outreach_id_logging(user, channel_id, user_id, parts)
                
        except Exception as e:
            return self._send_ephemeral_message(channel_id, user_id, f"❌ Error logging outreach attendance: {str(e)}")
    
    def _handle_outreach_id_logging(self, user, channel_id, user_id, parts):
        """Handle outreach ID based logging (full attendance)"""
        try:
            if len(parts) < 1:
                return self._send_ephemeral_message(channel_id, user_id, "❌ Format: `/log_outreach outreach_id [notes]`")
            
            outreach_id = int(parts[0])
            notes = " ".join(parts[1:]) if len(parts) > 1 else ""
            
            # Check if outreach event exists and is outreach type
            outreach_event = MeetingHour.query.get(outreach_id)
            if not outreach_event:
                return self._send_ephemeral_message(channel_id, user_id, "❌ Outreach event not found.")
            
            if outreach_event.meeting_type != 'outreach':
                return self._send_ephemeral_message(channel_id, user_id, "❌ This is not an outreach event.")
            
            # Check if already logged
            existing_log = AttendanceLog.query.filter_by(
                user_id=user.id,
                meeting_hour_id=outreach_id
            ).first()
            
            if existing_log:
                return self._send_ephemeral_message(channel_id, user_id, "❌ Outreach attendance already logged for this event.")
            
            # Calculate duration
            duration_hours = (outreach_event.end_time - outreach_event.start_time).total_seconds() / 3600
            
            # Create attendance log (full attendance)
            attendance_log = AttendanceLog(
                user_id=user.id,
                meeting_hour_id=outreach_id,
                notes=notes,
                is_partial=False,
                partial_hours=None,
                attendance_start_time=outreach_event.start_time,
                attendance_end_time=outreach_event.end_time
            )
            
            db.session.add(attendance_log)
            db.session.commit()
            
            return self._send_ephemeral_message(channel_id, user_id, f"✅ Outreach attendance logged for: {outreach_event.description} ({duration_hours:.1f} hours)")
            
        except ValueError:
            return self._send_ephemeral_message(channel_id, user_id, "❌ Invalid outreach event ID. Must be a number.")
    
    def _handle_outreach_time_based_logging(self, user, channel_id, user_id, parts, outreach_date):
        """Handle time-based outreach logging with start and end times"""
        try:
            if len(parts) < 3:
                return self._send_ephemeral_message(channel_id, user_id, "❌ Format: `/log_outreach YYYY-MM-DD HH:MM-HH:MM [notes]`")
            
            # Parse time range
            time_str = parts[1]
            notes = " ".join(parts[2:]) if len(parts) > 2 else ""
            
            # Parse time range
            try:
                start_time_str, end_time_str = time_str.split("-")
                start_time = datetime.strptime(f"{outreach_date.strftime('%Y-%m-%d')} {start_time_str}", "%Y-%m-%d %H:%M")
                end_time = datetime.strptime(f"{outreach_date.strftime('%Y-%m-%d')} {end_time_str}", "%Y-%m-%d %H:%M")
                
                if end_time <= start_time:
                    return self._send_ephemeral_message(channel_id, user_id, "❌ End time must be after start time.")
                    
            except ValueError:
                return self._send_ephemeral_message(channel_id, user_id, "❌ Invalid time format. Use HH:MM-HH:MM (e.g., 14:00-15:30).")
            
            # Find outreach events that overlap with the specified time range
            outreach_events = MeetingHour.query.filter(
                db.func.date(MeetingHour.start_time) == outreach_date.date(),
                MeetingHour.meeting_type == 'outreach',
                MeetingHour.start_time <= end_time,
                MeetingHour.end_time >= start_time
            ).all()
            
            if not outreach_events:
                return self._send_ephemeral_message(channel_id, user_id, f"❌ No outreach events found on {outreach_date.strftime('%Y-%m-%d')} that overlap with {start_time_str}-{end_time_str}. Please check the time or contact an admin.")
            
            # If multiple events overlap, find the best match (most overlap)
            best_event = None
            max_overlap = 0
            
            for event in outreach_events:
                # Calculate overlap duration
                overlap_start = max(event.start_time, start_time)
                overlap_end = min(event.end_time, end_time)
                overlap_duration = (overlap_end - overlap_start).total_seconds() / 3600
                
                if overlap_duration > max_overlap:
                    max_overlap = overlap_duration
                    best_event = event
            
            if not best_event:
                return self._send_ephemeral_message(channel_id, user_id, f"❌ No suitable outreach event found for the time range {start_time_str}-{end_time_str}.")
            
            # Check if already logged
            existing_log = AttendanceLog.query.filter_by(
                user_id=user.id,
                meeting_hour_id=best_event.id
            ).first()
            
            if existing_log:
                return self._send_ephemeral_message(channel_id, user_id, f"❌ Outreach attendance already logged for {best_event.description} on {outreach_date.strftime('%Y-%m-%d')}.")
            
            # Calculate actual hours attended (overlap with event)
            actual_start = max(best_event.start_time, start_time)
            actual_end = min(best_event.end_time, end_time)
            hours_attended = (actual_end - actual_start).total_seconds() / 3600
            event_duration = (best_event.end_time - best_event.start_time).total_seconds() / 3600
            
            # Determine if this is partial attendance
            is_partial = hours_attended < event_duration
            
            # Create attendance log
            attendance_log = AttendanceLog(
                user_id=user.id,
                meeting_hour_id=best_event.id,
                notes=notes,
                is_partial=is_partial,
                partial_hours=hours_attended if is_partial else None,
                attendance_start_time=actual_start,
                attendance_end_time=actual_end
            )
            
            db.session.add(attendance_log)
            db.session.commit()
            
            if is_partial:
                return self._send_ephemeral_message(channel_id, user_id, f"✅ Partial outreach attendance logged: {hours_attended:.1f}h of {event_duration:.1f}h for {best_event.description} on {outreach_date.strftime('%Y-%m-%d')}")
            else:
                return self._send_ephemeral_message(channel_id, user_id, f"✅ Full outreach attendance logged: {hours_attended:.1f}h for {best_event.description} on {outreach_date.strftime('%Y-%m-%d')}")
            
        except Exception as e:
            return self._send_ephemeral_message(channel_id, user_id, f"❌ Error logging outreach attendance: {str(e)}")
    
    def _handle_create_period(self, user, channel_id, user_id, text):
        """Handle creating a new reporting period"""
        if not user.is_admin:
            return self._send_ephemeral_message(channel_id, user_id, "❌ Admin privileges required.")
        
        try:
            # Parse text: "name with spaces YYYY-MM-DD YYYY-MM-DD"
            parts = text.strip().split()
            if len(parts) < 3:
                return self._send_ephemeral_message(channel_id, user_id, "❌ Format: `/create_period name YYYY-MM-DD YYYY-MM-DD`")
            
            # Last two parts are dates, everything else is the name
            name = " ".join(parts[:-2])  # Join all parts except last two to handle spaces in name
            start_date = datetime.strptime(parts[-2], "%Y-%m-%d")
            end_date = datetime.strptime(parts[-1], "%Y-%m-%d")
            
            # Create reporting period
            period = ReportingPeriod(
                name=name,
                start_date=start_date,
                end_date=end_date,
                created_by=user.id
            )
            
            db.session.add(period)
            db.session.commit()
            
            return self._send_ephemeral_message(channel_id, user_id, f"✅ Reporting period created: {name} ({parts[-2]} to {parts[-1]})")
            
        except Exception as e:
            return self._send_ephemeral_message(channel_id, user_id, f"❌ Error creating period: {str(e)}")
    
    def _handle_excuse(self, user, channel_id, user_id, text):
        """Handle excusing a user from a meeting"""
        if not user.is_admin:
            return self._send_ephemeral_message(channel_id, user_id, "❌ Admin privileges required.")
        
        try:
            # Parse text: "user_id meeting_id reason"
            parts = text.strip().split(None, 2)
            if len(parts) != 3:
                return self._send_ephemeral_message(channel_id, user_id, "❌ Format: `/excuse user_id meeting_id reason`")
            
            target_user_id = int(parts[0])
            meeting_id = int(parts[1])
            reason = parts[2]
            
            # Check if user exists
            target_user = User.query.get(target_user_id)
            if not target_user:
                return self._send_ephemeral_message(channel_id, user_id, "❌ User not found.")
            
            # Check if meeting exists
            meeting_hour = MeetingHour.query.get(meeting_id)
            if not meeting_hour:
                return self._send_ephemeral_message(channel_id, user_id, "❌ Meeting not found.")
            
            # Check if it's an outreach event (cannot be excused)
            if meeting_hour.meeting_type == 'outreach':
                return self._send_ephemeral_message(channel_id, user_id, f"❌ Outreach events cannot be excused. All outreach hours count toward the total.")
            
            # Get current reporting period
            current_period = ReportingPeriod.query.filter(
                ReportingPeriod.start_date <= datetime.utcnow(),
                ReportingPeriod.end_date >= datetime.utcnow()
            ).first()
            
            if not current_period:
                return self._send_ephemeral_message(channel_id, user_id, "❌ No active reporting period.")
            
            # Create excuse
            excuse = Excuse(
                user_id=target_user_id,
                meeting_hour_id=meeting_id,
                reporting_period_id=current_period.id,
                reason=reason,
                created_by=user.id
            )
            
            db.session.add(excuse)
            db.session.commit()
            
            return self._send_ephemeral_message(channel_id, user_id, f"✅ {target_user.username} excused from {meeting_hour.description}")
            
        except ValueError:
            return self._send_ephemeral_message(channel_id, user_id, "❌ Invalid user ID or meeting ID. Must be numbers.")
        except Exception as e:
            return self._send_ephemeral_message(channel_id, user_id, f"❌ Error creating excuse: {str(e)}")
    
    def _handle_my_attendance(self, user, channel_id, user_id):
        """Handle showing user's attendance"""
        try:
            # Get current reporting period
            current_period = ReportingPeriod.query.filter(
                ReportingPeriod.start_date <= datetime.utcnow(),
                ReportingPeriod.end_date >= datetime.utcnow()
            ).first()
            
            if not current_period:
                return self._send_ephemeral_message(channel_id, user_id, "❌ No active reporting period.")
            
            # Get user's attendance data
            from app import get_user_attendance_data
            attendance_data = get_user_attendance_data(user.id, current_period.id)
            
            if not attendance_data:
                return self._send_ephemeral_message(channel_id, user_id, "❌ No attendance data available.")
            
            # Format response
            message = f"📊 *Your Attendance Report*\n"
            message += f"Period: {current_period.name}\n\n"
            
            # Regular meetings - now hour-based
            regular = attendance_data['regular_meetings']
            message += f"*Regular Meetings:*\n"
            message += f"Total Hours: {regular['total_hours']} | Attended: {regular['attended_hours']} | Excused: {regular['excused_hours']}\n"
            message += f"Effective Total: {regular['effective_total_hours']} | Effective Attended: {regular['effective_attended_hours']}\n"
            message += f"Attendance Rate: {regular['attendance_percentage']}%\n"
            message += f"Team Requirement (60%): {'✅' if regular['meets_team_requirement'] else '❌'}\n"
            message += f"Travel Requirement (75%): {'✅' if regular['meets_travel_requirement'] else '❌'}\n\n"
            
            # Outreach hours
            outreach = attendance_data['outreach_hours']
            message += f"*Outreach Hours:*\n"
            message += f"Total Hours: {outreach['total_hours']} | Attended: {outreach['attended_hours']}\n"
            message += f"Team Requirement (12h): {'✅' if outreach['meets_team_requirement'] else '❌'}\n"
            message += f"Travel Requirement (18h): {'✅' if outreach['meets_travel_requirement'] else '❌'}\n"
            
            return self._send_ephemeral_message(channel_id, user_id, message)
            
        except Exception as e:
            return self._send_ephemeral_message(channel_id, user_id, f"❌ Error getting attendance data: {str(e)}")
    
    def _handle_request_excuse(self, user, channel_id, user_id, text):
        """Handle requesting an excuse for a meeting"""
        try:
            parts = text.strip().split()
            if len(parts) < 2:
                return self._send_ephemeral_message(channel_id, user_id, "❌ Format: `/request_excuse meeting_id reason` or `/request_excuse YYYY-MM-DD reason`")
            
            # Check if first part is a date or meeting ID
            first_part = parts[0]
            reason = " ".join(parts[1:])
            
            # Try to parse as date first
            try:
                meeting_date = datetime.strptime(first_part, "%Y-%m-%d")
                # Date-based request
                return self._handle_date_based_excuse_request(user, channel_id, user_id, meeting_date, reason)
            except ValueError:
                # Meeting ID based request
                return self._handle_meeting_id_excuse_request(user, channel_id, user_id, first_part, reason)
                
        except Exception as e:
            return self._send_ephemeral_message(channel_id, user_id, f"❌ Error requesting excuse: {str(e)}")
    
    def _handle_meeting_id_excuse_request(self, user, channel_id, user_id, meeting_id_str, reason):
        """Handle excuse request by meeting ID"""
        try:
            meeting_id = int(meeting_id_str)
            
            # Check if meeting exists
            meeting = MeetingHour.query.get(meeting_id)
            if not meeting:
                return self._send_ephemeral_message(channel_id, user_id, f"❌ Meeting with ID {meeting_id} not found.")
            
            # Check if it's an outreach event (cannot be excused)
            if meeting.meeting_type == 'outreach':
                return self._send_ephemeral_message(channel_id, user_id, f"❌ Outreach events cannot be excused. All outreach hours count toward your total.")
            
            # Check if already has pending request
            existing_request = ExcuseRequest.query.filter_by(
                user_id=user.id,
                meeting_hour_id=meeting_id,
                status='pending'
            ).first()
            
            if existing_request:
                return self._send_ephemeral_message(channel_id, user_id, f"❌ You already have a pending excuse request for: {meeting.description}")
            
            # Check if already excused
            existing_excuse = Excuse.query.filter_by(
                user_id=user.id,
                meeting_hour_id=meeting_id
            ).first()
            
            if existing_excuse:
                return self._send_ephemeral_message(channel_id, user_id, f"❌ You are already excused from: {meeting.description}")
            
            # Create excuse request
            excuse_request = ExcuseRequest(
                user_id=user.id,
                meeting_hour_id=meeting_id,
                reason=reason
            )
            
            db.session.add(excuse_request)
            db.session.commit()
            
            return self._send_ephemeral_message(channel_id, user_id, f"✅ Excuse request submitted for: {meeting.description}\n📅 Date: {meeting.start_time.strftime('%Y-%m-%d %H:%M')}\n📝 Reason: {reason}\n\nAn admin will review your request.")
            
        except ValueError:
            return self._send_ephemeral_message(channel_id, user_id, "❌ Invalid meeting ID. Must be a number.")
    
    def _handle_date_based_excuse_request(self, user, channel_id, user_id, meeting_date, reason):
        """Handle excuse request by date"""
        try:
            # Find meetings on the specified date
            meetings = MeetingHour.query.filter(
                db.func.date(MeetingHour.start_time) == meeting_date.date()
            ).all()
            
            if not meetings:
                return self._send_ephemeral_message(channel_id, user_id, f"❌ No meetings found on {meeting_date.strftime('%Y-%m-%d')}. Please check the date or contact an admin.")
            
            # If multiple meetings on the same date, show options
            if len(meetings) > 1:
                meeting_list = "\n".join([f"{i+1}. {m.description} ({m.start_time.strftime('%H:%M')}-{m.end_time.strftime('%H:%M')})" for i, m in enumerate(meetings)])
                return self._send_ephemeral_message(channel_id, user_id, f"❌ Multiple meetings found on {meeting_date.strftime('%Y-%m-%d')}:\n{meeting_list}\n\nPlease use `/request_excuse meeting_id reason` for specific meetings.")
            
            meeting = meetings[0]
            
            # Check if it's an outreach event (cannot be excused)
            if meeting.meeting_type == 'outreach':
                return self._send_ephemeral_message(channel_id, user_id, f"❌ Outreach events cannot be excused. All outreach hours count toward your total.")
            
            # Check if already has pending request
            existing_request = ExcuseRequest.query.filter_by(
                user_id=user.id,
                meeting_hour_id=meeting.id,
                status='pending'
            ).first()
            
            if existing_request:
                return self._send_ephemeral_message(channel_id, user_id, f"❌ You already have a pending excuse request for: {meeting.description}")
            
            # Check if already excused
            existing_excuse = Excuse.query.filter_by(
                user_id=user.id,
                meeting_hour_id=meeting.id
            ).first()
            
            if existing_excuse:
                return self._send_ephemeral_message(channel_id, user_id, f"❌ You are already excused from: {meeting.description}")
            
            # Create excuse request
            excuse_request = ExcuseRequest(
                user_id=user.id,
                meeting_hour_id=meeting.id,
                reason=reason
            )
            
            db.session.add(excuse_request)
            db.session.commit()
            
            return self._send_ephemeral_message(channel_id, user_id, f"✅ Excuse request submitted for: {meeting.description}\n📅 Date: {meeting.start_time.strftime('%Y-%m-%d %H:%M')}\n📝 Reason: {reason}\n\nAn admin will review your request.")
            
        except Exception as e:
            return self._send_ephemeral_message(channel_id, user_id, f"❌ Error requesting excuse: {str(e)}")
    
    def _handle_help(self, user, channel_id, user_id):
        """Handle help command"""
        message = "🤖 *Attendance Bot Commands*\n\n"
        
        if user.is_admin:
            message += "*Admin Commands:*\n"
            message += "`/add_meeting YYYY-MM-DD HH:MM-HH:MM Description` - Add a regular meeting\n"
            message += "`/add_outreach YYYY-MM-DD HH:MM-HH:MM Description` - Add an outreach event\n"
            message += "`/create_period name YYYY-MM-DD YYYY-MM-DD` - Create reporting period\n"
            message += "`/excuse user_id meeting_id reason` - Excuse user from meeting\n\n"
        
        message += "*User Commands:*\n"
        message += "`/log_attendance meeting_id [notes]` - Log full regular meeting attendance\n"
        message += "`/log_attendance YYYY-MM-DD HH:MM-HH:MM [notes]` - Log attendance by time range\n"
        message += "`/log_outreach outreach_id [notes]` - Log full outreach attendance\n"
        message += "`/log_outreach YYYY-MM-DD HH:MM-HH:MM [notes]` - Log outreach by time range\n"
        message += "`/request_excuse meeting_id reason` - Request excuse for a meeting\n"
        message += "`/request_excuse YYYY-MM-DD reason` - Request excuse by date\n"
        message += "`/my_attendance` - View your attendance and outreach hours\n"
        message += "`/help` - Show this help\n\n"
        message += "*Requirements:*\n"
        message += "• Regular Meetings: 60% (team) / 75% (travel)\n"
        message += "• Outreach Hours: 12h (team) / 18h (travel)\n\n"
        message += "Use the web app for detailed reports and management."
        
        return self._send_ephemeral_message(channel_id, user_id, message)
    
    def _send_message(self, channel_id, text):
        """Send a message to Slack channel"""
        try:
            response = self.client.chat_postMessage(
                channel=channel_id,
                text=text
            )
            return response
        except SlackApiError as e:
            logger.error(f"Error sending message: {e.response['error']}")
            return None
    
    def _send_ephemeral_message(self, channel_id, user_id, text):
        """Send an ephemeral message (only visible to the user who triggered the command)"""
        try:
            response = self.client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text=text
            )
            return response
        except SlackApiError as e:
            logger.error(f"Error sending ephemeral message: {e.response['error']}")
            return None
    
    def _send_private_response(self, channel_id, user_id, text):
        """Send a private response (ephemeral message) - wrapper for consistency"""
        return self._send_ephemeral_message(channel_id, user_id, text)
    
    def get_upcoming_meetings(self, days=7):
        """Get upcoming meetings for the next N days"""
        with self.app.app_context():
            end_date = datetime.utcnow() + timedelta(days=days)
            meetings = MeetingHour.query.filter(
                MeetingHour.start_time >= datetime.utcnow(),
                MeetingHour.start_time <= end_date
            ).order_by(MeetingHour.start_time).all()
            
            return meetings
