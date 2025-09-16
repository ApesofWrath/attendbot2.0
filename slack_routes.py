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
            
            # Handle App Home opened
            elif event.get('type') == 'app_home_opened':
                handle_app_home_opened(event)
        
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
    try:
        # Log the incoming request for debugging
        logger.info(f"Slack interactive endpoint called with method: {request.method}")
        logger.info(f"Content-Type: {request.content_type}")
        logger.info(f"Form data keys: {list(request.form.keys())}")
        
        # Parse the payload
        if 'payload' not in request.form:
            logger.error("No payload found in request form")
            return jsonify({'error': 'No payload provided'}), 400
        
        payload = json.loads(request.form['payload'])
        logger.info(f"Received payload type: {payload.get('type')}")
        logger.info(f"Payload: {payload}")
        
        # Handle different interaction types
        if payload['type'] == 'block_actions':
            logger.info("Processing block actions")
            handle_block_actions(payload)
            # For block actions, return empty response (200 OK)
            logger.info("Block actions processed successfully")
            return '', 200
        elif payload['type'] == 'view_submission':
            logger.info("Processing view submission")
            handle_view_submission(payload)
            # For view submissions, return empty response (200 OK)
            logger.info("View submission processed successfully")
            return '', 200
        else:
            logger.warning(f"Unknown payload type: {payload['type']}")
            return '', 200
        
    except Exception as e:
        logger.error(f"Error in slack_interactive: {e}")
        import traceback
        traceback.print_exc()
        # Return empty response even on error to prevent Slack retries
        return '', 200

@app.route('/slack/test-interactive', methods=['POST'])
def test_interactive():
    """Test endpoint for interactive components (for debugging)"""
    try:
        # Simulate a block actions payload
        test_payload = {
            'type': 'block_actions',
            'user': {'id': 'U12345TEST'},
            'trigger_id': 'test_trigger_123',
            'actions': [
                {
                    'action_id': 'refresh_app_home',
                    'value': None
                }
            ]
        }
        
        logger.info("Testing interactive components with mock payload")
        handle_block_actions(test_payload)
        
        return jsonify({
            'status': 'success',
            'message': 'Interactive components test completed. Check logs for details.'
        })
        
    except Exception as e:
        logger.error(f"Error in test interactive: {e}")
        return jsonify({'error': str(e)}), 500

def handle_block_actions(payload):
    """Handle button clicks and other block actions"""
    try:
        user_id = payload['user']['id']
        actions = payload['actions']
        trigger_id = payload.get('trigger_id')
        
        logger.info(f"Handling block actions for user {user_id}, trigger_id: {trigger_id}")
        logger.info(f"Actions: {actions}")
        
        if not trigger_id:
            logger.error("No trigger_id found in payload")
            return
        
        for action in actions:
            action_id = action.get('action_id')
            value = action.get('value')
            
            logger.info(f"Processing action: {action_id}")
            
            # Handle different button actions
            if action_id.startswith('log_attendance_'):
                meeting_id = action_id.replace('log_attendance_', '')
                logger.info(f"Opening log attendance modal for meeting {meeting_id}")
                bot.open_log_attendance_modal(user_id, meeting_id, trigger_id)
            
            elif action_id.startswith('edit_attendance_'):
                meeting_id = action_id.replace('edit_attendance_', '')
                logger.info(f"Opening edit attendance modal for meeting {meeting_id}")
                bot.open_edit_attendance_modal(user_id, meeting_id, trigger_id)
            
            elif action_id == 'add_regular_meeting':
                logger.info("Opening add regular meeting modal")
                bot.open_add_meeting_modal(user_id, 'regular', trigger_id)
            
            elif action_id == 'add_outreach_meeting':
                logger.info("Opening add outreach meeting modal")
                bot.open_add_meeting_modal(user_id, 'outreach', trigger_id)
            
            elif action_id.startswith('request_excuse_'):
                meeting_id = action_id.replace('request_excuse_', '')
                logger.info(f"Opening request excuse modal for meeting {meeting_id}")
                bot.open_request_excuse_modal(user_id, meeting_id, trigger_id)
            
            elif action_id == 'refresh_app_home':
                logger.info("Refreshing app home")
                bot.update_app_home(user_id)
            
            else:
                logger.warning(f"Unknown action_id: {action_id}")
                
    except Exception as e:
        logger.error(f"Error handling block actions: {e}")
        import traceback
        traceback.print_exc()

def handle_view_submission(payload):
    """Handle modal form submissions"""
    try:
        user_id = payload['user']['id']
        view = payload['view']
        
        # Handle different view callbacks
        callback_id = view.get('callback_id')
        
        if callback_id == 'log_attendance_modal':
            handle_log_attendance_modal(payload)
        elif callback_id == 'edit_attendance_modal':
            handle_edit_attendance_modal(payload)
        elif callback_id == 'request_excuse_modal':
            handle_request_excuse_modal(payload)
        elif callback_id == 'add_meeting_modal':
            handle_add_meeting_modal(payload)
        elif callback_id == 'add_outreach_modal':
            handle_add_outreach_modal(payload)
            
    except Exception as e:
        logger.error(f"Error handling view submission: {e}")

def handle_app_home_opened(event):
    """Handle when user opens the App Home tab"""
    try:
        user_id = event.get('user')
        channel_id = event.get('channel')  # This is the App Home tab ID
        
        logger.info(f"App Home opened by user {user_id}")
        
        # Update the App Home view
        bot.update_app_home(user_id)
        
    except Exception as e:
        logger.error(f"Error handling app home opened: {e}")

def handle_log_attendance_modal(payload):
    """Handle attendance logging modal submission"""
    try:
        user_id = payload['user']['id']
        values = payload['view']['state']['values']
        
        # Extract form data
        meeting_id = payload['view']['private_metadata']
        start_time = values.get('start_time_block', {}).get('start_time_input', {}).get('value', '')
        end_time = values.get('end_time_block', {}).get('end_time_input', {}).get('value', '')
        notes = values.get('notes_block', {}).get('notes_input', {}).get('value', '')
        
        # Process attendance logging
        bot.handle_attendance_modal_submission(user_id, meeting_id, start_time, end_time, notes)
        
    except Exception as e:
        logger.error(f"Error handling log attendance modal: {e}")

def handle_edit_attendance_modal(payload):
    """Handle attendance editing modal submission"""
    try:
        user_id = payload['user']['id']
        values = payload['view']['state']['values']
        
        # Extract form data
        meeting_id = payload['view']['private_metadata']
        start_time = values.get('start_time_block', {}).get('start_time_input', {}).get('value', '')
        end_time = values.get('end_time_block', {}).get('end_time_input', {}).get('value', '')
        notes = values.get('notes_block', {}).get('notes_input', {}).get('value', '')
        
        # Process attendance editing
        bot.handle_edit_attendance_modal_submission(user_id, meeting_id, start_time, end_time, notes)
        
    except Exception as e:
        logger.error(f"Error handling edit attendance modal: {e}")

def handle_add_meeting_modal(payload):
    """Handle add meeting modal submission"""
    try:
        user_id = payload['user']['id']
        values = payload['view']['state']['values']
        
        # Extract form data
        date = values.get('date_block', {}).get('date_input', {}).get('selected_date', '')
        start_time = values.get('start_time_block', {}).get('start_time_input', {}).get('value', '')
        end_time = values.get('end_time_block', {}).get('end_time_input', {}).get('value', '')
        description = values.get('description_block', {}).get('description_input', {}).get('value', '')
        
        # Process meeting creation
        bot.handle_add_meeting_modal_submission(user_id, 'regular', date, start_time, end_time, description)
        
    except Exception as e:
        logger.error(f"Error handling add meeting modal: {e}")

def handle_request_excuse_modal(payload):
    """Handle request excuse modal submission"""
    try:
        user_id = payload['user']['id']
        values = payload['view']['state']['values']
        
        # Extract form data
        meeting_id = payload['view']['private_metadata']
        reason = values.get('reason_block', {}).get('reason_input', {}).get('value', '')
        
        # Process excuse request
        bot.handle_request_excuse_modal_submission(user_id, meeting_id, reason)
        
    except Exception as e:
        logger.error(f"Error handling request excuse modal: {e}")

def handle_add_outreach_modal(payload):
    """Handle add outreach modal submission"""
    try:
        user_id = payload['user']['id']
        values = payload['view']['state']['values']
        
        # Extract form data
        date = values.get('date_block', {}).get('date_input', {}).get('selected_date', '')
        start_time = values.get('start_time_block', {}).get('start_time_input', {}).get('value', '')
        end_time = values.get('end_time_block', {}).get('end_time_input', {}).get('value', '')
        description = values.get('description_block', {}).get('description_input', {}).get('value', '')
        
        # Process outreach creation
        bot.handle_add_meeting_modal_submission(user_id, 'outreach', date, start_time, end_time, description)
        
    except Exception as e:
        logger.error(f"Error handling add outreach modal: {e}")
