#!/usr/bin/env python3
import os

import traceback
import json
from urllib.parse import urljoin
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

from botocore.vendored import requests

TOKEN_HEADER = 'X-Centricient-Hook-Token'
TENANT_HEADER = 'X-Quiq-Tenant'

def build_quiq_reply(question, replies):
    payload = {
        'interactionType': 'quiq-reply',
        'quiqReply': {
            'prompt': {
                'text': question,
            },
            'replies': replies
        },
        'transcriptHints': {
            'icon': { 'builtInIcon': 'list' },
            'heading1': question,
            'heading2': None,
            'description': ", ".join([reply['text'] for reply in replies])
            }
        }
    return payload
    

replies = [{'text': "🌟" * i, "directives": {"fieldUpdates": [{"field": "schema.conversation.custom.csat", "value": str(i)}], 'newConversationRouting': None, 'preventMessage': False}} for i in range(1, 6)]

stars_reply         = build_quiq_reply('How would you rate your experience?', replies)
opt_in_reply        = build_quiq_reply('Tell us how we did today?', [{'text': 'Yes', 'directives': None}, {'text': 'No Thanks', 'directives': None}])
anything_else_reply = build_quiq_reply('Thanks! Anything else to add?', [{'text': 'Yes', 'directives': None}, {'text': 'No', 'directives': None}])

solicit_msg = "Please tell us why you selected this rating"

class ReviewBot(object):
    def __init__(self, site, username, appId, appSecret, **kwargs):
        self.site = site
        self.username = username
        self.s = requests.Session()
        self.s.auth = (appId, appSecret)

    def pong(self, healthy=True):
        self.s.post(urljoin(self.site, 'api/v1/agent-hooks/pong'), json={'healthy':healthy})

    def acknowledge_conversation_update(self, update):
        cid  = update['state']['id']
        data = {'stateId': update['stateId']}
        self.s.post(urljoin(self.site, 'api/v1/messaging/conversations/{}/acknowledge'.format(cid)), json=data)

    def send_message(self, cid, msg=None, rich_interaction=None):
        data = {'text': msg, 'richInteraction': rich_interaction}
        print(self.s.post(urljoin(self.site, 'api/v1/messaging/conversations/{}/send-message'.format(cid)), json=data).text)

    def accept_invitation(self, cid):
        self.s.post(urljoin(self.site, 'api/v1/messaging/conversations/{}/accept'.format(cid)))

    def reject_invitation(self, cid):
        self.s.post(urljoin(self.site, 'api/v1/messaging/conversations/{}/reject'.format(cid)))

    def send_to_queue(self, cid, queue):
        data = {'targetQueue': queue}
        self.s.post(urljoin(self.site, 'api/v1/messaging/conversations/{}/send-to-queue'.format(cid)), json=data)

    def mark_closed(self, cid):
        self.s.post(urljoin(self.site, 'api/v1/messaging/conversations/{}/close'.format(cid)))

    def update_fields(self, cid, field_map):
        data = {'fields': [{'field': k, 'value': v} for k, v in field_map.items()]}
        self.s.post(urljoin(self.site, 'api/v1/messaging/conversations/{}/update-fields'.format(cid)), json=data)

    def handle(self, event_type, data):
        if event_type == 'conversation-update':
            self.handle_conversation_update(data)

    def handle_conversation_update(self, update):
        conversation = update['state']

        hint = next((h['hint'] for h in update['hints']), None)

        my_messages = [msg for msg in conversation['messages'] if msg['author'] == self.username]

        if hint == 'invitation-timer-active':
            self.accept_invitation(conversation['id'])
        elif hint == 'response-timer-active' or conversation['owner'] == self.username and len(my_messages) == 0:
            self.handle_responding_to_customer(conversation)

    def handle_responding_to_customer(self, conversation):
        cid = conversation['id']
        
        sent_yes_no   = next((msg for msg in conversation['messages'] if msg['richInteraction'] and msg['richInteraction']['quiqReply'] == opt_in_reply['quiqReply']), None) != None
        sent_stars    = next((msg for msg in conversation['messages'] if msg['richInteraction'] and msg['richInteraction']['quiqReply'] == stars_reply['quiqReply']), None) != None
        sent_solicit  = next((msg for msg in conversation['messages'] if msg['text'] and msg['text'] == solicit_msg), None) != None
        sent_anything = next((msg for msg in conversation['messages'] if msg['richInteraction'] and msg['richInteraction']['quiqReply'] == anything_else_reply['quiqReply']), None) != None

        last_customer_message = next(msg for msg in reversed(conversation['messages']) if msg['fromCustomer'])

        msg_text = last_customer_message['text']

        if not sent_yes_no:
            self.send_message(cid, rich_interaction=opt_in_reply)
        else:
            if not sent_stars:
                if msg_text.lower().startswith('yes'):
                    self.send_message(cid, 'Great!')
                    self.send_message(cid, rich_interaction=stars_reply)
                elif msg_text.lower().startswith('no'):
                    self.mark_closed(cid)
                else:
                    self.send_message(cid, 'Sorry, I\'m not sure what you mean by that. If you have any further questions please reply again to talk to an agent!')
                    self.mark_closed(cid)
            else:
                if not sent_solicit:
                    self.send_message(cid, solicit_msg)
                else:
                    if not sent_anything:
                        self.send_message(cid, rich_interaction=anything_else_reply)
                    else:
                        if msg_text.lower() == 'yes':
                            pass
                        elif msg_text.lower() == 'no':
                            self.send_message(cid, "Thanks for your feedback!")
                            self.mark_closed(cid)
                        else:
                            self.send_message(cid, rich_interaction=anything_else_reply)
    

def build_response(status_code, body):
    return {
        'statusCode': str(status_code),
        'body': json.dumps(body)
    }

def lambda_handler(event, context):
    """
    Main handler for the bot when running in AWS lambda
    """
    app_id = os.environ['appId']
    app_secret = os.environ['appSecret']
    site = os.environ['site']
    username = os.environ['username']
    hook_secret = os.environ['hookSecret']

    token = event['headers'].get('X-Centricient-Hook-Token')
    if token != hook_secret:
        return build_response(403, 'Invalid verification token provided')

    logger.info(event['body'])
    body = json.loads(event['body'])

    bot = ReviewBot(site, username, app_id, app_secret)

    if body['ping']:
        bot.pong()

    for update in body['conversationUpdates']:
        bot.handle('conversation-update', update)
        bot.acknowledge_conversation_update(update)

    return build_response(200, {})
