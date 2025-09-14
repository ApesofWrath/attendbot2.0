# Attendance Tracker

A Python-based web application for tracking team attendance with Slack bot integration, designed for teams that need to monitor meeting attendance and generate detailed reports.

## Features

- **Slack Integration**: Primary interface through Slack bot commands
- **Admin Management**: Create meeting hours, reporting periods, and excuse team members
- **User Attendance Logging**: Easy attendance logging through Slack
- **Outreach Tracking**: Separate tracking for outreach events with hour-based requirements
- **Detailed Reporting**: Web interface with comprehensive attendance reports
- **Smart Metrics**: Automatic calculation of attendance percentages and outreach hours
- **Dual Requirements**: Track both regular meeting attendance (60%/75%) and outreach hours (12h/18h)

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

### 3. Create Slash Commands

Add these slash commands to your Slack app:

| Command | Request URL | Short Description |
|---------|-------------|-------------------|
| `/add_meeting` | `https://your-domain.com/slack/commands` | Add a regular meeting |
| `/add_outreach` | `https://your-domain.com/slack/commands` | Add an outreach event |
| `/log_attendance` | `https://your-domain.com/slack/commands` | Log regular meeting attendance (supports both meeting_id and date-based logging) |
| `/log_outreach` | `https://your-domain.com/slack/commands` | Log outreach attendance |
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

### 5. Event Subscriptions

Enable event subscriptions and add your endpoint:
- Request URL: `https://your-domain.com/slack/events`
- Subscribe to: `app_mention`, `message.channels`

## Usage

### Admin Commands (Slack)

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

### User Commands (Slack)

```bash
# Log regular meeting attendance (by meeting ID)
/log_attendance 123 Attended the full meeting

# Log attendance by date (full attendance)
/log_attendance 2024-01-15 full Attended the full meeting

# Log partial attendance by date
/log_attendance 2024-01-15 1.5 Arrived late due to traffic

# Log outreach attendance
/log_outreach 456 Helped with school presentation

# Request excuse for a meeting
/request_excuse 123 Had a family emergency
/request_excuse 2024-01-15 Doctor appointment

# View your attendance and outreach
/my_attendance

# Get help
/help
```

### Web Interface

- **Dashboard**: View personal attendance metrics
- **Admin Panel**: Manage meetings, periods, and excuses
- **Reports**: Detailed attendance reports for each period

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
Attendance is calculated as:
```
Attendance % = (Attended Meetings / (Total Meetings - Excused Meetings)) × 100
```

### Outreach Hours
Outreach hours are calculated as:
```
Total Outreach Hours = Sum of all outreach event durations
Attended Outreach Hours = Sum of attended outreach event durations
```

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
