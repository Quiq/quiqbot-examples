import json
import boto3
from time import sleep
from Quiq import QuiqClient

LEX_BOT_NAME = "BookTrip"
LEX_BOT_ALIAS = "booktrip"

QUIQ_SITE = "https://fred.goquiq.com"
QUIQ_BOT_USERNAME = "booking_bot"
QUIQ_VERIFICATION_TOKEN = "9a23055c-63b2-4e74-99df-fa14f42563b0"
QUIQ_ACCESS_TOKEN_ID = "bd1fcce4-bf0f-473d-945a-e3cca9eefbda"
QUIQ_ACCESS_TOKEN_SECRET = "eyJhbGciOiJIUzI1NiIsImtpZCI6ImJhc2ljOjAifQ.eyJ0ZW5hbnQiOiJmcmVkIiwic3ViIjoiODM1MiJ9.r_cyUH9-5OHI8OHN57gNUInNtzcY7qMCNeoYTPyRDQU"

AGENT_QUEUE_NAME = "default"

lex = boto3.client('lex-runtime')
quiq = QuiqClient(QUIQ_SITE, QUIQ_BOT_USERNAME, QUIQ_ACCESS_TOKEN_ID, QUIQ_ACCESS_TOKEN_SECRET)

def build_response(status_code, body):
    return {
        'statusCode': str(status_code),
        'body': json.dumps(body)
    }

def get_lex_response(user_message, conversation_id):
    lex_response = lex.post_text(
        botName=LEX_BOT_NAME,
        botAlias=LEX_BOT_ALIAS,
        userId=conversation_id,
        inputText=user_message
    )
    raw_message =  lex_response.get('message')
    message_type = lex_response['messageFormat']
    dialog_state = lex_response['dialogState']
    intent_name = lex_response['intentName']

    messages = [msg['value'] for msg in json.loads(raw_message)['messages']] \
        if (message_type == 'Composite') \
        else [raw_message]

    return messages, dialog_state, intent_name

def respond_to_customer(conversation):
    cid = conversation['id']
    last_customer_message = next(msg for msg in reversed(conversation['messages']) if msg['fromCustomer'])['text']

    if last_customer_message.lower() == 'agent':
        quiq.send_message(cid, "Alright, I'm transferring you now.")
        quiq.send_to_queue(cid, AGENT_QUEUE_NAME)
    elif last_customer_message.lower() in ['goodbye', 'end', 'close', 'cya', 'bye', 'nevermind', 'nvm']:
        quiq.send_message(cid, "Thanks for using Quiq's resevration demo bot.")
        sleep(1)
        quiq.mark_closed(cid)
    else:
        (responses, dialog_state, intent_name) = get_lex_response(last_customer_message, cid)
        for msg in responses:
            quiq.send_message(cid, msg)
        if dialog_state == 'Failed':
            quiq.send_to_queue(cid, AGENT_QUEUE_NAME)
        if dialog_state == 'Fulfilled' and intent_name != 'Intro':
            sleep(1)
            quiq.mark_closed(cid)

def handle_conversation_update(update):
    conversation = update['state']
    hint = next((h['hint'] for h in update['hints']), None)
    if hint == 'invitation-timer-active':
        quiq.accept_invitation(conversation['id'])
    elif hint == 'response-timer-active':
        respond_to_customer(conversation)

def lambda_handler(event, context):
    # Verify ioncoming request (ensure 'X-Centricient-Hook-Token' mattches QUIQ_VERIFICATION_TOKEN)
    token = event['headers'].get('X-Centricient-Hook-Token')
    if token != QUIQ_VERIFICATION_TOKEN:
        return build_response(401, "Invalid verification token provided")

    body = json.loads(event['body'])

    # Ping Quiq if we need to, so that they know our bot is still active
    if body['ping']:
        quiq.pong()

    for update in body['conversationUpdates']:
        handle_conversation_update(update)
        quiq.acknowledge_conversation_update(update)

    return build_response(200, {})
