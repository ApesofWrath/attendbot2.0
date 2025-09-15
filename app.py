from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv
import os
import json
import csv
import io
from google_auth import get_flow, get_user_info, get_slack_user_info

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///attendance.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configure proxy settings for HTTPS behind nginx
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slack_user_id = db.Column(db.String(50), unique=True, nullable=True)
    google_id = db.Column(db.String(100), unique=True, nullable=True)
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    attendance_logs = db.relationship('AttendanceLog', backref='user', lazy=True)

class MeetingHour(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    description = db.Column(db.String(200), nullable=True)
    meeting_type = db.Column(db.String(20), nullable=False, default='regular')  # 'regular' or 'outreach'
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    attendance_logs = db.relationship('AttendanceLog', backref='meeting_hour', lazy=True)
    excuses = db.relationship('Excuse', backref='meeting_hour', lazy=True)

class AttendanceLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    meeting_hour_id = db.Column(db.Integer, db.ForeignKey('meeting_hour.id'), nullable=False)
    logged_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.String(500), nullable=True)
    # Attendance fields - now always required
    partial_hours = db.Column(db.Float, nullable=True)  # Hours actually attended (can be null for full attendance)
    is_partial = db.Column(db.Boolean, default=False)  # Whether this is partial attendance

class ReportingPeriod(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    excuses = db.relationship('Excuse', backref='reporting_period', lazy=True)

class ExcuseRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    meeting_hour_id = db.Column(db.Integer, db.ForeignKey('meeting_hour.id'), nullable=False)
    reason = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, approved, denied
    requested_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    admin_notes = db.Column(db.String(500), nullable=True)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='excuse_requests')
    meeting_hour = db.relationship('MeetingHour', backref='excuse_requests')
    reviewer = db.relationship('User', foreign_keys=[reviewed_by], backref='reviewed_excuses')

class Excuse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    meeting_hour_id = db.Column(db.Integer, db.ForeignKey('meeting_hour.id'), nullable=False)
    reporting_period_id = db.Column(db.Integer, db.ForeignKey('reporting_period.id'), nullable=False)
    reason = db.Column(db.String(500), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    excuse_request_id = db.Column(db.Integer, db.ForeignKey('excuse_request.id'), nullable=True)
    
    # Relationships with explicit foreign keys
    user = db.relationship('User', foreign_keys=[user_id], backref='excuses')
    created_by_user = db.relationship('User', foreign_keys=[created_by], backref='created_excuses')
    excuse_request = db.relationship('ExcuseRequest', backref='excuse')

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login')
def login():
    """Initiate Google OAuth login"""
    flow = get_flow()
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    session['state'] = state
    return redirect(authorization_url)

@app.route('/auth/google/callback')
def google_callback():
    """Handle Google OAuth callback"""
    try:
        print(f"OAuth callback received: {request.url}")
        flow = get_flow()
        print("Flow created successfully")
        
        flow.fetch_token(authorization_response=request.url)
        print("Token fetched successfully")
        
        credentials = flow.credentials
        user_info = get_user_info(credentials)
        print(f"User info: {user_info}")
        
        if not user_info:
            flash('Failed to get user information from Google.')
            return redirect(url_for('index'))
        
        # Check if user exists by Google ID
        user = User.query.filter_by(google_id=user_info['id']).first()
        
        if not user:
            # Check if user exists by email (for existing Slack users)
            user = User.query.filter_by(email=user_info['email']).first()
            
            if user:
                # Link Google account to existing user
                user.google_id = user_info['id']
                user.last_login = datetime.utcnow()
                db.session.commit()
                flash('Your Google account has been linked to your existing profile.')
            else:
                # Create new user
                user = User(
                    google_id=user_info['id'],
                    email=user_info['email'],
                    username=user_info.get('name', user_info['email'].split('@')[0]),
                    last_login=datetime.utcnow()
                )
                db.session.add(user)
                db.session.commit()
                flash('Welcome! Your account has been created.')
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        login_user(user)
        print(f"User logged in successfully: {user.username}")
        return redirect(url_for('dashboard'))
        
    except Exception as e:
        print(f"OAuth error: {e}")
        import traceback
        traceback.print_exc()
        flash('Authentication failed. Please try again.')
        return redirect(url_for('index'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Get current reporting period
    current_period = ReportingPeriod.query.filter(
        ReportingPeriod.start_date <= datetime.utcnow(),
        ReportingPeriod.end_date >= datetime.utcnow()
    ).first()
    
    # Get user's attendance data
    user_attendance = get_user_attendance_data(current_user.id, current_period.id if current_period else None)
    
    return render_template('dashboard.html', 
                         current_period=current_period,
                         user_attendance=user_attendance)

@app.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('dashboard'))
    
    periods = ReportingPeriod.query.order_by(ReportingPeriod.start_date.desc()).all()
    users = User.query.order_by(User.created_at.desc()).all()
    now = datetime.utcnow()
    return render_template('admin_dashboard.html', periods=periods, users=users, now=now)

@app.route('/admin/period/<int:period_id>/delete', methods=['POST'])
@login_required
def delete_period(period_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('admin_dashboard'))
    
    period = ReportingPeriod.query.get_or_404(period_id)
    
    try:
        # Get all meetings within this reporting period's date range
        meetings_in_period = MeetingHour.query.filter(
            MeetingHour.start_time >= period.start_date,
            MeetingHour.start_time <= period.end_date
        ).all()
        
        # Delete all attendance logs for meetings in this period
        meeting_ids = [m.id for m in meetings_in_period]
        if meeting_ids:
            AttendanceLog.query.filter(
                AttendanceLog.meeting_hour_id.in_(meeting_ids)
            ).delete(synchronize_session=False)
        
        # Delete all excuse requests for meetings in this period
        if meeting_ids:
            ExcuseRequest.query.filter(
                ExcuseRequest.meeting_hour_id.in_(meeting_ids)
            ).delete(synchronize_session=False)
        
        # Delete all excuses for meetings in this period
        if meeting_ids:
            Excuse.query.filter(
                Excuse.meeting_hour_id.in_(meeting_ids)
            ).delete(synchronize_session=False)
        
        # Delete all excuses that reference this reporting period directly
        Excuse.query.filter(
            Excuse.reporting_period_id == period_id
        ).delete(synchronize_session=False)
        
        # Delete all meetings in this period
        for meeting in meetings_in_period:
            db.session.delete(meeting)
        
        # Finally, delete the reporting period itself
        db.session.delete(period)
        db.session.commit()
        
        flash(f'Reporting period "{period.name}" and all associated meetings, attendance logs, and excuses have been deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting reporting period: {str(e)}', 'error')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add_meeting', methods=['POST'])
@login_required
def add_meeting_admin():
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied. Admin privileges required.'}), 403
    
    try:
        data = request.get_json()
        date_str = data.get('date')
        start_time_str = data.get('start_time')
        end_time_str = data.get('end_time')
        description = data.get('description', '')
        
        if not all([date_str, start_time_str, end_time_str]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Parse date and time
        start_time = datetime.strptime(f"{date_str} {start_time_str}", "%Y-%m-%d %H:%M")
        end_time = datetime.strptime(f"{date_str} {end_time_str}", "%Y-%m-%d %H:%M")
        
        # Create meeting hour
        meeting_hour = MeetingHour(
            start_time=start_time,
            end_time=end_time,
            description=description,
            meeting_type='regular',
            created_by=current_user.id
        )
        
        db.session.add(meeting_hour)
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'Meeting added: {description} on {date_str} from {start_time_str} to {end_time_str}'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error adding meeting: {str(e)}'}), 500

@app.route('/admin/add_outreach', methods=['POST'])
@login_required
def add_outreach_admin():
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied. Admin privileges required.'}), 403
    
    try:
        data = request.get_json()
        date_str = data.get('date')
        start_time_str = data.get('start_time')
        end_time_str = data.get('end_time')
        description = data.get('description', '')
        
        if not all([date_str, start_time_str, end_time_str]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Parse date and time
        start_time = datetime.strptime(f"{date_str} {start_time_str}", "%Y-%m-%d %H:%M")
        end_time = datetime.strptime(f"{date_str} {end_time_str}", "%Y-%m-%d %H:%M")
        
        # Create outreach event
        outreach_event = MeetingHour(
            start_time=start_time,
            end_time=end_time,
            description=description,
            meeting_type='outreach',
            created_by=current_user.id
        )
        
        db.session.add(outreach_event)
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'Outreach event added: {description} on {date_str} from {start_time_str} to {end_time_str}'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error adding outreach event: {str(e)}'}), 500

@app.route('/admin/create_period', methods=['POST'])
@login_required
def create_period_admin():
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied. Admin privileges required.'}), 403
    
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        
        if not all([name, start_date_str, end_date_str]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Parse dates
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
        
        # Create reporting period
        period = ReportingPeriod(
            name=name,
            start_date=start_date,
            end_date=end_date,
            created_by=current_user.id
        )
        
        db.session.add(period)
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'Reporting period created: {name} ({start_date_str} to {end_date_str})'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error creating period: {str(e)}'}), 500

@app.route('/admin/users')
@login_required
def admin_users():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('dashboard'))
    
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin_users.html', users=users)

@app.route('/admin/users/<int:user_id>/toggle_admin', methods=['POST'])
@login_required
def toggle_admin(user_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        return jsonify({'error': 'Cannot modify your own admin status'}), 400
    
    user.is_admin = not user.is_admin
    db.session.commit()
    
    return jsonify({
        'success': True,
        'is_admin': user.is_admin,
        'message': f'User {user.username} {"promoted to" if user.is_admin else "removed from"} admin'
    })

@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@login_required
def delete_user(user_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        return jsonify({'error': 'Cannot delete your own account'}), 400
    
    # Delete related data
    AttendanceLog.query.filter_by(user_id=user_id).delete()
    Excuse.query.filter_by(user_id=user_id).delete()
    
    db.session.delete(user)
    db.session.commit()
    
    return jsonify({'success': True, 'message': f'User {user.username} deleted'})

@app.route('/admin/users/<int:user_id>/edit', methods=['POST'])
@login_required
def edit_user(user_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        user = User.query.get_or_404(user_id)
        data = request.get_json()
        
        # Get form data
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        slack_user_id = data.get('slack_user_id', '').strip()
        google_id = data.get('google_id', '').strip()
        
        # Validate required fields
        if not username or not email:
            return jsonify({'error': 'Username and email are required'}), 400
        
        # Check for duplicate username (excluding current user)
        existing_user = User.query.filter(
            User.username == username,
            User.id != user_id
        ).first()
        if existing_user:
            return jsonify({'error': 'Username already exists'}), 400
        
        # Check for duplicate email (excluding current user)
        existing_email = User.query.filter(
            User.email == email,
            User.id != user_id
        ).first()
        if existing_email:
            return jsonify({'error': 'Email already exists'}), 400
        
        # Check for duplicate Slack ID (excluding current user)
        if slack_user_id:
            existing_slack = User.query.filter(
                User.slack_user_id == slack_user_id,
                User.id != user_id
            ).first()
            if existing_slack:
                return jsonify({'error': 'Slack ID already exists'}), 400
        
        # Check for duplicate Google ID (excluding current user)
        if google_id:
            existing_google = User.query.filter(
                User.google_id == google_id,
                User.id != user_id
            ).first()
            if existing_google:
                return jsonify({'error': 'Google ID already exists'}), 400
        
        # Update user data
        old_username = user.username
        user.username = username
        user.email = email
        user.slack_user_id = slack_user_id if slack_user_id else None
        user.google_id = google_id if google_id else None
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'User profile updated successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'slack_user_id': user.slack_user_id,
                'google_id': user.google_id,
                'is_admin': user.is_admin,
                'created_at': user.created_at.isoformat(),
                'last_login': user.last_login.isoformat() if user.last_login else None
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error updating user profile: {str(e)}'}), 500

@app.route('/admin/users/<int:user_id>/attendance')
@login_required
def user_attendance_report(user_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('admin_users'))
    
    user = User.query.get_or_404(user_id)
    
    # Get all attendance logs for this user, ordered by meeting date
    attendance_logs = db.session.query(AttendanceLog, MeetingHour).join(
        MeetingHour, AttendanceLog.meeting_hour_id == MeetingHour.id
    ).filter(
        AttendanceLog.user_id == user_id
    ).order_by(MeetingHour.start_time.desc()).all()
    
    # Separate regular meetings and outreach
    regular_attendance = []
    outreach_attendance = []
    
    for log, meeting in attendance_logs:
        # Calculate hours attended
        if log.partial_hours is not None:
            hours_attended = log.partial_hours
        else:
            hours_attended = (meeting.end_time - meeting.start_time).total_seconds() / 3600
        
        # Calculate total meeting hours
        total_hours = (meeting.end_time - meeting.start_time).total_seconds() / 3600
        
        attendance_data = {
            'log': log,
            'meeting': meeting,
            'hours_attended': round(hours_attended, 2),
            'total_hours': round(total_hours, 2),
            'attendance_percentage': round((hours_attended / total_hours * 100) if total_hours > 0 else 0, 1),
            'is_partial': log.is_partial,
            'notes': log.notes
        }
        
        if meeting.meeting_type == 'regular':
            regular_attendance.append(attendance_data)
        else:
            outreach_attendance.append(attendance_data)
    
    # Get user's excuses
    excuses = db.session.query(Excuse, MeetingHour).join(
        MeetingHour, Excuse.meeting_hour_id == MeetingHour.id
    ).filter(
        Excuse.user_id == user_id
    ).order_by(MeetingHour.start_time.desc()).all()
    
    # Separate regular and outreach excuses
    regular_excuses = []
    outreach_excuses = []
    
    for excuse, meeting in excuses:
        excuse_data = {
            'excuse': excuse,
            'meeting': meeting,
            'total_hours': round((meeting.end_time - meeting.start_time).total_seconds() / 3600, 2)
        }
        
        if meeting.meeting_type == 'regular':
            regular_excuses.append(excuse_data)
        else:
            outreach_excuses.append(excuse_data)
    
    # Calculate summary statistics
    total_regular_hours = sum(item['total_hours'] for item in regular_attendance)
    attended_regular_hours = sum(item['hours_attended'] for item in regular_attendance)
    excused_regular_hours = sum(item['total_hours'] for item in regular_excuses)
    effective_regular_hours = total_regular_hours - excused_regular_hours
    regular_percentage = (attended_regular_hours / effective_regular_hours * 100) if effective_regular_hours > 0 else 0
    
    total_outreach_hours = sum(item['total_hours'] for item in outreach_attendance)
    attended_outreach_hours = sum(item['hours_attended'] for item in outreach_attendance)
    outreach_percentage = (attended_outreach_hours / total_outreach_hours * 100) if total_outreach_hours > 0 else 0
    
    return render_template('user_attendance_report.html',
                         user=user,
                         regular_attendance=regular_attendance,
                         outreach_attendance=outreach_attendance,
                         regular_excuses=regular_excuses,
                         outreach_excuses=outreach_excuses,
                         total_regular_hours=round(total_regular_hours, 2),
                         attended_regular_hours=round(attended_regular_hours, 2),
                         excused_regular_hours=round(excused_regular_hours, 2),
                         effective_regular_hours=round(effective_regular_hours, 2),
                         regular_percentage=round(regular_percentage, 1),
                         total_outreach_hours=round(total_outreach_hours, 2),
                         attended_outreach_hours=round(attended_outreach_hours, 2),
                         outreach_percentage=round(outreach_percentage, 1))

@app.route('/admin/users/combine', methods=['POST'])
@login_required
def combine_users():
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        data = request.get_json()
        primary_user_id = data.get('primary_user_id')
        secondary_user_id = data.get('secondary_user_id')
        
        if not primary_user_id or not secondary_user_id:
            return jsonify({'error': 'Both primary and secondary user IDs are required'}), 400
        
        if primary_user_id == secondary_user_id:
            return jsonify({'error': 'Cannot combine a user with themselves'}), 400
        
        # Get users
        primary_user = User.query.get(primary_user_id)
        secondary_user = User.query.get(secondary_user_id)
        
        if not primary_user or not secondary_user:
            return jsonify({'error': 'One or both users not found'}), 404
        
        # Prevent combining with current user
        if secondary_user.id == current_user.id:
            return jsonify({'error': 'Cannot combine with your own account'}), 400
        
        # Combine user data
        result = combine_user_data(primary_user, secondary_user)
        
        if result['error']:
            return jsonify({'error': result['error']}), 400
        
        return jsonify({
            'success': True, 
            'message': f'Successfully combined {secondary_user.username} into {primary_user.username}',
            'details': result['details']
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error combining users: {str(e)}'}), 500

def combine_user_data(primary_user, secondary_user):
    """
    Combine secondary user data into primary user and delete secondary user.
    
    Args:
        primary_user: User object to keep
        secondary_user: User object to merge and delete
    
    Returns:
        dict with success status and details
    """
    try:
        details = []
        
        # Update primary user with data from secondary user if missing
        updated_fields = []
        
        if not primary_user.slack_user_id and secondary_user.slack_user_id:
            primary_user.slack_user_id = secondary_user.slack_user_id
            updated_fields.append('Slack ID')
        
        if not primary_user.google_id and secondary_user.google_id:
            primary_user.google_id = secondary_user.google_id
            updated_fields.append('Google ID')
        
        # Keep the most recent last_login
        if secondary_user.last_login and (not primary_user.last_login or secondary_user.last_login > primary_user.last_login):
            primary_user.last_login = secondary_user.last_login
            updated_fields.append('Last Login')
        
        if updated_fields:
            details.append(f"Updated primary user with: {', '.join(updated_fields)}")
        
        # Transfer attendance logs
        attendance_logs = AttendanceLog.query.filter_by(user_id=secondary_user.id).all()
        for log in attendance_logs:
            log.user_id = primary_user.id
        details.append(f"Transferred {len(attendance_logs)} attendance logs")
        
        # Transfer excuses
        excuses = Excuse.query.filter_by(user_id=secondary_user.id).all()
        for excuse in excuses:
            excuse.user_id = primary_user.id
        details.append(f"Transferred {len(excuses)} excuses")
        
        # Transfer excuse requests (both as user and reviewer)
        user_excuse_requests = ExcuseRequest.query.filter_by(user_id=secondary_user.id).all()
        for request in user_excuse_requests:
            request.user_id = primary_user.id
        details.append(f"Transferred {len(user_excuse_requests)} excuse requests (as user)")
        
        reviewer_excuse_requests = ExcuseRequest.query.filter_by(reviewed_by=secondary_user.id).all()
        for request in reviewer_excuse_requests:
            request.reviewed_by = primary_user.id
        details.append(f"Transferred {len(reviewer_excuse_requests)} excuse requests (as reviewer)")
        
        # Transfer created excuses
        created_excuses = Excuse.query.filter_by(created_by=secondary_user.id).all()
        for excuse in created_excuses:
            excuse.created_by = primary_user.id
        details.append(f"Transferred {len(created_excuses)} created excuses")
        
        # Transfer created meetings
        created_meetings = MeetingHour.query.filter_by(created_by=secondary_user.id).all()
        for meeting in created_meetings:
            meeting.created_by = primary_user.id
        details.append(f"Transferred {len(created_meetings)} created meetings")
        
        # Transfer created reporting periods
        created_periods = ReportingPeriod.query.filter_by(created_by=secondary_user.id).all()
        for period in created_periods:
            period.created_by = primary_user.id
        details.append(f"Transferred {len(created_periods)} created reporting periods")
        
        # Delete secondary user
        db.session.delete(secondary_user)
        
        # Commit all changes
        db.session.commit()
        
        details.append(f"Deleted secondary user: {secondary_user.username}")
        
        return {
            'error': None,
            'details': details
        }
        
    except Exception as e:
        db.session.rollback()
        return {
            'error': f'Error combining users: {str(e)}',
            'details': []
        }

@app.route('/reports/<int:period_id>')
@login_required
def attendance_report(period_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('dashboard'))
    
    period = ReportingPeriod.query.get_or_404(period_id)
    report_data = get_attendance_report_data(period_id)
    
    # Get meetings data for the meeting tab
    meetings_data = get_meetings_data_for_period(period_id)
    
    return render_template('attendance_report.html', 
                         period=period,
                         report_data=report_data,
                         meetings_data=meetings_data)

@app.route('/reports/<int:period_id>/meeting/<int:meeting_id>')
@login_required
def meeting_detail(period_id, meeting_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('dashboard'))
    
    period = ReportingPeriod.query.get_or_404(period_id)
    meeting = MeetingHour.query.get_or_404(meeting_id)
    
    # Get detailed attendance data for this meeting
    attendance_data = get_meeting_attendance_detail(meeting_id)
    
    return render_template('meeting_detail.html',
                         period=period,
                         meeting=meeting,
                         attendance_data=attendance_data)

@app.route('/api/attendance', methods=['POST'])
@login_required
def log_attendance():
    data = request.get_json()
    meeting_hour_id = data.get('meeting_hour_id')
    notes = data.get('notes', '')
    hours_attended = data.get('hours_attended')
    
    # Check if meeting hour exists and is valid
    meeting_hour = MeetingHour.query.get(meeting_hour_id)
    if not meeting_hour:
        return jsonify({'error': 'Meeting hour not found'}), 404
    
    # Check if user already logged attendance for this meeting
    existing_log = AttendanceLog.query.filter_by(
        user_id=current_user.id,
        meeting_hour_id=meeting_hour_id
    ).first()
    
    if existing_log:
        return jsonify({'error': 'Attendance already logged for this meeting'}), 400
    
    # Validate hours_attended
    if hours_attended is None:
        return jsonify({'error': 'Hours attended is required'}), 400
    
    try:
        hours_attended = float(hours_attended)
        if hours_attended <= 0:
            return jsonify({'error': 'Hours attended must be greater than 0'}), 400
        
        # Calculate total meeting hours
        total_meeting_hours = (meeting_hour.end_time - meeting_hour.start_time).total_seconds() / 3600
        if hours_attended > total_meeting_hours:
            return jsonify({'error': f'Hours attended ({hours_attended}) cannot exceed total meeting hours ({total_meeting_hours:.2f})'}), 400
            
    except (ValueError, TypeError):
        return jsonify({'error': 'Hours attended must be a valid number'}), 400
    
    # Determine if this is partial attendance
    is_partial = hours_attended < total_meeting_hours
    
    # Create attendance log
    attendance_log = AttendanceLog(
        user_id=current_user.id,
        meeting_hour_id=meeting_hour_id,
        notes=notes,
        is_partial=is_partial,
        partial_hours=hours_attended if is_partial else None
    )
    
    db.session.add(attendance_log)
    db.session.commit()
    
    return jsonify({'message': 'Attendance logged successfully'})

# Helper functions
def get_user_attendance_data(user_id, period_id):
    """Calculate user's attendance data for a given period"""
    if not period_id:
        return None
    
    period = ReportingPeriod.query.get(period_id)
    if not period:
        return None
    
    # Get all meeting hours in the period, separated by type
    all_meeting_hours = MeetingHour.query.filter(
        MeetingHour.start_time >= period.start_date,
        MeetingHour.start_time <= period.end_date
    ).all()
    
    regular_meetings = [m for m in all_meeting_hours if m.meeting_type == 'regular']
    outreach_meetings = [m for m in all_meeting_hours if m.meeting_type == 'outreach']
    
    # Get user's attendance logs
    attendance_logs = AttendanceLog.query.filter_by(user_id=user_id).join(MeetingHour).filter(
        MeetingHour.start_time >= period.start_date,
        MeetingHour.start_time <= period.end_date
    ).all()
    
    # Get user's excuses
    excuses = Excuse.query.filter_by(user_id=user_id, reporting_period_id=period_id).all()
    excused_meeting_ids = [excuse.meeting_hour_id for excuse in excuses]
    
    # Separate attendance by type
    regular_attended = [log for log in attendance_logs if log.meeting_hour.meeting_type == 'regular']
    outreach_attended = [log for log in attendance_logs if log.meeting_hour.meeting_type == 'outreach']
    
    # Separate excuses by type - only regular meetings can be excused
    regular_excused = [excuse for excuse in excuses if excuse.meeting_hour.meeting_type == 'regular']
    # outreach_excused = [] # Outreach hours cannot be excused
    
    # Calculate regular meeting metrics - now based on hours
    total_regular_hours = sum((m.end_time - m.start_time).total_seconds() / 3600 for m in regular_meetings)
    # Use partial_hours if available (for CSV imports), otherwise fall back to meeting duration
    attended_regular_hours = sum(log.partial_hours if log.partial_hours is not None else (log.meeting_hour.end_time - log.meeting_hour.start_time).total_seconds() / 3600 for log in regular_attended)
    
    # Calculate excused hours for regular meetings
    excused_regular_hours = 0
    for excuse in regular_excused:
        excused_regular_hours += (excuse.meeting_hour.end_time - excuse.meeting_hour.start_time).total_seconds() / 3600
    
    effective_regular_total_hours = total_regular_hours - excused_regular_hours
    effective_regular_attended_hours = attended_regular_hours
    
    regular_attendance_percentage = (effective_regular_attended_hours / effective_regular_total_hours * 100) if effective_regular_total_hours > 0 else 0
    
    # Calculate outreach hours
    total_outreach_hours = sum((m.end_time - m.start_time).total_seconds() / 3600 for m in outreach_meetings)
    
    # Calculate attended outreach hours
    # Use partial_hours if available (for CSV imports), otherwise fall back to meeting duration
    attended_outreach_hours = sum(log.partial_hours if log.partial_hours is not None else (log.meeting_hour.end_time - log.meeting_hour.start_time).total_seconds() / 3600 for log in outreach_attended)
    
    # Outreach hours cannot be excused - all hours count toward total
    excused_outreach_hours = 0  # No outreach hours can be excused
    effective_outreach_hours = total_outreach_hours  # All outreach hours count
    effective_attended_outreach_hours = attended_outreach_hours
    
    # Calculate overall metrics - now based on hours
    total_hours = total_regular_hours + total_outreach_hours
    attended_hours = attended_regular_hours + attended_outreach_hours
    excused_hours = excused_regular_hours  # Only regular meetings can be excused
    effective_total_hours = total_hours - excused_hours
    effective_attended_hours = attended_hours
    attendance_percentage = (effective_attended_hours / effective_total_hours * 100) if effective_total_hours > 0 else 0
    
    return {
        # Overall metrics - now hour-based
        'total_hours': round(total_hours, 2),
        'attended_hours': round(attended_hours, 2),
        'excused_hours': round(excused_hours, 2),
        'effective_total_hours': round(effective_total_hours, 2),
        'effective_attended_hours': round(effective_attended_hours, 2),
        'attendance_percentage': round(attendance_percentage, 2),
        'meets_team_requirement': regular_attendance_percentage >= 60,
        'meets_travel_requirement': regular_attendance_percentage >= 75,
        
        # Regular meeting metrics - now hour-based
        'regular_meetings': {
            'total_hours': round(total_regular_hours, 2),
            'attended_hours': round(attended_regular_hours, 2),
            'excused_hours': round(excused_regular_hours, 2),
            'effective_total_hours': round(effective_regular_total_hours, 2),
            'effective_attended_hours': round(effective_regular_attended_hours, 2),
            'attendance_percentage': round(regular_attendance_percentage, 2),
            'meets_team_requirement': regular_attendance_percentage >= 60,
            'meets_travel_requirement': regular_attendance_percentage >= 75
        },
        
        # Outreach metrics
        'outreach_hours': {
            'total_hours': round(total_outreach_hours, 2),
            'attended_hours': round(attended_outreach_hours, 2),
            'excused_hours': round(excused_outreach_hours, 2),
            'effective_total_hours': round(effective_outreach_hours, 2),
            'effective_attended_hours': round(effective_attended_outreach_hours, 2),
            'meets_team_requirement': effective_attended_outreach_hours >= 12,
            'meets_travel_requirement': effective_attended_outreach_hours >= 18
        }
    }

def get_attendance_report_data(period_id):
    """Get attendance report data for all users in a period who have >0 hours attended"""
    period = ReportingPeriod.query.get(period_id)
    if not period:
        return []
    
    users = User.query.all()
    report_data = []
    
    for user in users:
        user_data = get_user_attendance_data(user.id, period_id)
        if user_data and user_data['attended_hours'] > 0:
            user_data['user'] = user
            report_data.append(user_data)
    
    return sorted(report_data, key=lambda x: x['attendance_percentage'], reverse=True)

def get_meetings_data_for_period(period_id):
    """Get meetings data for a period with attendance summaries"""
    period = ReportingPeriod.query.get(period_id)
    if not period:
        return []
    
    # Get all meetings in the period
    meetings = MeetingHour.query.filter(
        MeetingHour.start_time >= period.start_date,
        MeetingHour.start_time <= period.end_date
    ).order_by(MeetingHour.start_time.desc()).all()
    
    meetings_data = []
    for meeting in meetings:
        # Get attendance logs for this meeting
        attendance_logs = AttendanceLog.query.filter_by(meeting_hour_id=meeting.id).all()
        
        # Calculate attendance statistics
        total_attended_hours = sum(
            log.partial_hours if log.partial_hours is not None 
            else (meeting.end_time - meeting.start_time).total_seconds() / 3600
            for log in attendance_logs
        )
        
        total_meeting_hours = (meeting.end_time - meeting.start_time).total_seconds() / 3600
        attendance_count = len(attendance_logs)
        
        # Get excuses for this meeting
        excuses = Excuse.query.filter_by(meeting_hour_id=meeting.id).all()
        excused_count = len(excuses)
        
        meetings_data.append({
            'meeting': meeting,
            'attendance_count': attendance_count,
            'excused_count': excused_count,
            'total_attended_hours': round(total_attended_hours, 2),
            'total_meeting_hours': round(total_meeting_hours, 2),
            'attendance_percentage': round((total_attended_hours / total_meeting_hours * 100) if total_meeting_hours > 0 else 0, 1)
        })
    
    return meetings_data

def get_meeting_attendance_detail(meeting_id):
    """Get detailed attendance data for a specific meeting"""
    meeting = MeetingHour.query.get(meeting_id)
    if not meeting:
        return None
    
    # Get all attendance logs for this meeting
    attendance_logs = db.session.query(AttendanceLog, User).join(
        User, AttendanceLog.user_id == User.id
    ).filter(
        AttendanceLog.meeting_hour_id == meeting_id
    ).order_by(AttendanceLog.logged_at).all()
    
    # Get excuses for this meeting
    excuses = db.session.query(Excuse, User).join(
        User, Excuse.user_id == User.id
    ).filter(
        Excuse.meeting_hour_id == meeting_id
    ).all()
    
    # Process attendance data
    attendance_data = []
    for log, user in attendance_logs:
        hours_attended = log.partial_hours if log.partial_hours is not None else (meeting.end_time - meeting.start_time).total_seconds() / 3600
        total_hours = (meeting.end_time - meeting.start_time).total_seconds() / 3600
        
        attendance_data.append({
            'log': log,
            'user': user,
            'hours_attended': round(hours_attended, 2),
            'total_hours': round(total_hours, 2),
            'attendance_percentage': round((hours_attended / total_hours * 100) if total_hours > 0 else 0, 1),
            'is_partial': log.is_partial,
            'notes': log.notes
        })
    
    # Process excuse data
    excuse_data = []
    for excuse, user in excuses:
        excuse_data.append({
            'excuse': excuse,
            'user': user,
            'reason': excuse.reason,
            'created_at': excuse.created_at
        })
    
    return {
        'attendance': attendance_data,
        'excuses': excuse_data,
        'total_attended_hours': sum(item['hours_attended'] for item in attendance_data),
        'total_meeting_hours': round((meeting.end_time - meeting.start_time).total_seconds() / 3600, 2),
        'attendance_count': len(attendance_data),
        'excused_count': len(excuse_data)
    }

def guess_date_for_outreach_row(rows, current_row_idx, data_start_row):
    """
    For outreach imports, guess a date for a row that doesn't have a date
    by finding the nearest dates above and below and interpolating.
    """
    # Look for dates in rows above
    above_date = None
    for i in range(current_row_idx - 1, data_start_row - 1, -1):
        if i < len(rows):
            row = rows[i]
            if len(row) >= 1 and row[0]:
                first_column = row[0].strip()
                if first_column and any(char.isdigit() for char in first_column):
                    # Try to extract date
                    import re
                    date_patterns = [
                        r'(\d{1,2}/\d{1,2}/\d{2,4})',  # MM/DD/YYYY or MM/DD/YY
                        r'(\d{4}-\d{1,2}-\d{1,2})',    # YYYY-MM-DD
                        r'(\d{1,2}-\d{1,2}-\d{2,4})',  # MM-DD-YYYY or MM-DD-YY
                    ]
                    
                    date_match = None
                    for pattern in date_patterns:
                        match = re.search(pattern, first_column)
                        if match:
                            date_match = match.group(1)
                            break
                    
                    if date_match:
                        # Parse the date
                        for date_format in ['%m/%d/%Y', '%m/%d/%y', '%Y-%m-%d', '%m-%d-%Y', '%m-%d-%y']:
                            try:
                                above_date = datetime.strptime(date_match, date_format)
                                break
                            except ValueError:
                                continue
                    if above_date:
                        break
    
    # Look for dates in rows below
    below_date = None
    for i in range(current_row_idx + 1, len(rows)):
        if i < len(rows):
            row = rows[i]
            if len(row) >= 1 and row[0]:
                first_column = row[0].strip()
                if first_column and any(char.isdigit() for char in first_column):
                    # Try to extract date
                    import re
                    date_patterns = [
                        r'(\d{1,2}/\d{1,2}/\d{2,4})',  # MM/DD/YYYY or MM/DD/YY
                        r'(\d{4}-\d{1,2}-\d{1,2})',    # YYYY-MM-DD
                        r'(\d{1,2}-\d{1,2}-\d{2,4})',  # MM-DD-YYYY or MM-DD-YY
                    ]
                    
                    date_match = None
                    for pattern in date_patterns:
                        match = re.search(pattern, first_column)
                        if match:
                            date_match = match.group(1)
                            break
                    
                    if date_match:
                        # Parse the date
                        for date_format in ['%m/%d/%Y', '%m/%d/%y', '%Y-%m-%d', '%m-%d-%Y', '%m-%d-%y']:
                            try:
                                below_date = datetime.strptime(date_match, date_format)
                                break
                            except ValueError:
                                continue
                    if below_date:
                        break
    
    # If we have both dates, interpolate
    if above_date and below_date:
        # Calculate the midpoint date
        from datetime import timedelta
        time_diff = below_date - above_date
        midpoint_days = time_diff.days // 2
        return above_date + timedelta(days=midpoint_days)
    elif above_date:
        # If only above date, add 1 day
        from datetime import timedelta
        return above_date + timedelta(days=1)
    elif below_date:
        # If only below date, subtract 1 day
        from datetime import timedelta
        return below_date - timedelta(days=1)
    
    return None

def parse_csv_attendance_data(rows, data_type, period_id, created_by_user_id):
    """
    Parse CSV data for attendance/outreach import.
    
    Expected format:
    - First row: usernames (after first two columns)
    - First column: dates
    - Second column: meeting length in hours
    - Rest of data: hours attended by each user
    
    Args:
        rows: List of CSV rows
        data_type: 'attendance' or 'outreach'
        period_id: ID of the reporting period
        created_by_user_id: ID of the user creating the meetings
    
    Returns:
        dict with success status, counts, and details
    """
    try:
        if len(rows) < 2:
            return {'error': 'CSV must have at least 2 rows', 'meetings_created': 0, 'attendance_logs_created': 0, 'excuses_created': 0, 'details': []}
        
        # Get usernames from first row (skip first two columns)
        # For attendance data, ignore last 5 columns; for outreach, ignore last 3 columns
        ignore_columns = 5 if data_type == 'attendance' else 3
        usernames = [username.strip() for username in rows[0][2:-ignore_columns] if username.strip()]
        
        if not usernames:
            return {'error': 'No usernames found in CSV header', 'meetings_created': 0, 'attendance_logs_created': 0, 'excuses_created': 0, 'details': []}
        
        # Create username to user_id mapping
        username_to_user = {}
        for username in usernames:
            # Try to find user by username (exact match first)
            user = User.query.filter_by(username=username).first()
            if not user:
                # Try to find by email if username contains @
                if '@' in username:
                    user = User.query.filter_by(email=username).first()
                # Try partial match on username
                if not user:
                    user = User.query.filter(User.username.contains(username)).first()
            
            if user:
                username_to_user[username] = user.id
            else:
                # Create new user if not found
                new_user = User(
                    username=username,
                    email=f"{username}@example.com",  # Placeholder email
                    is_admin=False
                )
                db.session.add(new_user)
                db.session.flush()  # Get the ID
                username_to_user[username] = new_user.id
        
        meetings_created = 0
        attendance_logs_created = 0
        excuses_created = 0
        details = []
        
        # Find the actual data rows - skip header rows and summary rows
        data_start_row = 1
        for i, row in enumerate(rows[1:], start=2):
            if len(row) >= 3 and row[0] and row[1] and not row[0].startswith('%') and not row[0].startswith('Last') and not row[0].startswith('REQUIREMENT'):
                # For outreach imports, start from row 2 (after header) and use date guessing
                if data_type == 'outreach':
                    data_start_row = 2  # Start from row 2 for outreach
                    break
                else:
                    # For attendance imports, look for rows with dates
                    try:
                        date_str = row[0].strip()
                        if date_str and any(char.isdigit() for char in date_str):
                            data_start_row = i
                            break
                    except:
                        continue
        
        # Process data rows starting from the identified data start row
        for row_idx, row in enumerate(rows[data_start_row-1:], start=data_start_row):
            if len(row) < 3:  # Need at least date, length, and one user column
                continue
            
            # Skip rows that don't look like data (e.g., percentage rows, total rows)
            if not row[0] or row[0].startswith('%') or row[0].startswith('Last') or row[0].startswith('REQUIREMENT') or row[0].strip().lower() == 'total':
                continue
            
            # For outreach imports, allow empty meeting length (will default to 0)
            if data_type == 'attendance' and not row[1]:
                continue
            
            try:
                # Parse date and extract description from first column
                first_column = row[0].strip()
                if not first_column:
                    continue
                
                # Try to extract date and description from the first column
                date = None
                description = ""
                
                # Look for date patterns in the first column
                import re
                date_patterns = [
                    r'(\d{1,2}/\d{1,2}/\d{2,4})',  # MM/DD/YYYY or MM/DD/YY
                    r'(\d{4}-\d{1,2}-\d{1,2})',    # YYYY-MM-DD
                    r'(\d{1,2}-\d{1,2}-\d{2,4})',  # MM-DD-YYYY or MM-DD-YY
                ]
                
                date_match = None
                for pattern in date_patterns:
                    match = re.search(pattern, first_column)
                    if match:
                        date_match = match.group(1)
                        break
                
                if date_match:
                    # Extract the date part
                    date_str = date_match
                    # Extract description (everything except the date)
                    description = first_column.replace(date_str, '').strip()
                    # Clean up description (remove extra spaces, common prefixes)
                    description = re.sub(r'^\s*[-,\s]+\s*', '', description)
                    description = re.sub(r'\s+', ' ', description)
                    
                    # Parse the date
                    for date_format in ['%m/%d/%Y', '%m/%d/%y', '%Y-%m-%d', '%m-%d-%Y', '%m-%d-%y']:
                        try:
                            date = datetime.strptime(date_str, date_format)
                            break
                        except ValueError:
                            continue
                else:
                    # If no date pattern found, try parsing the entire first column as a date
                    for date_format in ['%m/%d/%Y', '%m/%d/%y', '%Y-%m-%d', '%m-%d-%Y']:
                        try:
                            date = datetime.strptime(first_column, date_format)
                            break
                        except ValueError:
                            continue
                
                if not date:
                    # For outreach imports, try to guess the date
                    if data_type == 'outreach':
                        guessed_date = guess_date_for_outreach_row(rows, row_idx, data_start_row)
                        if guessed_date:
                            date = guessed_date
                            description = first_column  # Use the entire first column as description
                            details.append(f"Row {row_idx}: Guessed date {date.strftime('%Y-%m-%d')} for '{first_column}'")
                        else:
                            details.append(f"Row {row_idx}: Could not parse or guess date from '{first_column}'")
                            continue
                    else:
                        details.append(f"Row {row_idx}: Could not parse date from '{first_column}'")
                        continue
                
                # Parse meeting length
                try:
                    if not row[1] or row[1].strip() == '':
                        # For outreach imports, default to 0 if meeting length is empty
                        meeting_length = 0 if data_type == 'outreach' else None
                        if meeting_length is None:
                            details.append(f"Row {row_idx}: Missing meeting length")
                            continue
                    else:
                        meeting_length = float(row[1])
                        if meeting_length < 0:
                            details.append(f"Row {row_idx}: Invalid meeting length '{row[1]}'")
                            continue
                except (ValueError, TypeError):
                    details.append(f"Row {row_idx}: Could not parse meeting length '{row[1]}'")
                    continue
                
                # Handle 0-hour meetings (bonus hours)
                # These meetings allow users to attend more hours than the meeting length
                is_bonus_meeting = (meeting_length == 0)
                
                # Determine meeting start time based on weekday/weekend
                if date.weekday() < 5:  # Monday = 0, Sunday = 6
                    # Weekday: 15:30
                    start_time = date.replace(hour=15, minute=30, second=0, microsecond=0)
                else:
                    # Weekend: 10:00
                    start_time = date.replace(hour=10, minute=0, second=0, microsecond=0)
                
                # Calculate end time
                # For 0-hour meetings, use 0 duration
                effective_meeting_length = meeting_length
                end_time = start_time + timedelta(hours=effective_meeting_length)
                
                # Create meeting description
                meeting_type = 'regular' if data_type == 'attendance' else 'outreach'
                bonus_note = " (Bonus Hours)" if is_bonus_meeting else ""
                if description:
                    meeting_description = f"{meeting_type.title()} Meeting - {description} ({date.strftime('%B %d, %Y')}){bonus_note}"
                else:
                    meeting_description = f"{meeting_type.title()} Meeting - {date.strftime('%B %d, %Y')}{bonus_note}"
                
                # Check if meeting already exists
                existing_meeting = MeetingHour.query.filter(
                    MeetingHour.start_time == start_time,
                    MeetingHour.meeting_type == meeting_type
                ).first()
                
                if existing_meeting:
                    meeting_hour = existing_meeting
                    details.append(f"Row {row_idx}: Using existing meeting for {date.strftime('%Y-%m-%d')}")
                else:
                    # Create new meeting
                    meeting_hour = MeetingHour(
                        start_time=start_time,
                        end_time=end_time,
                        description=meeting_description,
                        meeting_type=meeting_type,
                        created_by=created_by_user_id
                    )
                    db.session.add(meeting_hour)
                    db.session.flush()  # Get the ID
                    meetings_created += 1
                    bonus_note = " (bonus hours)" if is_bonus_meeting else ""
                    details.append(f"Row {row_idx}: Created {meeting_type} meeting for {date.strftime('%Y-%m-%d')}" + (f" - {description}" if description else "") + bonus_note)
                
                # Process attendance data for each user
                for user_idx, username in enumerate(usernames):
                    if user_idx + 2 >= len(row):  # Not enough columns
                        continue
                    
                    # Skip if we're beyond the valid data columns (after ignoring last columns)
                    if user_idx + 2 >= len(row) - ignore_columns:
                        continue
                    
                    hours_attended_str = row[user_idx + 2].strip()
                    if not hours_attended_str or hours_attended_str in ['', '0', '0.0']:
                        continue
                    
                    # Handle excused absence (*)
                    if hours_attended_str == '*':
                        user_id = username_to_user[username]
                        
                        # Check if excuse already exists
                        existing_excuse = Excuse.query.filter_by(
                            user_id=user_id,
                            meeting_hour_id=meeting_hour.id
                        ).first()
                        
                        if not existing_excuse:
                            # Create new excuse
                            excuse = Excuse(
                                user_id=user_id,
                                meeting_hour_id=meeting_hour.id,
                                reporting_period_id=period_id,
                                reason="Imported from CSV - excused absence",
                                created_by=created_by_user_id
                            )
                            db.session.add(excuse)
                            excuses_created += 1
                            details.append(f"Row {row_idx}: Created excused absence for {username}")
                        else:
                            details.append(f"Row {row_idx}: Excuse already exists for {username}")
                        continue
                    
                    try:
                        hours_attended = float(hours_attended_str)
                        if hours_attended <= 0:
                            continue
                        
                        # For 0-hour meetings (bonus hours), allow any amount of attendance
                        # For regular meetings, validate against meeting length
                        if not is_bonus_meeting and hours_attended > meeting_length:
                            details.append(f"Row {row_idx}: Hours attended ({hours_attended}h) exceeds meeting length ({meeting_length}h) for {username}")
                            continue
                        
                        # Check if attendance already logged
                        user_id = username_to_user[username]
                        existing_log = AttendanceLog.query.filter_by(
                            user_id=user_id,
                            meeting_hour_id=meeting_hour.id
                        ).first()
                        
                        # Determine if this is partial attendance
                        # For bonus meetings, never mark as partial since hours can exceed meeting length
                        is_partial = False if is_bonus_meeting else (hours_attended < meeting_length)
                        
                        # For CSV imports, always store the actual hours attended
                        # This ensures accurate calculation regardless of partial/full attendance
                        partial_hours_value = hours_attended
                        
                        if existing_log:
                            # Update existing log
                            existing_log.partial_hours = partial_hours_value
                            existing_log.is_partial = is_partial
                            bonus_note = " (bonus hours)" if is_bonus_meeting else ""
                            details.append(f"Row {row_idx}: Updated attendance for {username}: {hours_attended}h{bonus_note}")
                        else:
                            # Create new attendance log
                            attendance_log = AttendanceLog(
                                user_id=user_id,
                                meeting_hour_id=meeting_hour.id,
                                partial_hours=partial_hours_value,
                                is_partial=is_partial,
                                notes=f"Imported from CSV{' (bonus hours)' if is_bonus_meeting else ''}"
                            )
                            db.session.add(attendance_log)
                            attendance_logs_created += 1
                            bonus_note = " (bonus hours)" if is_bonus_meeting else ""
                            details.append(f"Row {row_idx}: Logged attendance for {username}: {hours_attended}h{bonus_note}")
                    
                    except (ValueError, TypeError):
                        details.append(f"Row {row_idx}: Invalid hours for {username}: '{hours_attended_str}'")
                        continue
            
            except Exception as e:
                details.append(f"Row {row_idx}: Error processing row: {str(e)}")
                continue
        
        return {
            'error': None,
            'meetings_created': meetings_created,
            'attendance_logs_created': attendance_logs_created,
            'excuses_created': excuses_created,
            'details': details
        }
    
    except Exception as e:
        return {'error': f'Error parsing CSV: {str(e)}', 'meetings_created': 0, 'attendance_logs_created': 0, 'excuses_created': 0, 'details': []}

# Import Slack routes (moved to avoid circular imports)

@app.route('/admin/excuse_requests')
@login_required
def admin_excuse_requests():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    
    # Get all pending excuse requests
    pending_requests = ExcuseRequest.query.filter_by(status='pending').order_by(ExcuseRequest.requested_at.desc()).all()
    
    # Get recent approved/denied requests
    recent_requests = ExcuseRequest.query.filter(ExcuseRequest.status != 'pending').order_by(ExcuseRequest.reviewed_at.desc()).limit(20).all()
    
    return render_template('admin_excuse_requests.html', 
                         pending_requests=pending_requests, 
                         recent_requests=recent_requests)

@app.route('/admin/excuse_requests/<int:request_id>/approve', methods=['POST'])
@login_required
def approve_excuse_request(request_id):
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    
    excuse_request = ExcuseRequest.query.get_or_404(request_id)
    
    if excuse_request.status != 'pending':
        flash('This request has already been processed.', 'error')
        return redirect(url_for('admin_excuse_requests'))
    
    # Check if it's an outreach event (cannot be excused)
    if excuse_request.meeting_hour.meeting_type == 'outreach':
        flash('Outreach events cannot be excused. All outreach hours count toward the total.', 'error')
        return redirect(url_for('admin_excuse_requests'))
    
    # Get admin notes from form
    admin_notes = request.form.get('admin_notes', '')
    
    # Update excuse request status
    excuse_request.status = 'approved'
    excuse_request.reviewed_by = current_user.id
    excuse_request.reviewed_at = datetime.utcnow()
    excuse_request.admin_notes = admin_notes
    
    # Create the actual excuse
    excuse = Excuse(
        user_id=excuse_request.user_id,
        meeting_hour_id=excuse_request.meeting_hour_id,
        reporting_period_id=excuse_request.meeting_hour.reporting_period_id,
        reason=excuse_request.reason,
        created_by=current_user.id,
        excuse_request_id=excuse_request.id
    )
    
    db.session.add(excuse)
    db.session.commit()
    
    flash(f'Excuse request approved for {excuse_request.user.username}.', 'success')
    return redirect(url_for('admin_excuse_requests'))

@app.route('/admin/excuse_requests/<int:request_id>/deny', methods=['POST'])
@login_required
def deny_excuse_request(request_id):
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    
    excuse_request = ExcuseRequest.query.get_or_404(request_id)
    
    if excuse_request.status != 'pending':
        flash('This request has already been processed.', 'error')
        return redirect(url_for('admin_excuse_requests'))
    
    # Get admin notes from form
    admin_notes = request.form.get('admin_notes', '')
    
    # Update excuse request status
    excuse_request.status = 'denied'
    excuse_request.reviewed_by = current_user.id
    excuse_request.reviewed_at = datetime.utcnow()
    excuse_request.admin_notes = admin_notes
    
    db.session.commit()
    
    flash(f'Excuse request denied for {excuse_request.user.username}.', 'success')
    return redirect(url_for('admin_excuse_requests'))

@app.route('/admin/import_csv', methods=['POST'])
@login_required
def import_csv():
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied. Admin privileges required.'}), 403
    
    try:
        # Get form data
        csv_file = request.files.get('csv_file')
        data_type = request.form.get('data_type')  # 'attendance' or 'outreach'
        period_action = request.form.get('period_action')  # 'new' or 'existing'
        period_id = request.form.get('period_id')  # Only used if period_action is 'existing'
        period_name = request.form.get('period_name')  # Only used if period_action is 'new'
        period_start_date = request.form.get('period_start_date')  # Only used if period_action is 'new'
        period_end_date = request.form.get('period_end_date')  # Only used if period_action is 'new'
        
        if not csv_file or not data_type or not period_action:
            return jsonify({'error': 'Missing required fields'}), 400
        
        if csv_file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not csv_file.filename.lower().endswith('.csv'):
            return jsonify({'error': 'File must be a CSV file'}), 400
        
        # Determine the reporting period
        if period_action == 'new':
            if not all([period_name, period_start_date, period_end_date]):
                return jsonify({'error': 'Missing required fields for new period'}), 400
            
            # Create new reporting period
            start_date = datetime.strptime(period_start_date, "%Y-%m-%d")
            end_date = datetime.strptime(period_end_date, "%Y-%m-%d")
            
            period = ReportingPeriod(
                name=period_name,
                start_date=start_date,
                end_date=end_date,
                created_by=current_user.id
            )
            db.session.add(period)
            db.session.flush()  # Get the ID
            period_id = period.id
        else:
            if not period_id:
                return jsonify({'error': 'Period ID required for existing period'}), 400
            period = ReportingPeriod.query.get(period_id)
            if not period:
                return jsonify({'error': 'Reporting period not found'}), 404
        
        # Parse CSV file
        csv_data = csv_file.read().decode('utf-8')
        csv_reader = csv.reader(io.StringIO(csv_data))
        rows = list(csv_reader)
        
        if len(rows) < 2:
            return jsonify({'error': 'CSV file must have at least 2 rows (header and data)'}), 400
        
        # Parse the CSV data
        result = parse_csv_attendance_data(rows, data_type, period_id, current_user.id)
        
        if result['error']:
            return jsonify({'error': result['error']}), 400
        
        # Commit all changes
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully imported {result["meetings_created"]} meetings, {result["attendance_logs_created"]} attendance records, and {result["excuses_created"]} excused absences',
            'details': result['details']
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Error importing CSV: {str(e)}'}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
