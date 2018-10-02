import json
import boto3
from time import sleep
from Quiq import QuiqClient

LEX_BOT_NAME = "<Name of the AWS Lex bot to use>"
LEX_BOT_ALIAS = "<Alias for the bot you chose when you published the bot>"

QUIQ_SITE = "https://<tenant>.goquiq.com"

# NOTE: In production, you should never store your Quiq secrets in source code.
#       This is for demo purposes only.

QUIQ_BOT_USERNAME = "<username of your Quiq bot agent>"
QUIQ_VERIFICATION_TOKEN = "<your quiq bot secret>"
QUIQ_ACCESS_TOKEN_ID = "<Bot agent's access token ID>"
QUIQ_ACCESS_TOKEN_SECRET = "<Bot agent's access token secret>"

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

    current_hints = set([h['hint'] for h in update['hints']])

    if 'invitation-timer-active' in current_hints:
        quiq.accept_invitation(conversation['id'])
    elif 'response-timer-active' in current_hints or 'no-message-since-assignment' in current_hints:
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
