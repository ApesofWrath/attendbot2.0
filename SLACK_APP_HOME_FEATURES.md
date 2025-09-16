# Slack App Home Attendance Tracking

This document describes the new Slack App Home functionality for interactive attendance logging.

## Features Implemented

### 1. App Home Dashboard
- **Recent Meetings Display**: Shows the 5 most recent regular meetings and 5 most recent outreach meetings
- **Attendance Status**: Clearly shows whether attendance has been logged for each meeting
- **Interactive Buttons**: Provides "Log Attendance" or "Edit Attendance" buttons for each meeting
- **Admin Controls**: Admins can add new regular and outreach meetings directly from the App Home
- **Auto-refresh**: App Home updates automatically after any actions

### 2. Attendance Logging
- **Interactive Modals**: Users can log attendance using intuitive forms with start/end time inputs
- **Pre-filled Times**: Modals pre-populate with meeting times for convenience
- **Validation**: Ensures end time is after start time and hours don't exceed meeting duration
- **Notes Support**: Users can add optional notes to their attendance records
- **Real-time Feedback**: Users receive immediate confirmation via direct messages

### 3. Attendance Editing
- **Edit Existing Records**: Users can modify previously logged attendance
- **Current Data Display**: Edit modals show existing attendance times and notes
- **Same Validation**: Full validation ensures data integrity during edits

### 4. Admin Meeting Management
- **Add Regular Meetings**: Admins can create new regular meetings with date, time, and description
- **Add Outreach Meetings**: Admins can create new outreach events
- **Date Picker**: Intuitive date selection for meeting creation
- **Permission Checks**: Only admin users can access meeting creation features

## User Experience Flow

### For Regular Users:
1. User opens the App Home tab in Slack
2. Sees a personalized dashboard with recent meetings
3. Can click "Log Attendance" for meetings they haven't logged yet
4. Can click "Edit Attendance" for meetings they've already logged
5. Fills out the modal form with start/end times and optional notes
6. Receives confirmation and sees the App Home update automatically

### For Admins:
1. All regular user functionality plus:
2. Admin controls section at the bottom of App Home
3. Can click "Add Regular Meeting" or "Add Outreach Meeting"
4. Fills out meeting details (date, time, description)
5. Meeting is created and visible to all users immediately

## Technical Implementation

### New Event Handlers
- `app_home_opened`: Triggered when users open the App Home tab
- `block_actions`: Handles button clicks for logging/editing attendance and admin actions
- `view_submission`: Processes modal form submissions

### New Slack Bot Methods
- `update_app_home()`: Creates and publishes the App Home view
- `open_log_attendance_modal()`: Opens attendance logging modal
- `open_edit_attendance_modal()`: Opens attendance editing modal
- `open_add_meeting_modal()`: Opens meeting creation modal
- `handle_attendance_modal_submission()`: Processes attendance logging
- `handle_edit_attendance_modal_submission()`: Processes attendance editing
- `handle_add_meeting_modal_submission()`: Processes meeting creation

### Block Kit Components Used
- **Headers**: Section titles and welcome message
- **Sections**: Meeting information display
- **Buttons**: Action triggers for logging/editing
- **Modals**: Forms for data input
- **Date Pickers**: For selecting meeting dates
- **Text Inputs**: For time and description entry
- **Dividers**: Visual separation between sections

## Configuration Requirements

### Slack App Permissions
Add these OAuth scopes to your Slack app:
- `chat:write` - Send messages and publish App Home views
- `users:read` - Get user information
- `im:write` - Send direct messages for confirmations

### Event Subscriptions
Subscribe to this additional event:
- `app_home_opened` - When users open the App Home tab

### App Home Settings
1. Enable App Home in your Slack app settings
2. Enable the "Home Tab" feature
3. Set appropriate display name and description

## Database Interactions
- **Read Operations**: Fetches recent meetings and existing attendance logs
- **Write Operations**: Creates new attendance logs and meetings
- **Update Operations**: Modifies existing attendance records
- **Validation**: Ensures data integrity with the same rules as web interface

## Error Handling
- User-friendly error messages sent via direct message
- Comprehensive logging of errors for debugging
- Graceful fallbacks for missing user accounts
- Validation errors with specific guidance

## Security Features
- Admin permission checks for meeting creation
- User authentication via Slack user ID
- SQL injection protection through ORM usage
- Input validation for all form submissions

## Testing Considerations
- Test with both admin and regular users
- Verify all button interactions work correctly
- Test modal submissions with valid and invalid data
- Ensure App Home refreshes properly after actions
- Test error scenarios (missing meetings, invalid times, etc.)

## Future Enhancements
- Attendance statistics on App Home
- Quick actions for common time ranges
- Meeting reminders and notifications
- Bulk attendance operations
- Mobile optimization for Block Kit layouts
