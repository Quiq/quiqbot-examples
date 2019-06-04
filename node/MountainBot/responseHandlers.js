const last = require('lodash/last');
const apiCalls = require('./apiCalls');

const sendTopMenu = async conversation => {
  const lastCustomerMessage = last(conversation.messages.filter(m => m.fromCustomer));

  const actionMap = {
    'snow report': 'sendSnowReport',
    'hours of operation': 'sendHours',
    'ticket prices': 'sendTicketPrices',
    'live representative': 'sendTriage',
  };

  const action = Object.keys(actionMap).find(k =>
    lastCustomerMessage.text.toLowerCase().includes(k),
  );
  if (action) return actionMap[action];

  await apiCalls.sendMessage(conversation.id, {text: "Sorry, I'm not built to understand that!"});
  return 'sendTopMenu';
};

const sendTriage = async conversation => {
  const lastCustomerMessage = last(conversation.messages.filter(m => m.fromCustomer));

  const responseMap = {
    'purchase tickets': 'tickets',
    'equipment rental': 'rental',
    lodging: 'lodging',
    'ski school': 'school',
  };
  const response = Object.keys(responseMap).find(k =>
    lastCustomerMessage.text.toLowerCase().includes(k),
  );

  const intent = response ? responseMap[response] : 'other';

  await apiCalls.updateFields(conversation.id, {
    fields: [{field: 'schema.conversation.custom.intent', value: intent}],
  });
  await apiCalls.sendToQueue(conversation.id, {targetQueue: 'default'});
};

module.exports = {
  sendTopMenu,
  sendTriage,
};
