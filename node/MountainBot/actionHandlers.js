const apiCalls = require('./apiCalls');

const sendTopMenu = async (conversation, botState) => {
  let text = '';
  if (!botState.introduced) {
    text =
      'Thanks for contacting Quiqsilver Mountain Resort! My name is Mountain Bot. How can I help you today?';
    botState.introduced = true;
  } else {
    text = 'What else can I help you with today?';
  }

  await apiCalls.sendMessage(conversation.id, {
    text,
    quiqReply: {
      replies: [
        {text: 'Snow Report'},
        {text: 'Hours of Operation'},
        {text: 'Ticket Prices'},
        {text: 'Live Representative'},
      ],
    },
  });
};

const sendSnowReport = async conversation => {
  await apiCalls.sendMessage(conversation.id, {
    text:
      'We\'ve received 6" of new snow overnight! Our current summit depth is 82". Current weather is 22° & calm with a few flakes falling!',
  });
};

const sendHours = async conversation => {
  await apiCalls.sendMessage(conversation.id, {
    text:
      'Lifts are open from 9:30am - 4pm, except for the Mercury lift which closes at 3:30. The ticket office and rental shop are open from 8am-6pm',
  });
};

const sendTicketPrices = async conversation => {
  await apiCalls.sendMessage(conversation.id, {
    text:
      'Adult full-day tickets are $49 (ages 13-64), $38 for seniors and $26 for children. Half-day tickets are available adults for $38 starting at 1pm',
  });
};

const sendTriage = async conversation => {
  await apiCalls.sendMessage(conversation.id, {
    text: 'What do you need help with?',
    quiqReply: {
      replies: [
        {text: 'Purchase Tickets'},
        {text: 'Equipment Rental'},
        {text: 'Lodging'},
        {text: 'Ski School'},
        {text: 'Something Else'},
      ],
    },
  });
};

module.exports = {
  sendTopMenu,
  sendSnowReport,
  sendHours,
  sendTicketPrices,
  sendTriage,
};
