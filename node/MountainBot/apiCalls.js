const fetch = require('./fetch');
const logger = require('node-color-log');

// [Previous status, Current status]
let healthy = [false, true];
const pong = async () => {
  healthy[0] = healthy[1];
  try {
    await fetch('api/v1/agent-hooks/pong', {
      method: 'POST',
      body: {healthy: true},
    });
    healthy[1] = true;
  } catch (e) {
    healthy[1] = false;
  } finally {
    if (healthy[0] && !healthy[1]) logger.color('red').log('Client has become unhealthy!');
    if (healthy[1] && !healthy[0]) logger.color('green').log('Client has become healthy!');
    if (!healthy[0] && !healthy[1]) logger.color('red').log('Client is still unhealthy!');
  }
};

const conversationApi = async (conversationId, body, endpoint) => {
  await fetch(`api/v1/messaging/conversations/${conversationId}/${endpoint}`, {
    method: 'POST',
    body,
  });
};

const acknowledge = async (conversationId, body) =>
  conversationApi(conversationId, body, 'acknowledge');

const accept = async conversationId => conversationApi(conversationId, undefined, 'accept');

const acceptTransfer = async conversationId =>
  conversationApi(conversationId, undefined, 'accept-transfer');

const sendMessage = async (conversationId, body) =>
  conversationApi(conversationId, body, 'send-message');

const sendToQueue = async (conversationId, body) =>
  conversationApi(conversationId, body, 'send-to-queue');

const sendToUser = async (conversationId, body) =>
  conversationApi(conversationId, body, 'send-to-user');

const updateFields = async (conversationId, body) =>
  conversationApi(conversationId, body, 'update-fields');

module.exports = {
  pong,
  acknowledge,
  accept,
  acceptTransfer,
  sendMessage,
  sendToQueue,
  sendToUser,
  updateFields,
};
