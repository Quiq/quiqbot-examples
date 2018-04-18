#!/usr/bin/env python3
import traceback
import requests
from urllib.parse import urljoin

from flask import Flask, request

import mock_data

TOKEN_HEADER = 'X-Centricient-Hook-Token'

get_order_msg = """
What's your order number?
""".strip()

get_last_name_msg = """
What is the last name associated with this order?
""".strip()

class SelfServiceBot(object):
    def __init__(self, site, username, appId, appSecret):
        print('Created bot for {}'.format(site))
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

    def send_message(self, cid, msg):
        data = {'text': msg}
        self.s.post(urljoin(self.site, 'api/v1/messaging/conversations/{}/send-message'.format(cid)), json=data)

    def accept_invitation(self, cid):
        self.s.post(urljoin(self.site, 'api/v1/messaging/conversations/{}/accept'.format(cid)))

    def send_to_queue(self, cid, queue):
        data = {'targetQueue': queue}
        self.s.post(urljoin(self.site, 'api/v1/messaging/conversations/{}/send-to-queue'.format(cid)), json=data)

    def mark_closed(self, cid):
        self.s.post(urljoin(self.site, 'api/v1/messaging/conversations/{}/close'.format(cid)))

    def handle(self, event_type, data):
        if event_type == 'conversation-update':
            self.handle_conversation_update(data)

    def handle_conversation_update(self, update):
        conversation = update['state']

        hint = next((h['hint'] for h in update['hints']), None)
        if hint == 'invitation-timer-active':
            self.accept_invitation(conversation['id'])
        elif hint == 'response-timer-active':
            self.handle_responding_to_customer(conversation)

    def determine_state(self, conversation):
        bot_messages = [m for m in conversation['messages'] if m['author'] == self.username]
        if len(bot_messages) == 0:
            return 'get-order'

        sent_get_order_message = len([m for m in bot_messages if m['text'] == get_order_msg]) > 0
        sent_get_last_name_message = len([m for m in bot_messages if m['text'] == get_last_name_msg]) > 0
        sent_order_info = len([m for m in bot_messages if m['text'].startswith('You ordered a')]) > 0

        if sent_order_info:
            return 'wrapup'

        if sent_get_last_name_message:
            return 'lookup-order-name'

        if sent_get_order_message:
            return 'lookup-order-id'

        return None

    def handle_responding_to_customer(self, conversation):
        cid = conversation['id']

        last = next(msg for msg in reversed(conversation['messages']) if msg['fromCustomer'])['text']

        state = self.determine_state(conversation)
        if state == 'get-order':
            self.send_message(cid, get_order_msg)

        elif state == 'lookup-order-id':
            match = None
            for token in last.split():
                match = next((order for order in mock_data.orders if order['id'] == token), None)
                if match:
                    break
            if match:
                self.send_message(cid, 'You ordered a ' + match['description'] + ' on ' + match['orderDate'] + '. \n\nIs there anything else I can help you with?')
            else:
                self.send_message(cid, get_last_name_msg)

        elif state == 'lookup-order-name':
            match = None
            for token in last.split():
                for idx, cust in enumerate(mock_data.customers):
                    if cust['name'].split()[1].lower() == token.lower():
                        match = mock_data.orders[idx]
                if match:
                    break
            if match:
                self.send_message(cid, 'You ordered a ' + match['description'] + ' on ' + match['orderDate'] + '. \n\nIs there anything else I can help you with?')
            else:
                self.send_message(cid, 'One moment please')
                self.send_to_queue(cid, 'default')

        elif state == 'wrapup':
            if len([tok for tok in last.split() if tok.lower().startswith('no')]) > 0:
                self.mark_closed(cid)
            else:
                self.send_message(cid, 'One moment please')
                self.send_to_queue(cid, 'default')

def create_app(config='config.py'):
    app = Flask(__name__)
    app.config.from_pyfile(config)
    bot = SelfServiceBot(**app.config['BOT'])

    @app.route('/react', methods=['post'])
    def react():
        if app.config.get('HOOK_TOKEN') and app.config.get('HOOK_TOKEN') != request.headers.get(TOKEN_HEADER):
            return 'Invalid hook token', 403
        try:
            if request.json['ping']:
                bot.pong()

            for update in request.json['conversationUpdates']:
                bot.handle('conversation-update', update)
                bot.acknowledge_conversation_update(update)
        except Exception:
            traceback.print_exc()
        return '', 204

    @app.route('/ping')
    def ping():
        return 'pong'

    return app

if __name__=='__main__':
    app = create_app()
    app.run(port=9000, debug=True)
