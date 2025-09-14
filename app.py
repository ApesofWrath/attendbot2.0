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
from google_auth import get_flow, get_user_info, get_slack_user_info

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///attendance.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

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
    # Partial attendance fields
    partial_hours = db.Column(db.Float, nullable=True)  # Hours actually attended
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
    return render_template('admin_dashboard.html', periods=periods, users=users)

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

@app.route('/reports/<int:period_id>')
@login_required
def attendance_report(period_id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('dashboard'))
    
    period = ReportingPeriod.query.get_or_404(period_id)
    report_data = get_attendance_report_data(period_id)
    
    return render_template('attendance_report.html', 
                         period=period,
                         report_data=report_data)

@app.route('/api/attendance', methods=['POST'])
@login_required
def log_attendance():
    data = request.get_json()
    meeting_hour_id = data.get('meeting_hour_id')
    notes = data.get('notes', '')
    
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
    
    # Create attendance log
    attendance_log = AttendanceLog(
        user_id=current_user.id,
        meeting_hour_id=meeting_hour_id,
        notes=notes
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
    
    # Calculate regular meeting metrics
    total_regular = len(regular_meetings)
    attended_regular = len(regular_attended)
    excused_regular = len(regular_excused)
    effective_regular_total = total_regular - excused_regular
    effective_regular_attended = attended_regular
    
    # Calculate partial attendance for regular meetings
    partial_attendance_hours = 0
    for log in regular_attended:
        if log.is_partial and log.partial_hours:
            partial_attendance_hours += log.partial_hours
        else:
            # Full attendance - count as 1 meeting
            pass
    
    regular_attendance_percentage = (effective_regular_attended / effective_regular_total * 100) if effective_regular_total > 0 else 0
    
    # Calculate outreach hours
    total_outreach_hours = sum((m.end_time - m.start_time).total_seconds() / 3600 for m in outreach_meetings)
    
    # Calculate attended outreach hours (including partial attendance)
    attended_outreach_hours = 0
    for log in outreach_attended:
        if log.is_partial and log.partial_hours:
            attended_outreach_hours += log.partial_hours
        else:
            # Full attendance - use meeting duration
            attended_outreach_hours += (log.meeting_hour.end_time - log.meeting_hour.start_time).total_seconds() / 3600
    
    # Outreach hours cannot be excused - all hours count toward total
    excused_outreach_hours = 0  # No outreach hours can be excused
    effective_outreach_hours = total_outreach_hours  # All outreach hours count
    effective_attended_outreach_hours = attended_outreach_hours
    
    # Calculate overall metrics - only regular meetings can be excused
    total_meetings = len(all_meeting_hours)
    attended_meetings = len(attendance_logs)
    excused_meetings = len(regular_excused)  # Only count regular meeting excuses
    effective_total = total_meetings - excused_meetings
    effective_attended = attended_meetings
    attendance_percentage = (effective_attended / effective_total * 100) if effective_total > 0 else 0
    
    return {
        # Overall metrics
        'total_meetings': total_meetings,
        'attended_meetings': attended_meetings,
        'excused_meetings': excused_meetings,
        'effective_total': effective_total,
        'effective_attended': effective_attended,
        'attendance_percentage': round(attendance_percentage, 2),
        'meets_team_requirement': regular_attendance_percentage >= 60,
        'meets_travel_requirement': regular_attendance_percentage >= 75,
        
        # Regular meeting metrics
        'regular_meetings': {
            'total': total_regular,
            'attended': attended_regular,
            'excused': excused_regular,
            'effective_total': effective_regular_total,
            'effective_attended': effective_regular_attended,
            'partial_hours': round(partial_attendance_hours, 2),
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
    """Get attendance report data for all users in a period"""
    period = ReportingPeriod.query.get(period_id)
    if not period:
        return []
    
    users = User.query.all()
    report_data = []
    
    for user in users:
        user_data = get_user_attendance_data(user.id, period_id)
        if user_data:
            user_data['user'] = user
            report_data.append(user_data)
    
    return sorted(report_data, key=lambda x: x['attendance_percentage'], reverse=True)

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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
