import json
import logging
import os

from botocore.vendored import requests
from urllib.parse import urljoin

logger = logging.getLogger()
logger.setLevel(logging.INFO)

app_id      = os.environ['appId']
app_secret  = os.environ['appSecret']
hook_secret = os.environ['hookSecret']

site = os.environ['site']

http = requests.Session()
http.auth = (app_id, app_secret) 
def qapi_pong(): return http.post(urljoin(site, 'api/v1/agent-hooks/pong'), json={'healthy': True})

def qapi_acknowledge(conversation_id, request):    return http.post(urljoin(site, 'api/v1/messaging/conversations/{}/acknowledge'.format(conversation_id)), json=request)
def qapi_accept(conversation_id):                  return http.post(urljoin(site, 'api/v1/messaging/conversations/{}/accept'.format(conversation_id)))
def qapi_accept_transfer(conversation_id):         return http.post(urljoin(site, 'api/v1/messaging/conversations/{}/accept-transfer'.format(conversation_id)))
def qapi_send_message(conversation_id, request):   return http.post(urljoin(site, 'api/v1/messaging/conversations/{}/send-message'.format(conversation_id)), json=request)
def qapi_send_to_queue(conversation_id, request):  return http.post(urljoin(site, 'api/v1/messaging/conversations/{}/send-to-queue'.format(conversation_id)), json=request)
def qapi_send_to_user(conversation_id, request):   return http.post(urljoin(site, 'api/v1/messaging/conversations/{}/send-to-user'.format(conversation_id)), json=request)
def qapi_update_fields(conversation_id, request):  return http.post(urljoin(site, 'api/v1/messaging/conversations/{}/update-fields'.format(conversation_id)), json=request)
    
def lambda_handler(event, context):

    token = event['headers'].get('X-Centricient-Hook-Token')

    if token != hook_secret:
        return {'statusCode': 403, 'body': "Invalid verification token provided"}

    agent_hook_handler(json.loads(event['body']))

    return {'statusCode': 204, 'body': None}

def agent_hook_handler(event):
    
    if event['ping']:
        qapi_pong()

    for update in event['conversationUpdates']:
        conversation_update_handler(update)

def conversation_update_handler(update):
    
    conversation_state    = update['state']
    conversation_id       = update['state']['id']
    conversation_hints    = update['hints']
    conversation_state_id = update['stateId']

    bot_state = update['clientState'] if 'clientState' in update and update['clientState'] else {}

    try:
        react_to_conversation_update(conversation_state, conversation_hints, bot_state)
    except Exception as e:
        logger.error("Error while handling conversation update!", e)
        
    request = {'stateId': conversation_state_id, 'clientState': bot_state}
    qapi_acknowledge(conversation_id, request)

def react_to_conversation_update(conversation, conversation_hints, bot_state):
    
    hints = set([hint['hint'] for hint in conversation_hints])
        
    conversation_id = conversation['id']

    if 'transfer-requested' in hints:
        qapi_accept_transfer(conversation_id)
    elif 'response-timer-active' in hints or 'no-message-since-assignment' in hints:
        generate_response(conversation, bot_state)
 
fields  = ['equipment-type', 'terrain', 'skill-level', 'height']
heights = ["4'", "4' 3\"", "4' 6\"", "4' 9\"", "5'", "5' 3\"", "5' 6\"", "5' 9\"", "6'", "6' 3\""]

field_message_map = {
    'equipment-type': {
        'text': 'Are you a skier or snowboarder?',
        'quiqReply': {'replies': [{'text': 'Skier'}, {'text': 'Snowboarder'}]}
    },
    'terrain': {
        'text': "What type of equipment are you looking for?",
        'quiqReply': {'replies': [{'text': 'All Mountain'}, {'text': 'Powder'}, {'text': 'Carving'}, {'text': 'Park & Pipe'}]}
    },

    'skill-level': {
        'text': "What's your skill level on the mountain?",
        'quiqReply': {'replies': [{'text': 'Beginner'}, {'text': 'Intermediate'}, {'text': 'Advanced'}, {'text': 'Expert'}]}
    },
    'height': {
        'text': "How tall are you?",
        'quiqReply': {'replies': [{'text': height} for height in heights]}
    }
}
      
def generate_response(conversation, bot_state):
    
    if 'expected_field' not in bot_state:
        bot_state['expected_field'] = None

    if 'customer_info' not in bot_state:
        bot_state['customer_info'] = {}

    expected_field = bot_state['expected_field']

    if expected_field:
        last_customer_message = [msg for msg in conversation['messages'] if msg['fromCustomer']][-1]['text']
        bot_state['customer_info'][expected_field] = last_customer_message
        bot_state['expected_field'] = None
   
    for field in fields:
        if not bot_state['expected_field'] and field not in bot_state['customer_info']:
            qapi_send_message(conversation['id'], field_message_map[field])
            bot_state['expected_field'] = field

    if not bot_state['expected_field']:
        return_conversation_to_previous_owner(conversation)

def return_conversation_to_previous_owner(conversation):
    old_owner = [event['oldOwner'] for event in conversation['events'] if event['type'] == 'ownerChanged'][-1]

    qapi_send_to_user(conversation['id'], {'userId': old_owner})

from flask import Flask, request
app = Flask(__name__)

@app.route('/flask-handler', methods=['post'])
def flask_handler():
    if request.headers.get('X-Centricient-Hook-Token') != hook_secret:
        return 'Invalid verification token provided', 403

    agent_hook_handler(request.json)

    return '', 204

app.run(port=9000, debug=True)
