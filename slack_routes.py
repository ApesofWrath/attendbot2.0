from flask import request, jsonify
from app import app
from slack_bot import AttendanceSlackBot
import json

bot = AttendanceSlackBot()

@app.route('/slack/events', methods=['POST'])
def slack_events():
    """Handle Slack events"""
    data = request.get_json()
    
    # Handle URL verification
    if data.get('type') == 'url_verification':
        return data.get('challenge')
    
    # Handle event callbacks
    if data.get('type') == 'event_callback':
        event = data.get('event', {})
        
        # Handle app mentions
        if event.get('type') == 'app_mention':
            handle_app_mention(event)
        
        # Handle slash commands
        elif event.get('type') == 'slash_command':
            handle_slash_command(event)
    
    return jsonify({'status': 'ok'})

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
        return jsonify({'response_type': 'in_channel'})
    else:
        return jsonify({'response_type': 'ephemeral', 'text': 'Error processing command'})

def handle_app_mention(event):
    """Handle when the bot is mentioned"""
    # This could be used for interactive features
    pass

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
