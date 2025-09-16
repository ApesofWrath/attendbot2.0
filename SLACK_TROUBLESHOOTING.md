# Slack App Home Troubleshooting Guide

## Issue: Buttons Show Exclamation Marks and Don't Work

### Root Cause
The debug script revealed that the Slack API is returning `invalid_auth` errors, which means the bot token is not valid or properly configured.

### Step-by-Step Fix

#### 1. Check Your Slack App Configuration

1. **Go to your Slack App settings**: https://api.slack.com/apps
2. **Select your app** from the list
3. **Check the Bot Token**:
   - Go to "OAuth & Permissions"
   - Look for "Bot User OAuth Token" (starts with `xoxb-`)
   - If it's missing or shows as "Not Set", you need to install the app to your workspace

#### 2. Install the App to Your Workspace

1. **In your Slack app settings**, go to "OAuth & Permissions"
2. **Click "Install to Workspace"** (or "Reinstall to Workspace" if already installed)
3. **Authorize the app** with the required permissions
4. **Copy the Bot User OAuth Token** (starts with `xoxb-`)

#### 3. Update Your Environment Variables

1. **Update your `.env` file** with the correct token:
   ```bash
   SLACK_BOT_TOKEN=xoxb-your-actual-bot-token-here
   ```

2. **Restart your application** after updating the token

#### 4. Configure Interactivity (Required for Buttons)

1. **In your Slack app settings**, go to "Interactivity & Shortcuts"
2. **Turn on "Interactivity"**
3. **Set the Request URL** to: `https://your-domain.com/slack/interactive`
4. **Save Changes**

#### 5. Configure App Home (Required for the Dashboard)

1. **In your Slack app settings**, go to "App Home"
2. **Enable "Home Tab"**
3. **Set a display name** for your app
4. **Save Changes**

#### 6. Required OAuth Scopes

Make sure your app has these scopes in "OAuth & Permissions":
- `app_mentions:read`
- `channels:history`
- `chat:write`
- `commands`
- `users:read`
- `im:write` (for direct message confirmations)

#### 7. Event Subscriptions

1. **Go to "Event Subscriptions"**
2. **Turn on "Enable Events"**
3. **Set Request URL** to: `https://your-domain.com/slack/events`
4. **Subscribe to these events**:
   - `app_mention`
   - `message.channels`
   - `app_home_opened`

### Testing the Fix

1. **Restart your application** with the correct token
2. **Open the App Home** in Slack (click on your app in the sidebar)
3. **Try clicking a button** - it should now open a modal instead of showing an exclamation mark

### Common Issues and Solutions

#### Issue: "invalid_auth" Error
- **Solution**: The bot token is incorrect or expired
- **Fix**: Reinstall the app and get a fresh token

#### Issue: "missing_scope" Error
- **Solution**: The app doesn't have the required permissions
- **Fix**: Add the missing OAuth scopes and reinstall the app

#### Issue: "invalid_request" Error
- **Solution**: The Request URL is incorrect or not accessible
- **Fix**: Verify the URL is correct and your server is running

#### Issue: Buttons Still Show Exclamation Marks
- **Solution**: Interactivity is not enabled or URL is wrong
- **Fix**: Enable interactivity and set the correct Request URL

### Debugging Steps

1. **Check the application logs** when clicking buttons
2. **Verify the Request URL** is accessible from the internet
3. **Test the endpoints** manually:
   ```bash
   curl -X POST https://your-domain.com/slack/interactive \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "payload={\"type\":\"test\"}"
   ```

4. **Use the debug script**:
   ```bash
   python debug_slack_interactive.py
   ```

### Production Deployment Checklist

- [ ] Bot token is valid and up-to-date
- [ ] Interactivity is enabled with correct Request URL
- [ ] App Home is enabled
- [ ] All required OAuth scopes are granted
- [ ] Event subscriptions are configured
- [ ] Request URLs are accessible from the internet
- [ ] Application is running and responding to requests

### Getting Help

If you're still having issues:

1. **Check the Slack API documentation**: https://api.slack.com/methods
2. **Review the error logs** in your application
3. **Test with a simple button** first to isolate the issue
4. **Verify your Slack app configuration** matches the requirements

The most common issue is an invalid or missing bot token, so start there!
