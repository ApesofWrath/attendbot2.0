from flask import request, jsonify
from app import app
from slack_bot import AttendanceSlackBot
import json
import logging

# Configure logging
logger = logging.getLogger(__name__)

bot = AttendanceSlackBot()

@app.route('/slack/events', methods=['POST'])
def slack_events():
    """Handle Slack events"""
    try:
        # Log the incoming request for debugging
        logger.info(f"Slack events endpoint called with method: {request.method}")
        logger.info(f"Content-Type: {request.content_type}")
        
        # Handle both JSON and form data
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()
        
        logger.info(f"Received data: {data}")
        
        # Handle URL verification challenge
        if data and data.get('type') == 'url_verification':
            challenge = data.get('challenge')
            logger.info(f"URL verification challenge: {challenge}")
            if challenge:
                # Return the challenge value as plain text, not JSON
                return challenge, 200, {'Content-Type': 'text/plain'}
            else:
                return 'No challenge provided', 400
        
        # Handle event callbacks
        if data and data.get('type') == 'event_callback':
            event = data.get('event', {})
            
            # Handle app mentions
            if event.get('type') == 'app_mention':
                handle_app_mention(event)
            
            # Handle direct messages
            elif event.get('type') == 'message':
                handle_direct_message(event)
            
            # Handle slash commands
            elif event.get('type') == 'slash_command':
                handle_slash_command(event)
        
        return jsonify({'status': 'ok'}), 200
        
    except Exception as e:
        logger.error(f"Error in slack_events: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/slack/commands', methods=['POST'])
def slack_commands():
    """Handle Slack slash commands"""
    data = request.form.to_dict()
    
    command = data.get('command')
    user_id = data.get('user_id')
    channel_id = data.get('channel_id')
    text = data.get('text', '')
    
    response = bot.handle_command(command, user_id, channel_id, text)
    
    if response:
        # Since the bot sends ephemeral messages directly, we don't need to return a response
        # Slack will show the command as processed but the actual response is ephemeral
        return '', 200
    else:
        return jsonify({'response_type': 'ephemeral', 'text': 'Error processing command'})

def handle_app_mention(event):
    """Handle when the bot is mentioned in a channel"""
    try:
        user_id = event.get('user')
        channel_id = event.get('channel')
        text = event.get('text', '')
        
        # Remove the bot mention from the text
        # Text format: "<@U1234567890> command args"
        bot_user_id = event.get('bot_id') or event.get('user')
        mention_pattern = f"<@{bot_user_id}>"
        if text.startswith(mention_pattern):
            text = text[len(mention_pattern):].strip()
        
        logger.info(f"App mention from {user_id} in {channel_id}: {text}")
        
        # Process as a command
        if text:
            # Parse the command (first word is the command)
            parts = text.split()
            command = f"/{parts[0]}" if parts else "/help"
            command_text = " ".join(parts[1:]) if len(parts) > 1 else ""
            
            response = bot.handle_command(command, user_id, channel_id, command_text)
            
        else:
            # No command provided, show help
            response = bot.handle_command("/help", user_id, channel_id, "")
            
    except Exception as e:
        logger.error(f"Error handling app mention: {e}")
        bot._send_ephemeral_message(channel_id, user_id, "❌ Error processing your request. Please try again.")

def handle_direct_message(event):
    """Handle direct messages to the bot"""
    try:
        # Only process messages from users (not from bots)
        if event.get('bot_id') or event.get('subtype'):
            return
            
        user_id = event.get('user')
        channel_id = event.get('channel')
        text = event.get('text', '')
        
        # Check if this is a DM (channel starts with 'D')
        if not channel_id.startswith('D'):
            return
            
        logger.info(f"Direct message from {user_id}: {text}")
        
        # Process as a command
        if text:
            # Parse the command (first word is the command)
            parts = text.split()
            command = f"/{parts[0]}" if parts else "/help"
            command_text = " ".join(parts[1:]) if len(parts) > 1 else ""
            
            response = bot.handle_command(command, user_id, channel_id, command_text)
            
        else:
            # No command provided, show help
            response = bot.handle_command("/help", user_id, channel_id, "")
            
    except Exception as e:
        logger.error(f"Error handling direct message: {e}")
        bot._send_message(channel_id, "❌ Error processing your request. Please try again.")

def handle_slash_command(event):
    """Handle slash command events"""
    # This is handled by the /slack/commands endpoint
    pass

@app.route('/slack/interactive', methods=['POST'])
def slack_interactive():
    """Handle Slack interactive components (buttons, modals, etc.)"""
    payload = json.loads(request.form['payload'])
    
    # Handle different interaction types
    if payload['type'] == 'block_actions':
        handle_block_actions(payload)
    elif payload['type'] == 'view_submission':
        handle_view_submission(payload)
    
    return jsonify({'response_type': 'ephemeral'})

def handle_block_actions(payload):
    """Handle button clicks and other block actions"""
    pass

def handle_view_submission(payload):
    """Handle modal form submissions"""
    pass
