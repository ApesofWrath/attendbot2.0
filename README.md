# Attendance Tracker

A Python-based web application for tracking team attendance with Slack bot integration, designed for teams that need to monitor meeting attendance and generate detailed reports.

## Features

- **Slack Integration**: Primary interface through Slack bot commands and interactive App Home
- **Interactive App Home**: Intuitive dashboard showing recent meetings with one-click attendance logging
- **Admin Management**: Create meeting hours, reporting periods, and excuse team members
- **Time-Based Attendance Logging**: Log precise start and end times for accurate tracking
- **Smart Time Matching**: Automatically finds meetings/events based on date and time overlap
- **Modal-Based Forms**: User-friendly forms for logging and editing attendance directly in Slack
- **Outreach Tracking**: Separate tracking for outreach events with hour-based requirements
- **Detailed Reporting**: Web interface with comprehensive attendance reports and charts
- **Attendance Visualization**: Charts showing member presence over time during meetings
- **Smart Metrics**: Automatic calculation of attendance percentages and outreach hours
- **Dual Requirements**: Track both regular meeting attendance (60%/75%) and outreach hours (12h/18h)
- **Legacy Support**: Intelligent handling of existing records without specific times

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd attendance

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy environment template
cp env.example .env

# Edit .env with your configuration
nano .env
```

Required environment variables:
- `SECRET_KEY`: Flask secret key for sessions
- `DATABASE_URL`: Database connection string
- `SLACK_BOT_TOKEN`: Your Slack bot token
- `SLACK_SIGNING_SECRET`: Your Slack app signing secret
- `GOOGLE_CLIENT_ID`: Your Google OAuth client ID
- `GOOGLE_CLIENT_SECRET`: Your Google OAuth client secret
- `GOOGLE_REDIRECT_URI`: Your Google OAuth redirect URI

### 3. Database Setup

```bash
# Initialize database
python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

### 4. Run the Application

```bash
# Development
python app.py

# Production (with gunicorn)
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

## Slack Bot Setup

### 1. Create a Slack App

1. Go to [api.slack.com](https://api.slack.com/apps)
2. Click "Create New App" → "From scratch"
3. Name your app and select your workspace

### 2. Configure Bot Permissions

Add the following OAuth scopes:
- `app_mentions:read`
- `channels:history`
- `chat:write`
- `commands`
- `users:read`
- `im:write` (for App Home direct message confirmations)

### 3. Create Slash Commands

Add these slash commands to your Slack app:

| Command | Request URL | Short Description |
|---------|-------------|-------------------|
| `/add_meeting` | `https://your-domain.com/slack/commands` | Add a regular meeting |
| `/add_outreach` | `https://your-domain.com/slack/commands` | Add an outreach event |
| `/log_attendance` | `https://your-domain.com/slack/commands` | Log regular meeting attendance (supports both meeting_id and date-based logging) |
| `/log_outreach` | `https://your-domain.com/slack/commands` | Log outreach attendance |
| `/edit_attendance` | `https://your-domain.com/slack/commands` | Edit existing attendance by time range |
| `/request_excuse` | `https://your-domain.com/slack/commands` | Request excuse for a meeting |
| `/create_period` | `https://your-domain.com/slack/commands` | Create reporting period |
| `/excuse` | `https://your-domain.com/slack/commands` | Excuse user from meeting (admin only) |
| `/my_attendance` | `https://your-domain.com/slack/commands` | View your attendance and outreach |
| `/help` | `https://your-domain.com/slack/commands` | Show help |

### 4. Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google+ API
4. Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client IDs"
5. Set application type to "Web application"
6. Add authorized redirect URIs:
   - `http://localhost:5001/auth/google/callback` (development)
   - `https://your-domain.com/auth/google/callback` (production)
7. Copy the Client ID and Client Secret to your `.env` file

### 5. App Home Setup

1. Enable App Home in your Slack app settings:
   - Go to "App Home" in your app configuration
   - Enable the "Home Tab" feature
   - Set a display name and description for your app

### 6. Event Subscriptions

Enable event subscriptions and add your endpoint:
- Request URL: `https://your-domain.com/slack/events`
- Subscribe to: `app_mention`, `message.channels`, `app_home_opened`

### 7. Interactivity & Shortcuts

Enable interactivity for buttons and modals:
- Request URL: `https://your-domain.com/slack/interactive`

## Usage

### Slack App Home (Recommended)

The easiest way to log attendance is through the Slack App Home:

1. **Open App Home**: Click on the attendance bot in your Slack sidebar or search for the app
2. **View Recent Meetings**: See the 5 most recent regular meetings and outreach events
3. **Log Attendance**: Click "Log Attendance" for meetings you attended
4. **Edit Records**: Click "Edit Attendance" to modify existing records
5. **Admin Features**: Admins can add new meetings directly from the App Home

#### App Home Features:
- **One-Click Access**: Easy buttons for logging and editing attendance
- **Visual Status**: Clear indicators showing which meetings have logged attendance
- **Interactive Forms**: User-friendly modals for entering start/end times and notes
- **Real-Time Updates**: App Home refreshes automatically after any changes
- **Admin Controls**: Streamlined meeting creation for administrators

### Running the Application

#### Development Mode

```bash
# Method 1: Using run.py (recommended for development)
python run.py

# Method 2: Using start.py (includes Slack integration)
python start.py

# Method 3: Direct Flask app
python app.py
```

The application will be available at `http://localhost:5001`

#### Production Mode

```bash
# Using Gunicorn (recommended for production)
gunicorn -w 4 -b 0.0.0.0:8000 start:app

# Using Docker
docker-compose up -d

# Using Docker directly
docker build -t attendance-tracker .
docker run -p 8000:8000 --env-file .env attendance-tracker
```

#### Environment Setup

1. **Create your environment file:**
```bash
cp env.example .env
```

2. **Configure required variables in `.env`:**
```bash
# Flask Configuration
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///attendance.db  # or postgresql://user:pass@host/db

# Slack Integration
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_SIGNING_SECRET=your-signing-secret

# Google OAuth (for web login)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:5001/auth/google/callback

# Optional: Production settings
FLASK_ENV=production
BEHIND_PROXY=true  # Set to true if behind nginx/proxy
```

3. **Initialize the database:**
```bash
# For SQLite (development)
python -c "from app import app, db; app.app_context().push(); db.create_all()"

# For PostgreSQL (production)
# Database will be created automatically on first run
```

### Slack Bot Commands

#### Admin Commands

```bash
# Add a regular meeting
/add_meeting 2024-01-15 14:00-16:00 Team Meeting

# Add an outreach event  
/add_outreach 2024-01-16 10:00-12:00 School Visit

# Create a reporting period
/create_period Fall Season 2024-01-01 2024-03-31

# Excuse a user from a meeting
/excuse 123 456 Family emergency
```

#### User Commands

##### Regular Meeting Attendance

```bash
# Log full attendance by meeting ID
/log_attendance 123 Attended the full meeting

# Log attendance by specific time range
/log_attendance 2024-01-15 14:00-16:00 Attended the full meeting

# Log partial attendance by time range
/log_attendance 2024-01-15 14:30-15:30 Arrived late due to traffic

# Log attendance with notes
/log_attendance 2024-01-15 14:00-15:30 Left early for another meeting
```

##### Outreach Event Attendance

```bash
# Log full outreach attendance by event ID
/log_outreach 456 Participated in school visit

# Log outreach by specific time range
/log_outreach 2024-01-16 10:00-12:00 Full participation in school visit

# Log partial outreach by time range
/log_outreach 2024-01-16 10:30-11:30 Arrived late to school visit

# Log outreach with notes
/log_outreach 2024-01-16 10:00-11:30 Left early for another commitment
```

##### Edit Attendance

```bash
# Edit existing attendance by time range
/edit_attendance 2024-01-15 14:30-16:00 Updated attendance times

# Edit attendance with notes
/edit_attendance 2024-01-15 14:00-15:45 Corrected my actual attendance time
```

##### Excuse Requests

```bash
# Request excuse for a meeting by ID
/request_excuse 123 Family emergency

# Request excuse by date
/request_excuse 2024-01-15 Medical appointment
```

##### Other Commands

```bash
# View your attendance summary
/my_attendance

# Get help with commands
/help
```

#### Time-Based Logging Features

The new time-based logging system provides several advantages:

- **Precise Tracking**: Log exact start and end times of your attendance
- **Automatic Calculation**: System calculates actual hours attended based on overlap with meeting times
- **Smart Matching**: Automatically finds the correct meeting/outreach event based on date and time
- **Partial Attendance**: Easily log partial attendance with specific time ranges
- **Legacy Support**: Existing records without specific times are handled intelligently

**Time Format**: Use `HH:MM-HH:MM` format (24-hour time)
- Examples: `14:00-16:00`, `09:30-11:00`, `13:45-14:15`

**Date Format**: Use `YYYY-MM-DD` format
- Examples: `2024-01-15`, `2024-03-22`, `2024-12-31`

### Web Interface

Access the web interface at `http://localhost:5001` (development) or your production URL.

#### Features:
- **Dashboard**: View personal attendance metrics and current status
- **Log Attendance**: One-click attendance logging with time-based input
- **Edit Attendance**: Modify existing attendance records with start/end times
- **Admin Panel**: Manage meetings, periods, and excuses
- **Reports**: Detailed attendance reports for each period
- **Meeting Details**: Individual meeting views with attendance charts
- **Attendance Visualization**: Charts showing member presence over time
- **Peak Attendance Analytics**: Identify when most members were present
- **User Management**: Admin can manage users and permissions
- **Google OAuth**: Secure login using Google accounts

#### Navigation:
- **Home**: Personal dashboard with attendance overview
- **Admin Dashboard**: Full administrative controls (admin only)
- **Reports**: Generate and view attendance reports
- **Login/Logout**: Google OAuth authentication

### Database Management

#### Migrations (if using Flask-Migrate)
```bash
# Initialize migrations
flask db init

# Create migration
flask db migrate -m "Description of changes"

# Apply migration
flask db upgrade
```

#### Manual Database Operations
```bash
# Reset database (development only)
python -c "from app import app, db; app.app_context().push(); db.drop_all(); db.create_all()"

# Create admin user
python -c "from app import app, db, User; app.app_context().push(); admin = User(username='admin', email='admin@example.com', is_admin=True); db.session.add(admin); db.session.commit()"
```

### Troubleshooting

#### Common Issues

1. **"User not found" in Slack commands:**
   - Ensure the user has logged in via the web interface first
   - Check that Slack user ID is properly linked in the database

2. **Database connection errors:**
   - Verify DATABASE_URL is correct
   - For PostgreSQL, ensure the database exists and credentials are correct
   - For SQLite, check file permissions

3. **Slack bot not responding:**
   - Verify SLACK_BOT_TOKEN and SLACK_SIGNING_SECRET are correct
   - Check that the Slack app has proper permissions
   - Ensure the webhook URL is accessible from Slack

4. **Google OAuth not working:**
   - Verify GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET
   - Check that redirect URI matches exactly
   - Ensure Google+ API is enabled in Google Cloud Console

5. **Port already in use:**
   - Change the port in run.py or start.py
   - Kill existing processes: `lsof -ti:5001 | xargs kill -9`

#### Logs and Debugging

```bash
# Enable debug mode
export FLASK_DEBUG=1
python run.py

# View application logs
tail -f logs/app.log  # if logging to file

# Check database
sqlite3 instance/attendance.db  # for SQLite
psql $DATABASE_URL  # for PostgreSQL
```

## Database Schema

### Users
- `id`: Primary key
- `slack_user_id`: Slack user identifier
- `username`: Display name
- `email`: Optional email
- `is_admin`: Admin privileges flag

### Meeting Hours
- `id`: Primary key
- `start_time`: Meeting start time
- `end_time`: Meeting end time
- `description`: Meeting description
- `meeting_type`: Type of meeting ('regular' or 'outreach')
- `created_by`: Admin who created the meeting

### Attendance Logs
- `id`: Primary key
- `user_id`: User who logged attendance
- `meeting_hour_id`: Meeting attended
- `logged_at`: When attendance was logged
- `notes`: Optional notes
- `partial_hours`: Hours actually attended (for partial attendance)
- `is_partial`: Whether this is partial attendance
- `attendance_start_time`: Actual start time of attendance
- `attendance_end_time`: Actual end time of attendance

### Reporting Periods
- `id`: Primary key
- `name`: Period name (e.g., "Fall Season")
- `start_date`: Period start date
- `end_date`: Period end date
- `created_by`: Admin who created the period

### Excuses
- `id`: Primary key
- `user_id`: User being excused
- `meeting_hour_id`: Meeting being excused from
- `reporting_period_id`: Period context
- `reason`: Reason for excuse
- `created_by`: Admin who created the excuse

## Attendance Calculation

### Regular Meetings
Attendance is now calculated based on hours:
```
Attendance % = (Attended Hours / (Total Hours - Excused Hours)) × 100
```

### Outreach Hours
Outreach hours are calculated as:
```
Total Outreach Hours = Sum of all outreach event durations
Attended Outreach Hours = Sum of attended outreach event durations
```

### Time-Based Tracking
- Users specify start and end times of their actual attendance
- System automatically calculates hours attended based on time overlap with meeting duration
- Partial attendance is supported - users can log fewer hours than the total meeting duration
- Full attendance means the user attended for the entire meeting duration
- Extended attendance is allowed - users can log more hours than the meeting duration
- Excused meetings are excluded from the total hours calculation
- Legacy records without specific times are handled intelligently

### Requirements
- **Regular Meetings**: 60% (team) / 75% (travel)
- **Outreach Hours**: 12h (team) / 18h (travel)

## Deployment

### Heroku

1. Create a Heroku app
2. Set environment variables
3. Deploy with Git

```bash
heroku create your-app-name
heroku config:set SECRET_KEY=your-secret-key
heroku config:set SLACK_BOT_TOKEN=your-bot-token
heroku config:set SLACK_SIGNING_SECRET=your-signing-secret
git push heroku main
```

### Docker

```bash
# Build image
docker build -t attendance-tracker .

# Run container
docker run -p 8000:8000 --env-file .env attendance-tracker
```

## Development

### Adding New Features

1. Update database models in `app.py`
2. Add new routes and logic
3. Update Slack bot commands in `slack_bot.py`
4. Add web interface templates
5. Update tests

### Testing

```bash
# Run tests (when implemented)
python -m pytest tests/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues and questions:
1. Check the documentation
2. Search existing issues
3. Create a new issue with detailed information
