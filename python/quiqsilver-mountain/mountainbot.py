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
    conversation_ack_id   = update['ackId']

    bot_state = update['clientState'] if 'clientState' in update and update['clientState'] else {}

    try:
        react_to_conversation_update(conversation_state, conversation_hints, bot_state)
    except Exception as e:
        logger.error("Error while handling conversation update!", e)
        
    request = {'ackId': conversation_ack_id, 'clientState': bot_state}
    qapi_acknowledge(conversation_id, request)

def react_to_conversation_update(conversation, conversation_hints, bot_state):
    
    hints = set([hint['hint'] for hint in conversation_hints])
        
    conversation_id = conversation['id']

    if 'invitation-timer-active' in hints:
        qapi_accept(conversation_id)
    elif 'response-timer-active' in hints or 'no-message-since-assignment' in hints:
        generate_response(conversation, bot_state)

# Action handlers

def send_top_menu(conversation, bot_state):
    first_time = False if 'introduced' in  bot_state and bot_state['introduced'] else True

    replies = {'replies': [
        {'text': 'Snow Report'},
        {'text': 'Hours of Operation'},
        {'text': 'Ticket Prices'},
        {'text': 'Live Representative'}
    ]}

    if first_time:
        text = 'Thanks for contacting Quiqsilver Mountain Resort! My name is Mountain Bot. How can I help you today?'
        bot_state['introduced'] = True
    else:
        text = 'What else can I help you with today?'
        
    qapi_send_message(conversation['id'], {'text': text, 'quiqReply': replies}).text

def send_snow_report(conversation, bot_state):
    qapi_send_message(conversation['id'], {'text': """We've received 6" of new snow overnight! Our current summit depth is 82". Current weather is 22° & calm with a few flakes falling!"""})

def send_hours(conversation, bot_state):
    qapi_send_message(conversation['id'], {'text': """Lifts are open from 9:30am - 4pm, except for the Mercury lift which closes at 3:30. The ticket office and rental shop are open from 8am-6pm"""})

def send_ticket_prices(conversation, bot_state):
    qapi_send_message(conversation['id'], {'text': 'Adult full-day tickets are $49 (ages 13-64), $38 for seniors and $26 for children. Half-day tickets are available adults for $38 starting at 1pm'})

def send_triage(conversation, bot_state):
    qapi_send_message(conversation['id'], 
        {'text': 'What do you need help with?', 
         'quiqReply': {'replies': [
             {'text': 'Purchase Tickets'},
             {'text': 'Equipment Rental'},
             {'text': 'Lodging'},
             {'text': 'Ski School'},
             {'text': 'Something Else'},
           ]}
        })

action_handlers = {
  'send-top-menu': send_top_menu,
  'send-snow-report': send_snow_report,
  'send-hours': send_hours,
  'send-ticket-prices': send_ticket_prices,
  'send-triage': send_triage
}

# Response handlers

def top_menu_response_handler(conversation, bot_state):
    response = [msg['text'].lower() for msg in conversation['messages'] if msg['fromCustomer']][-1]

    action_map = {
        'snow report': 'send-snow-report',
        'hours of operation': 'send-hours',
        'ticket prices': 'send-ticket-prices',
        'live representative': 'send-triage',
    }

    if response in action_map:
        return action_map[response]
    else:
        qapi_send_message(conversation['id'], {'text': "Sorry, I'm not built to understand that!"})
        return 'send-top-menu'
 
def triage_response_handler(conversation, bot_state):
     response = [msg['text'].lower() for msg in conversation['messages'] if msg['fromCustomer']][-1]
     response_map = {
         'purchase tickets': 'tickets',
         'equipment rental': 'rental',
         'lodging': 'lodging',
         'ski school': 'school'
     }

     intent = response_map[response] if response in response_map else 'other'
     qapi_update_fields(conversation['id'], {'fields': [{'field': 'schema.conversation.custom.intent', 'value': intent}]})

     qapi_send_to_queue(conversation['id'], {'targetQueue': 'default'})
     return None

response_handlers = {
  'send-top-menu': top_menu_response_handler,
  'send-triage': triage_response_handler
}
 
def generate_response(conversation, bot_state):

    if 'last-action' not in bot_state:
        bot_state['last-action'] = None

    next_action = 'send-top-menu'

    if bot_state['last-action'] and bot_state['last-action'] in response_handlers:
        next_action = response_handlers[bot_state['last-action']](conversation, bot_state)

    if next_action:
        action_handlers[next_action](conversation, bot_state)

    bot_state['last-action'] = next_action

# For running locally
if __name__ == '__main__':
    from flask import Flask, request
    app = Flask(__name__)

    @app.route('/flask-handler', methods=['post'])
    def flask_handler():
        if request.headers.get('X-Centricient-Hook-Token') != hook_secret:
            return 'Invalid verification token provided', 403

        agent_hook_handler(request.json)

        return '', 204

    app.run(port=9000, debug=True)
