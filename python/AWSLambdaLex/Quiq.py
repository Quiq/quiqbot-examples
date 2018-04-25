import requests
from urllib.parse import urljoin

class QuiqClient(object):
    def __init__(self, site, username, appId, appSecret):
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
