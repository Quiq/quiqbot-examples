const apiCalls = require('./apiCalls');
const logger = require('node-color-log');
const actionHandlers = require('./actionHandlers');
const responseHandlers = require('./responseHandlers');

const generateResponse = async (conversation, botState) => {
  let nextAction = 'sendTopMenu';

  if (botState['lastAction'] && responseHandlers[botState['lastAction']]) {
    nextAction = await responseHandlers[botState['lastAction']](conversation, botState);
  }

  if (nextAction) {
    await actionHandlers[nextAction](conversation, botState);
  }

  botState['lastAction'] = nextAction;
};

const reactToConversationUpdate = async (conversation, conversationHints, botState) => {
  const hints = conversationHints.map(h => h.hint);

  if (hints.includes('invitation-timer-active')) return await apiCalls.accept(conversation.id);
  else if (hints.includes('response-timer-active') || hints.includes('no-message-since-assignment'))
    return await generateResponse(conversation, botState);
};

const handleConversationUpdate = async update => {
  const {state, ackId, clientState} = update;
  const botState = clientState || {};

  logger.color('yellow').log(`Bot State Before Update ${JSON.stringify(botState)}`);
  try {
    await reactToConversationUpdate(state, update.hints, botState);
  } catch (e) {
    logger.color('red').log(`Error while hanlding conversation update!`, e);
  }
  logger.color('yellow').log(`Bot State After Update ${JSON.stringify(botState)}`);

  await apiCalls.acknowledge(state.id, {ackId, clientState: botState});
};

const handleConversationEvents = async updates => {
  for (update of updates){
    await handleConversationUpdate(update);
  }
}

module.exports = handleConversationEvents;
